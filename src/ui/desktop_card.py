import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QCheckBox, QPushButton, QFileDialog
)
from PySide6.QtCore import Signal, Qt
from src.ui.styles import BRONZE, TEXT_MUTED, CARD_STYLE


class DesktopCard(QWidget):
    enabled_changed = Signal(str, bool)       # desktop_id, enabled
    background_changed = Signal(str, str)     # desktop_id, image_path
    delete_requested = Signal(str)            # desktop_id

    def __init__(self, desktop: dict, parent=None):
        super().__init__(parent)
        self.desktop = desktop
        self.setObjectName("desktopCard")
        self.setStyleSheet(CARD_STYLE)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        # Row 1: name + enabled checkbox + delete
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        name_label = QLabel(self.desktop["name"])
        name_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: #E8E8E8;")
        top_row.addWidget(name_label)
        top_row.addStretch()

        self.enabled_cb = QCheckBox("Enabled")
        self.enabled_cb.setChecked(self.desktop.get("enabled", True))
        self.enabled_cb.stateChanged.connect(self._on_enabled_changed)
        top_row.addWidget(self.enabled_cb)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerButton")
        delete_btn.setFixedWidth(70)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.desktop["id"]))
        top_row.addWidget(delete_btn)

        outer.addLayout(top_row)

        # Row 2: background path + select button
        bg_row = QHBoxLayout()
        bg_row.setSpacing(10)

        bg_path = self.desktop.get("background_path") or ""
        display = os.path.basename(bg_path) if bg_path else "No background set"
        self.bg_label = QLabel(display)
        self.bg_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        self.bg_label.setToolTip(bg_path)
        bg_row.addWidget(self.bg_label, stretch=1)

        select_btn = QPushButton("Select Background")
        select_btn.setFixedWidth(140)
        select_btn.clicked.connect(self._on_select_background)
        bg_row.addWidget(select_btn)

        outer.addLayout(bg_row)

    def _on_enabled_changed(self, state):
        self.enabled_changed.emit(self.desktop["id"], state == Qt.CheckState.Checked.value)

    def _on_select_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            os.path.expanduser("~\\Pictures"),
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.desktop["background_path"] = path
            self.bg_label.setText(os.path.basename(path))
            self.bg_label.setToolTip(path)
            self.background_changed.emit(self.desktop["id"], path)
