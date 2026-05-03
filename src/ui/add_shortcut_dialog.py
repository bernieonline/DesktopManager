"""
AddShortcutDialog: two-step dialog for adding a shortcut.

Step 1 — File picker: user selects a file, folder, or .exe
Step 2 — Name confirmation: pre-filled name, user can edit before confirming
Returns (target_path, confirmed_name) or None if cancelled.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt

from src.core.shortcut_manager import get_display_name
from src.ui.styles import BRONZE, TEXT_PRIMARY, TEXT_MUTED, BG_DARK, MAIN_STYLE
from src.utils.logger import get_logger

logger = get_logger("AddShortcutDialog")


class AddShortcutDialog:

    def __init__(self, parent=None):
        self._parent = parent

    def exec_dialog(self) -> tuple[str, str] | None:
        """
        Run the two-step flow.
        Returns (target_path, label) or None if the user cancels.
        """
        target_path = self._pick_target()
        if not target_path:
            return None

        auto_name = get_display_name(target_path)
        label = self._confirm_name(auto_name, target_path)
        if label is None:
            return None

        logger.info(f"AddShortcutDialog: '{label}' → {target_path}")
        return target_path, label

    # ------------------------------------------------------------------
    # Step 1: file / folder picker
    # ------------------------------------------------------------------

    def _pick_target(self) -> str | None:
        """
        Open a dialog that lets the user pick a file or folder.
        Returns the selected path, or None if cancelled.
        """
        # First ask: file or folder?
        choice = _PickTypeDialog(self._parent).exec_choice()
        if choice is None:
            return None

        if choice == "folder":
            path = QFileDialog.getExistingDirectory(
                self._parent,
                "Select Folder",
                "",
                QFileDialog.Option.ShowDirsOnly
            )
            return path or None

        else:  # file / app
            path, _ = QFileDialog.getOpenFileName(
                self._parent,
                "Select File or Application",
                "",
                "Applications & Files (*.exe *.lnk *.com *.bat *.cmd *.msi *.py *.*)"
            )
            return path or None

    # ------------------------------------------------------------------
    # Step 2: name confirmation
    # ------------------------------------------------------------------

    def _confirm_name(self, auto_name: str, path: str) -> str | None:
        """
        Show a small dialog pre-filled with auto_name.
        Returns the confirmed name string, or None if cancelled.
        """
        dialog = _NameDialog(auto_name, path, self._parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_name()
        return None


# ---------------------------------------------------------------------------
# Internal dialogs
# ---------------------------------------------------------------------------

class _PickTypeDialog(QDialog):
    """Compact dialog: pick file or folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Shortcut")
        self.setFixedSize(280, 130)
        self.setStyleSheet(MAIN_STYLE)
        self._choice = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        lbl = QLabel("What would you like to add a shortcut to?")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        folder_btn = QPushButton("📁  Folder")
        folder_btn.setObjectName("primaryButton")
        folder_btn.clicked.connect(lambda: self._select("folder"))
        btn_row.addWidget(folder_btn)

        file_btn = QPushButton("⚙  File / App")
        file_btn.clicked.connect(lambda: self._select("file"))
        btn_row.addWidget(file_btn)

        layout.addLayout(btn_row)

    def _select(self, choice: str):
        self._choice = choice
        self.accept()

    def exec_choice(self) -> str | None:
        self.exec()
        return self._choice


class _NameDialog(QDialog):
    """Compact dialog: confirm or edit the shortcut label."""

    def __init__(self, auto_name: str, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shortcut Name")
        self.setFixedSize(320, 150)
        self.setStyleSheet(MAIN_STYLE)
        self._build(auto_name, path)

    def _build(self, auto_name: str, path: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        lbl = QLabel("Shortcut name:")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(lbl)

        self._edit = QLineEdit(auto_name)
        self._edit.selectAll()
        self._edit.returnPressed.connect(self.accept)
        layout.addWidget(self._edit)

        path_lbl = QLabel(path)
        path_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        path_lbl.setWordWrap(True)
        layout.addWidget(path_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Add Shortcut")
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

        self._edit.setFocus()

    def get_name(self) -> str:
        return self._edit.text().strip() or self._edit.placeholderText()
