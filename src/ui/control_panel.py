import os
import shutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QLabel, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.core.config_manager import ConfigManager
from src.core.virtual_desktop_manager import VirtualDesktopManager
from src.ui.desktop_card import DesktopCard
from src.ui.add_desktop_dialog import AddDesktopDialog
from src.ui.styles import MAIN_STYLE, BRONZE, TEXT_MUTED, BG_DARK
from src.utils.logger import get_logger

logger = get_logger("ControlPanel")


class ControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.vdm = VirtualDesktopManager()
        self.config.load_profile()
        self._build_ui()
        self._refresh_cards()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle("Desktop Workspaces")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        self.setStyleSheet(MAIN_STYLE)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_scroll_area(), stretch=1)
        root.addWidget(self._build_footer())

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("Ready.")

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background-color: #141414; border-bottom: 1px solid #2A2A2A;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Desktop Workspaces")
        title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {BRONZE};")
        layout.addWidget(title)
        layout.addStretch()

        subtitle = QLabel("Control Panel")
        subtitle.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        layout.addWidget(subtitle)

        return header

    def _build_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet(f"background-color: #1E1E1E; border-bottom: 1px solid #2A2A2A;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        add_btn = QPushButton("+ Add Desktop")
        add_btn.setStyleSheet(
            f"QPushButton {{ background-color: {BRONZE}; color: #1A1A1A; font-weight: bold;"
            "border: none; border-radius: 4px; padding: 6px 14px; font-size: 13px; }"
            "QPushButton:hover { background-color: #7DD4F8; }"
            "QPushButton:pressed { background-color: #29A8D8; }"
        )
        add_btn.clicked.connect(self._on_add_desktop)
        layout.addWidget(add_btn)

        refresh_btn = QPushButton("⟳ Refresh Desktops")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #2E2E2E; color: #E8E8E8; border: 1px solid #333333;"
            "border-radius: 4px; padding: 6px 14px; font-size: 13px; }"
            f"QPushButton:hover {{ background-color: #383838; border-color: #4FC3F7; }}"
            "QPushButton:pressed { background-color: #222222; }"
        )
        refresh_btn.clicked.connect(self._on_refresh_desktops)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        return toolbar

    def _build_scroll_area(self) -> QScrollArea:
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet(f"background-color: #1A1A1A;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(16, 16, 16, 16)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        return self.scroll_area

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"background-color: #141414; border-top: 1px solid #2A2A2A;")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        layout.addStretch()

        diag_btn = QPushButton("Diagnostics")
        diag_btn.clicked.connect(self._on_diagnostics)
        layout.addWidget(diag_btn)

        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)

        return footer

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    def _refresh_cards(self):
        # Remove existing cards (all items except the trailing stretch)
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        desktops = self.config.get_all_desktops()

        if not desktops:
            empty = QLabel("No desktops yet. Click '+ Add Desktop' to get started.")
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.insertWidget(0, empty)
            return

        for i, desktop in enumerate(desktops):
            card = DesktopCard(desktop)
            card.enabled_changed.connect(self._on_enabled_changed)
            card.background_changed.connect(self._on_background_changed)
            card.delete_requested.connect(self._on_delete_desktop)
            self.cards_layout.insertWidget(i, card)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_desktop(self):
        dialog = AddDesktopDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        if dialog.exec() != AddDesktopDialog.DialogCode.Accepted:
            return

        name = dialog.get_name()
        existing = self.vdm.find_desktop_by_name(name)
        if existing:
            self._set_status(f"A desktop named '{name}' already exists in Windows.")
            return

        desktop = self.config.add_desktop(name)
        self.vdm.create_desktop(name)
        self._refresh_cards()
        self._set_status(f"Desktop '{name}' created.")
        logger.info(f"Added desktop: '{name}'")

    def _on_delete_desktop(self, desktop_id: str):
        desktop = self.config.get_desktop_by_id(desktop_id)
        if not desktop:
            return

        name = desktop["name"]
        reply = QMessageBox.question(
            self,
            "Delete Desktop",
            f"Delete '{name}'? This will remove it from Windows and your profile.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.vdm.delete_desktop(name)
        self.config.delete_desktop(desktop_id)
        self._refresh_cards()
        self._set_status(f"Desktop '{name}' deleted.")
        logger.info(f"Deleted desktop: '{name}'")

    def _on_enabled_changed(self, desktop_id: str, enabled: bool):
        desktop = self.config.get_desktop_by_id(desktop_id)
        if not desktop:
            return
        self.config.update_desktop(desktop_id, {"enabled": enabled})
        state = "enabled" if enabled else "disabled"
        self._set_status(f"Desktop '{desktop['name']}' {state}. Change takes effect on next startup.")

    def _on_background_changed(self, desktop_id: str, image_path: str):
        desktop = self.config.get_desktop_by_id(desktop_id)
        if not desktop:
            return

        local_path = self._copy_wallpaper_locally(image_path)
        if local_path is None:
            QMessageBox.warning(
                self,
                "Image Not Available",
                f"The selected image could not be read.\n\n"
                f"If it's stored in OneDrive, right-click the file in Explorer "
                f"and choose 'Always keep on this device', then try again."
            )
            return

        self.config.update_desktop(desktop_id, {"background_path": local_path})
        ok = self.vdm.set_wallpaper(desktop["name"], local_path)
        if ok:
            self._set_status(f"Background updated for '{desktop['name']}'.")
        else:
            self._set_status(f"Background saved but could not apply — desktop may not exist yet.")

    def _copy_wallpaper_locally(self, source_path: str) -> str | None:
        source_path = os.path.normpath(os.path.abspath(source_path))
        if not os.path.isfile(source_path):
            logger.warning(f"Wallpaper source not accessible: {source_path}")
            return None
        wallpaper_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "DesktopWorkspaces", "wallpapers"
        )
        os.makedirs(wallpaper_dir, exist_ok=True)
        dest_path = os.path.join(wallpaper_dir, os.path.basename(source_path))
        shutil.copy2(source_path, dest_path)
        logger.info(f"Wallpaper copied to local store: {dest_path}")
        return dest_path

    def _on_refresh_desktops(self):
        all_desktops = self.config.get_all_desktops()
        created = self.vdm.sync_desktops(all_desktops)
        self._set_status(f"Refreshed: {len(created)} desktop(s) active.")
        logger.info(f"Refresh desktops: {len(created)} active.")

    def _on_diagnostics(self):
        desktops = self.config.get_all_desktops()
        windows_desktops = self.vdm.get_all_desktops()
        lines = [
            f"Profile desktops: {len(desktops)}",
            f"Windows desktops: {len(windows_desktops)}",
            "",
        ]
        for d in desktops:
            status = "enabled" if d.get("enabled") else "disabled"
            bg = d.get("background_path") or "none"
            lines.append(f"  {d['name']} [{status}] — bg: {bg}")

        QMessageBox.information(self, "Diagnostics", "\n".join(lines))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, message: str):
        self.status_bar.showMessage(message)
