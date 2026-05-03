from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt
from src.ui.styles import BRONZE, TEXT_MUTED


class AddDesktopDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Desktop")
        self.setFixedSize(420, 170)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        label = QLabel("Desktop name:")
        layout.addWidget(label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Design, Development, Writing…")
        self.name_input.returnPressed.connect(self._accept)
        layout.addWidget(self.name_input)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        self.ok_btn = QPushButton("Add Desktop")
        self.ok_btn.setObjectName("primaryButton")
        self.ok_btn.clicked.connect(self._accept)

        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: #C0392B; font-size: 12px;")
        layout.addWidget(self.error_label)

    def _accept(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText("Please enter a name.")
            return
        if len(name) > 40:
            self.error_label.setText("Name must be 40 characters or fewer.")
            return
        self.accept()

    def get_name(self) -> str:
        return self.name_input.text().strip()
