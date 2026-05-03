"""
ShortcutTile: a single clickable shortcut in the shop window.

Visual design:
  - Fixed 116 x 104 px
  - Icon (48x48) centred above a short label
  - Small status dot in top-right corner (green / amber / red / grey)
  - Bronze border on hover
  - Single click launches the target via os.startfile()
  - paintEvent draws the background and border (supports transparency)
"""

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFontMetrics

from src.core.shortcut_manager import get_shell_icon
from src.ui.styles import BRONZE, STATUS_AVAILABLE, STATUS_UNAVAILABLE, STATUS_DEAD, STATUS_UNKNOWN
from src.utils.logger import get_logger

logger = get_logger("ShortcutTile")

_DEFAULT_TILE_W = 116
_DEFAULT_TILE_H = 104
CORNER_RADIUS = 6

STATUS_COLOURS = {
    "available":   STATUS_AVAILABLE,
    "unavailable": STATUS_UNAVAILABLE,
    "dead":        STATUS_DEAD,
}


class ShortcutTile(QWidget):
    """
    Clickable tile representing one shortcut in the shop window.

    shortcut_data dict must contain: id, label, path, type
    Optional: status ("available" | "unavailable" | "dead" | None)
    """

    def __init__(self, shortcut_data: dict, tile_w: int = _DEFAULT_TILE_W,
                 tile_h: int = _DEFAULT_TILE_H, parent=None):
        super().__init__(parent)
        self._data = shortcut_data
        self._hovered = False
        self._status = shortcut_data.get("status")
        self._tile_w = tile_w
        self._tile_h = tile_h

        # Derive sub-element sizes from tile dimensions
        self._icon_size = max(24, int(tile_w * 0.38))
        self._dot_size  = max(7,  int(tile_w * 0.08))
        self._font_size = max(9,  int(tile_w * 0.095))

        self.setFixedSize(tile_w, tile_h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(shortcut_data.get("path", ""))

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self._icon_size, self._icon_size)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._load_icon()
        layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        # Label
        self._name_label = QLabel(self._elide(self._data.get("label", ""), self._tile_w - 14))
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._name_label.setStyleSheet(
            f"color: #E8E8E8; font-family: Segoe UI; font-size: {self._font_size}px; background: transparent;"
        )
        self._name_label.setWordWrap(False)
        layout.addWidget(self._name_label, 0, Qt.AlignmentFlag.AlignHCenter)

    def _load_icon(self):
        path = self._data.get("path", "")
        icon = get_shell_icon(path)
        pixmap = icon.pixmap(QSize(self._icon_size, self._icon_size))
        self._icon_label.setPixmap(pixmap)

    # ------------------------------------------------------------------
    # Public: update status dot after background validation
    # ------------------------------------------------------------------

    def set_status(self, status: str):
        self._status = status
        self.update()  # trigger repaint for the dot

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        # Background
        bg_colour = QColor(55, 55, 55, 190) if self._hovered else QColor(30, 30, 30, 155)
        painter.setBrush(QBrush(bg_colour))

        # Border
        if self._hovered:
            painter.setPen(QPen(QColor(BRONZE), 1.5))
        else:
            painter.setPen(QPen(QColor(60, 60, 60, 180), 1))

        painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)

        # Status dot — top-right corner
        dot_colour = QColor(STATUS_COLOURS.get(self._status, STATUS_UNKNOWN))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_colour))
        dot_x = self.width() - self._dot_size - 5
        dot_y = 5
        painter.drawEllipse(dot_x, dot_y, self._dot_size, self._dot_size)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path = self._data.get("path", "")
            if path:
                try:
                    os.startfile(path)
                    logger.info(f"Launched: '{self._data.get('label')}' → {path}")
                except Exception as e:
                    logger.error(f"Failed to launch '{path}': {e}")
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _elide(text: str, max_width: int) -> str:
        """Truncate text with ellipsis if it exceeds max_width pixels."""
        from PySide6.QtGui import QFont
        fm = QFontMetrics(QFont("Segoe UI", 8))
        return fm.elidedText(text, Qt.TextElideMode.ElideRight, max_width)
