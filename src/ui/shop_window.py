"""
ShopWindow: the primary user interface — a translucent, frameless launcher
that shows the current virtual desktop's shortcuts as clickable tiles.

Design:
  - Frameless, translucent background, 1px bronze border
  - Fixed width, positioned top-right of primary screen
  - Header: active desktop name
  - Body: 3-column tile grid (shortcut tiles)
  - Footer bar: action buttons
  - Manage panel: expands below footer for editing
  - Draggable by header
"""

import os
import ctypes
import ctypes.wintypes
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QScrollArea, QSizePolicy, QFileDialog, QMessageBox,
    QFrame
)
from PySide6.QtCore import Qt, QPoint, QTimer, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor

from src.core.config_manager import ConfigManager
from src.core.virtual_desktop_manager import VirtualDesktopManager
from src.core.shortcut_manager import (
    validate_path, extract_lnk_target, get_display_name, create_lnk, DESKTOP_DIR
)
from src.core.shortcut_validator import ShortcutValidator
from src.ui.shortcut_tile import ShortcutTile, REORDER_MIME
from src.ui.add_shortcut_dialog import NameConfirmDialog
from src.ui.styles import (
    BRONZE, TEXT_PRIMARY, TEXT_MUTED, BG_DARK, BORDER,
    STATUS_AVAILABLE, STATUS_UNAVAILABLE, STATUS_DEAD
)
from src.utils.logger import get_logger

logger = get_logger("ShopWindow")

_WM_MOUSEACTIVATE          = 0x0021
_MA_NOACTIVATE             = 3           # return value: don't activate on click
_WM_NCHITTEST              = 0x0084
_HTBOTTOM                  = 15          # resize from bottom edge

# OLE drag-and-drop registration diagnostics
_S_OK                      = 0x00000000
_DRAGDROP_E_NOTREGISTERED  = 0x80040100  # RevokeDragDrop: nothing was registered
_DRAGDROP_E_ALREADYREG     = 0x80040101  # RegisterDragDrop: already registered


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd",    ctypes.wintypes.HWND),
        ("message", ctypes.c_uint),
        ("wParam",  ctypes.wintypes.WPARAM),
        ("lParam",  ctypes.wintypes.LPARAM),
        ("time",    ctypes.wintypes.DWORD),
        ("pt",      ctypes.wintypes.POINT),
    ]

TILES_PER_ROW = 3
CORNER_RADIUS = 10

# Screen-relative sizing — calculated once at startup in _calc_dimensions()
# Targets ~22% of available screen width, clamped to a sensible range.
# Everything else derives from WINDOW_WIDTH so the layout always fits.
WINDOW_WIDTH = 420   # overwritten by _calc_dimensions() at runtime
TILE_SPACING = 10
TILE_MARGIN  = 16
TILE_W       = 116
TILE_H       = 104

# Resize constants
RESIZE_HANDLE_H = 6   # bottom strip that returns HTBOTTOM
HEADER_H        = 44
FOOTER_H        = 44
TOP_OFFSET      = 72  # same as _position_top_right y offset


def _calc_dimensions():
    """
    Derive window and tile dimensions from the primary screen's available width.
    Called once after QApplication exists.
    Updates module-level constants so ShortcutTile picks them up.
    """
    global WINDOW_WIDTH, TILE_SPACING, TILE_MARGIN, TILE_W, TILE_H
    from PySide6.QtWidgets import QApplication
    screen_w = QApplication.primaryScreen().availableGeometry().width()

    # 22% of screen width, clamped 320 px … 560 px
    WINDOW_WIDTH = max(320, min(560, int(screen_w * 0.22)))

    # Derive tile width so 3 tiles + spacing + margins fill the window exactly
    TILE_W = (WINDOW_WIDTH - TILE_MARGIN * 2 - TILE_SPACING * (TILES_PER_ROW - 1)) // TILES_PER_ROW
    TILE_H = int(TILE_W * 0.90)          # keep a pleasing aspect ratio
    TILE_SPACING = max(6, TILE_W // 12)
    TILE_MARGIN  = max(12, TILE_W // 8)


class _DropIndicator(QWidget):
    """Thin horizontal bronze line shown between tile rows during reorder drag."""

    _HEIGHT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self._HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(BRONZE))


class _ThinProgressBar(QWidget):
    """3 px progress bar overlaid on the bottom edge of the shop window.

    Shown during background shortcut validation so the user knows status
    dots are still being updated.  Transparent to mouse events so it
    never interferes with drag-and-drop or tile clicks.
    """

    _HEIGHT = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._maximum = 1
        self.setFixedHeight(self._HEIGHT)
        # Must not swallow mouse/drag events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def set_progress(self, value: int, maximum: int):
        self._value = value
        self._maximum = max(1, maximum)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        ratio = min(1.0, self._value / self._maximum)
        filled = int(self.width() * ratio)
        if filled > 0:
            painter.fillRect(0, 0, filled, self._HEIGHT, QColor(BRONZE))
        if filled < self.width():
            painter.fillRect(
                filled, 0, self.width() - filled, self._HEIGHT,
                QColor(40, 40, 40, 100),
            )


class ShopWindow(QWidget):

    def __init__(self):
        super().__init__()
        _calc_dimensions()   # must run after QApplication exists

        self.config = ConfigManager()
        self.vdm = VirtualDesktopManager()
        self.config.load_profile()

        self._drag_pos: QPoint | None = None
        self._manage_visible = False
        self._tiles: dict[str, ShortcutTile] = {}   # shortcut_id → tile
        self._active_desktop: dict | None = None
        self._current_vd_name: str | None = None     # raw Windows desktop name
        self._last_vd_id = None                      # tracks desktop switches
        self._validator: ShortcutValidator | None = None
        self._validation_total = 0
        self._validation_done = 0
        self._drop_registered = False    # True once RegisterDragDrop is verified
        self._in_adjust_size = False     # guard: prevent resizeEvent capturing height during adjustSize
        self._grid_widget: QWidget | None = None  # ref to tile grid container
        self._drop_insert_index: int | None = None  # insertion index during reorder drag
        self._reorder_drag_active = False            # True while internal tile drag is in progress

        # Load persisted window height (None = auto-size to content)
        ws = self.config._profile.get("window_state", {})
        self._user_height: int | None = ws.get("shop_height")

        self._setup_window()
        self._build_ui()
        self._progress_bar = _ThinProgressBar(self)  # overlay, not in layout
        self._progress_bar.raise_()
        self._detect_and_load_desktop()
        self._position_top_right()
        self._start_desktop_poll()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool              # no taskbar entry; desktop-widget behaviour
        )
        # WA_TranslucentBackground is intentionally NOT used here.
        # It causes Qt to use UpdateLayeredWindow (per-pixel alpha), which makes
        # Windows 11 24H2 skip this window entirely for OLE drag-and-drop routing.
        # Rounded corners are achieved via setMask() in _apply_mask() instead.
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)
        self.setAutoFillBackground(False)
        self.setFixedWidth(WINDOW_WIDTH)
        # WM_TASKBARCREATED is broadcast by Explorer to all top-level windows when
        # it finishes initialising (including at boot and after Explorer restarts).
        # We use it to re-register our OLE IDropTarget after the shell is ready.
        self._WM_TASKBARCREATED = ctypes.windll.user32.RegisterWindowMessageW("TaskbarCreated")
        logger.debug(
            f"Screen-relative sizing: window={WINDOW_WIDTH}px "
            f"tile={TILE_W}×{TILE_H}px spacing={TILE_SPACING}px"
        )

    def _position_top_right(self):
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 24
        y = screen.top() + 72   # clear Windows title bars and system tray area
        self.move(x, y)

    # ------------------------------------------------------------------
    # Height management (vertical resize support)
    # ------------------------------------------------------------------

    def _update_window_height(self):
        """Set window height respecting user-dragged height if set."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        max_h = screen.height() - TOP_OFFSET - 12
        min_h = self._compute_min_height()

        self.setMinimumHeight(min_h)
        self.setMaximumHeight(max_h)

        if self._user_height is not None:
            target = max(min_h, min(max_h, self._user_height))
            self.resize(WINDOW_WIDTH, target)
        else:
            self._in_adjust_size = True
            self.adjustSize()
            self._in_adjust_size = False

    def _compute_min_height(self) -> int:
        """Minimum window height: header + 1 tile row + body margins + footer."""
        body_margin_v = (TILE_MARGIN - 4) * 2
        min_body = TILE_H + body_margin_v
        manage_h = self._manage_panel.sizeHint().height() if self._manage_visible else 0
        return HEADER_H + min_body + FOOTER_H + manage_h + 2  # +2 for root margins

    def _persist_height(self):
        """Save the user-chosen window height to profile."""
        if self._user_height is not None:
            self.config._profile.setdefault("window_state", {})["shop_height"] = self._user_height
            self.config.save_profile()

    def _send_to_bottom(self):
        """Keep window in normal z-order (not topmost, not behind desktop icons).

        WS_EX_NOACTIVATE is intentionally NOT set here — it signals to the shell
        that the window cannot receive user input, which causes Windows 11 to skip
        it entirely for OLE drag-and-drop routing.  Focus-steal prevention is
        handled instead via WM_MOUSEACTIVATE in nativeEvent.
        """
        try:
            import win32gui
            import win32con
            hwnd = int(self.winId())
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            )
        except Exception as e:
            logger.debug(f"_send_to_bottom failed: {e}")

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Root layout — no margins (we paint border ourselves)
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        # Inner container — must be fully transparent so the window's
        # paintEvent translucency shows through
        self._inner = QWidget()
        self._inner.setObjectName("shopInner")
        self._inner.setAutoFillBackground(False)
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._inner.setStyleSheet("QWidget#shopInner { background: transparent; }")
        inner_layout = QVBoxLayout(self._inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        inner_layout.addWidget(self._build_header())
        inner_layout.addWidget(self._build_body())
        inner_layout.addWidget(self._build_footer())

        # Manage panel — hidden by default
        self._manage_panel = self._build_manage_panel()
        self._manage_panel.setVisible(False)
        inner_layout.addWidget(self._manage_panel)

        root.addWidget(self._inner)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(
            "background: transparent;"
            f"border-bottom: 1px solid rgba(80,80,80,120);"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 0, 10, 0)

        # Bronze diamond accent
        accent = QLabel("◆")
        accent.setStyleSheet(f"color: {BRONZE}; font-size: 10px; background: transparent;")
        layout.addWidget(accent)

        # Desktop name
        self._desktop_name_label = QLabel("—")
        self._desktop_name_label.setStyleSheet(
            f"color: {BRONZE}; font-family: Segoe UI; font-size: 14px;"
            "font-weight: bold; background: transparent;"
        )
        layout.addWidget(self._desktop_name_label)
        layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #888888; border: none; font-size: 13px; }"
            "QPushButton:hover { color: #E8E8E8; }"
        )
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return header

    def _build_body(self) -> QScrollArea:
        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(TILE_MARGIN, TILE_MARGIN - 4, TILE_MARGIN, TILE_MARGIN - 4)
        self._body_layout.setSpacing(0)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidget(self._body)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Enable acceptDrops on intermediate widgets so reorder drags reach ShopWindow
        self._scroll_area.setAcceptDrops(True)
        self._body.setAcceptDrops(True)
        self._scroll_area.viewport().setAcceptDrops(True)
        # Install event filter to forward drag/drop events to ShopWindow
        self._scroll_area.installEventFilter(self)
        self._scroll_area.viewport().installEventFilter(self)
        self._body.installEventFilter(self)

        self._scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
            "QScrollBar:vertical { background: rgba(30,30,30,0); width: 6px; }"
            f"QScrollBar::handle:vertical {{ background: rgba(80,80,80,160); border-radius: 3px; min-height: 20px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: rgba(184,149,106,200); }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        self._scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return self._scroll_area

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(44)
        footer.setStyleSheet(
            "background: transparent;"
            f"border-top: 1px solid rgba(80,80,80,120);"
        )
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        # Add Shortcut
        self._btn_add = self._footer_btn("+ Shortcut")
        self._btn_add.clicked.connect(self._on_add_shortcut)
        layout.addWidget(self._btn_add)

        # Manage toggle
        self._btn_manage = self._footer_btn("✎ Manage")
        self._btn_manage.setCheckable(True)
        self._btn_manage.clicked.connect(self._on_toggle_manage)
        layout.addWidget(self._btn_manage)

        layout.addStretch()

        # Backup
        btn_backup = self._footer_btn("💾")
        btn_backup.setFixedWidth(36)
        btn_backup.setToolTip("Backup profile")
        btn_backup.clicked.connect(self._on_backup)
        layout.addWidget(btn_backup)

        # Import
        btn_import = self._footer_btn("📥")
        btn_import.setFixedWidth(36)
        btn_import.setToolTip("Import profile")
        btn_import.clicked.connect(self._on_import)
        layout.addWidget(btn_import)

        # Status badge (shows problem count)
        self._btn_status = self._footer_btn("●")
        self._btn_status.setFixedWidth(36)
        self._btn_status.setToolTip("All shortcuts OK")
        self._btn_status.setStyleSheet(
            self._btn_status.styleSheet() +
            f"QPushButton {{ color: {STATUS_AVAILABLE}; }}"
        )
        self._btn_status.clicked.connect(self._on_show_status)
        layout.addWidget(self._btn_status)

        return footer

    def _build_manage_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(
            f"background: rgba(20,20,20,140);"
            f"border-top: 1px solid rgba(80,80,80,120);"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        # Section: open full Control Panel
        open_btn = QPushButton("Open Full Control Panel")
        open_btn.setStyleSheet(self._manage_btn_style())
        open_btn.clicked.connect(self._on_open_control_panel)
        layout.addWidget(open_btn)

        # Section: shortcuts list for active desktop
        sc_header = QLabel("Shortcuts on this desktop")
        sc_header.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(sc_header)

        self._manage_sc_list = QWidget()
        self._manage_sc_list.setStyleSheet("background: transparent;")
        self._manage_sc_list_layout = QVBoxLayout(self._manage_sc_list)
        self._manage_sc_list_layout.setContentsMargins(0, 0, 0, 0)
        self._manage_sc_list_layout.setSpacing(4)
        layout.addWidget(self._manage_sc_list)

        return panel

    # ------------------------------------------------------------------
    # Desktop detection & tile rendering
    # ------------------------------------------------------------------

    def _detect_and_load_desktop(self):
        """Detect which virtual desktop is active and populate the shop window."""
        try:
            from pyvda import VirtualDesktop
            _current_vd = VirtualDesktop.current()
            self._last_vd_id = _current_vd.id if _current_vd else None
            if _current_vd:
                vd_name = (_current_vd.name or "").strip()
                self._current_vd_name = vd_name if vd_name else f"Desktop {_current_vd.number}"
            else:
                self._current_vd_name = None
        except Exception as e:
            logger.error(f"Could not detect current desktop: {e}")
            self._last_vd_id = None
            self._current_vd_name = None

        # Match profile entry — by Windows VD GUID first (reliable), then by name
        self._active_desktop = None
        vd_id_str = str(self._last_vd_id) if self._last_vd_id else None

        for desktop in self.config.get_all_desktops():
            if vd_id_str and desktop.get("windows_vd_id") == vd_id_str:
                self._active_desktop = desktop
                break

        if self._active_desktop is None and self._current_vd_name:
            for desktop in self.config.get_all_desktops():
                if desktop["name"].strip().lower() == self._current_vd_name.lower():
                    self._active_desktop = desktop
                    # Write the GUID back so future matches use it
                    if vd_id_str and not desktop.get("windows_vd_id"):
                        self.config.update_desktop(desktop["id"], {"windows_vd_id": vd_id_str})
                    break

        self._render_body()
        self._refresh_manage_list()

    def _render_body(self):
        """Clear body and render correct state based on active desktop."""
        # Clear existing body contents (widgets, spacers, and stretch items)
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tiles.clear()
        self._grid_widget = None

        if self._active_desktop is None:
            self._render_unrecognised()
        else:
            shortcuts = self._active_desktop.get("shortcuts", [])
            self._desktop_name_label.setText(self._current_vd_name or self._active_desktop["name"])
            if shortcuts:
                self._render_tile_grid(shortcuts)
            else:
                self._render_empty_desktop()

        self._update_window_height()

    def _render_tile_grid(self, shortcuts: list):
        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid_widget.setAcceptDrops(True)
        self._grid_widget.installEventFilter(self)
        self._grid_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        grid_layout = QGridLayout(self._grid_widget)
        grid_layout.setHorizontalSpacing(TILE_SPACING)
        grid_layout.setVerticalSpacing(TILE_SPACING)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        num_rows = (len(shortcuts) + TILES_PER_ROW - 1) // TILES_PER_ROW

        for i, sc in enumerate(shortcuts):
            tile = ShortcutTile(sc, tile_w=TILE_W, tile_h=TILE_H)
            row, col = divmod(i, TILES_PER_ROW)
            grid_layout.addWidget(tile, row, col)
            self._tiles[sc["id"]] = tile

        # Fill empty cells in last row so layout stays left-aligned
        remainder = len(shortcuts) % TILES_PER_ROW
        if remainder:
            for col in range(remainder, TILES_PER_ROW):
                spacer = QWidget()
                spacer.setFixedSize(TILE_W, TILE_H)
                spacer.setStyleSheet("background: transparent;")
                last_row = num_rows - 1
                grid_layout.addWidget(spacer, last_row, col)

        # Fix each row height so no row stretches beyond its tile height
        for r in range(num_rows):
            grid_layout.setRowMinimumHeight(r, TILE_H)
            grid_layout.setRowStretch(r, 0)

        self._body_layout.addWidget(self._grid_widget)
        self._body_layout.addStretch(1)

        # Drop indicator overlay (child of body so it scrolls with content)
        self._drop_indicator = _DropIndicator(parent=self._body)
        self._drop_indicator.setFixedWidth(WINDOW_WIDTH - TILE_MARGIN * 2)

    def _render_unrecognised(self):
        name = self._current_vd_name or "This Desktop"
        self._desktop_name_label.setText(name)
        self._render_placeholder()

    def _render_empty_desktop(self):
        self._render_placeholder()

    def _render_placeholder(self):
        msg = QLabel("No shortcuts for this desktop.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; background: transparent;"
            "padding: 28px 0;"
        )
        self._body_layout.addWidget(msg)

    # ------------------------------------------------------------------
    # Manage panel list
    # ------------------------------------------------------------------

    def _refresh_manage_list(self):
        while self._manage_sc_list_layout.count():
            item = self._manage_sc_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._active_desktop is None:
            return

        for sc in self._active_desktop.get("shortcuts", []):
            row = self._build_manage_row(sc)
            self._manage_sc_list_layout.addWidget(row)

        if not self._active_desktop.get("shortcuts"):
            empty = QLabel("No shortcuts yet.")
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
            self._manage_sc_list_layout.addWidget(empty)

    def _build_manage_row(self, sc: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: rgba(40,40,40,180); border-radius: 4px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        icon_map = {"folder": "📁", "app": "⚙", "file": "📄"}
        icon = QLabel(icon_map.get(sc.get("type", "file"), "📄"))
        icon.setFixedWidth(20)
        icon.setStyleSheet("background: transparent; font-size: 13px;")
        layout.addWidget(icon)

        label = QLabel(sc.get("label", ""))
        label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; background: transparent;")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(label)

        status_map = {"available": "✅", "unavailable": "⚠️", "dead": "❌"}
        status_icon = QLabel(status_map.get(sc.get("status"), "●"))
        status_icon.setStyleSheet("background: transparent; font-size: 11px;")
        layout.addWidget(status_icon)

        remove_btn = QPushButton("🗑")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 13px; color: #888; }"
            "QPushButton:hover { color: #C0392B; }"
        )
        sc_id = sc["id"]
        remove_btn.clicked.connect(lambda checked=False, sid=sc_id: self._on_remove_shortcut(sid))
        layout.addWidget(remove_btn)

        return row

    # ------------------------------------------------------------------
    # Virtual desktop polling — refresh when user switches desktops
    # ------------------------------------------------------------------

    def _start_desktop_poll(self):
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._on_poll_desktop)
        self._poll_timer.start()

    def _on_poll_desktop(self):
        try:
            from pyvda import VirtualDesktop
            current_vd = VirtualDesktop.current()
            vd_id = current_vd.id if current_vd else None
        except Exception:
            return

        if vd_id != self._last_vd_id:
            self._last_vd_id = vd_id
            self.config.load_profile()          # pick up any changes since last switch
            self._detect_and_load_desktop()

    # ------------------------------------------------------------------
    # Validation — update tile dots after background thread
    # ------------------------------------------------------------------

    def start_validation(self):
        """Called after the window is shown to start background path validation."""
        profile = self.config._profile
        if not profile:
            return
        self._validation_total = sum(
            len(d.get("shortcuts", [])) for d in profile.get("desktops", [])
        )
        self._validation_done = 0
        if self._validation_total > 0:
            self._progress_bar.set_progress(0, self._validation_total)
            self._progress_bar.show()
        self._validator = ShortcutValidator(profile)
        self._validator.shortcut_validated.connect(self._on_shortcut_validated)
        self._validator.validation_complete.connect(self._on_validation_complete)
        self._validator.start()

    def _on_shortcut_validated(self, desktop_id: str, shortcut_id: str, status: str):
        self.config.update_shortcut_status(desktop_id, shortcut_id, status)
        if shortcut_id in self._tiles:
            self._tiles[shortcut_id].set_status(status)
        # Refresh manage list status icons if open
        if self._manage_visible:
            self._refresh_manage_list()
        self._validation_done += 1
        self._progress_bar.set_progress(self._validation_done, self._validation_total)

    def _on_validation_complete(self, counts: dict):
        # Keep the bar visible for at least 800 ms so the user can see it
        # (local paths validate in <1 s and the bar would otherwise flash away
        # before the first repaint).
        QTimer.singleShot(800, self._progress_bar.hide)
        problems = counts.get("unavailable", 0) + counts.get("dead", 0)
        if problems:
            self._btn_status.setToolTip(
                f"{counts.get('unavailable',0)} unavailable, {counts.get('dead',0)} dead"
            )
            self._btn_status.setStyleSheet(
                self._footer_btn_base_style() +
                f"QPushButton {{ color: {STATUS_UNAVAILABLE}; }}"
            )
        else:
            self._btn_status.setToolTip("All shortcuts OK")
            self._btn_status.setStyleSheet(
                self._footer_btn_base_style() +
                f"QPushButton {{ color: {STATUS_AVAILABLE}; }}"
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_shortcut(self):
        if self._active_desktop is None:
            # Auto-create a profile entry for this Windows desktop on first shortcut add
            name = self._current_vd_name or "New Desktop"
            vd_id_str = str(self._last_vd_id) if self._last_vd_id else None
            self._active_desktop = self.config.add_desktop(name, windows_vd_id=vd_id_str)
            logger.info(f"Auto-created profile entry for desktop: {name} (vd_id: {vd_id_str})")
        from src.ui.add_shortcut_dialog import AddShortcutDialog
        dialog = AddShortcutDialog(self)
        result = dialog.exec_dialog()
        if result is None:
            return

        target_path, label = result
        sc_type = _infer_type(target_path)

        lnk_path = create_lnk(target_path, label, self._active_desktop["id"])

        shortcut = {
            "label": label,
            "type":  sc_type,
            "path":  target_path,
            "lnk_path": lnk_path,
            "status": validate_path(target_path),
        }
        self.config.add_shortcut(self._active_desktop["id"], shortcut)
        self._active_desktop = self.config.get_desktop_by_id(self._active_desktop["id"])
        self._render_body()
        self._refresh_manage_list()

    def _on_remove_shortcut(self, shortcut_id: str):
        if self._active_desktop is None:
            return

        sc = self.config.get_shortcut_by_id(self._active_desktop["id"], shortcut_id)
        label = sc.get("label", shortcut_id) if sc else shortcut_id

        reply = QMessageBox.question(
            self, "Remove Shortcut",
            f"Remove '{label}' from {self._active_desktop['name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete the .lnk file
        if sc and sc.get("lnk_path"):
            from src.core.shortcut_manager import delete_lnk
            delete_lnk(sc["lnk_path"])

        self.config.remove_shortcut(self._active_desktop["id"], shortcut_id)
        self._active_desktop = self.config.get_desktop_by_id(self._active_desktop["id"])
        self._render_body()
        self._refresh_manage_list()

    def _on_toggle_manage(self):
        self._manage_visible = not self._manage_visible
        self._manage_panel.setVisible(self._manage_visible)
        self._btn_manage.setChecked(self._manage_visible)
        if self._manage_visible:
            self._refresh_manage_list()
        self._update_window_height()

    def _on_open_control_panel(self):
        """Open the full management Control Panel window."""
        from src.ui.control_panel import ControlPanel
        self._cp = ControlPanel()
        self._cp.show()

    def _on_backup(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"DesktopWorkspaces_Backup_{ts}.json"
        docs = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", os.path.join(docs, default_name),
            "JSON Files (*.json)"
        )
        if not path:
            return
        ok = self.config.backup_profile(path)
        if ok:
            QMessageBox.information(self, "Backup Saved", f"✓ Backup saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Backup Failed", "Could not save backup. Check logs.")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "JSON Files (*.json)"
        )
        if not path:
            return

        # Preview
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                incoming = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Cannot read file:\n{e}")
            return

        current = self.config.profile_summary()
        incoming_desktops = len(incoming.get("desktops", []))
        incoming_shortcuts = sum(
            len(d.get("shortcuts", [])) for d in incoming.get("desktops", [])
        )

        reply = QMessageBox.question(
            self, "Import Profile",
            f"Replace current profile with this backup?\n\n"
            f"Current:  {current['desktops']} desktops, {current['shortcuts']} shortcuts\n"
            f"Backup:   {incoming_desktops} desktops, {incoming_shortcuts} shortcuts\n\n"
            f"Your current profile will be backed up automatically.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        ok, msg = self.config.import_profile(path)
        if ok:
            self._detect_and_load_desktop()
            QMessageBox.information(self, "Import Complete", f"✓ {msg}")
        else:
            QMessageBox.warning(self, "Import Failed", msg)

    def _on_show_status(self):
        if self._active_desktop is None:
            return
        shortcuts = self._active_desktop.get("shortcuts", [])
        problems = [
            s for s in shortcuts
            if s.get("status") in ("unavailable", "dead")
        ]
        if not problems:
            QMessageBox.information(self, "Shortcut Status", "All shortcuts are available. ✅")
            return
        lines = []
        for s in problems:
            icon = "⚠️" if s.get("status") == "unavailable" else "❌"
            lines.append(f"{icon}  {s['label']}\n    {s['path']}")
        QMessageBox.warning(self, "Shortcut Status", "\n\n".join(lines))

    # ------------------------------------------------------------------
    # Drag-and-drop — OLE IDropTarget (via Qt setAcceptDrops)
    # WM_DROPFILES confirmed dead on Win 11 24H2 for WS_EX_LAYERED windows.
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        """Forward drag/drop events from child widgets to ShopWindow."""
        t = event.type()
        if t == QEvent.Type.DragEnter:
            self.dragEnterEvent(event)
            return True
        if t == QEvent.Type.DragMove:
            self.dragMoveEvent(event)
            return True
        if t == QEvent.Type.DragLeave:
            self.dragLeaveEvent(event)
            return True
        if t == QEvent.Type.Drop:
            self.dropEvent(event)
            return True
        return super().eventFilter(obj, event)

    def nativeEvent(self, event_type, message):
        """Handle WM_NCHITTEST, WM_MOUSEACTIVATE, and WM_TASKBARCREATED."""
        if event_type == b"windows_generic_MSG":
            try:
                msg = _MSG.from_address(int(message))
                # Bottom-edge resize handle
                if msg.message == _WM_NCHITTEST:
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    rel_y = y - self.frameGeometry().top()
                    if rel_y >= self.height() - RESIZE_HANDLE_H:
                        return True, _HTBOTTOM
                if msg.message == _WM_MOUSEACTIVATE and not self._reorder_drag_active:
                    return True, _MA_NOACTIVATE
                if msg.message == self._WM_TASKBARCREATED:
                    logger.debug("WM_TASKBARCREATED received — re-registering OLE drop target")
                    self._drop_registered = False   # force fresh registration
                    QTimer.singleShot(1000, self._do_register_drop)
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(REORDER_MIME):
            self._reorder_drag_active = True
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(REORDER_MIME):
            event.acceptProposedAction()
            self._show_drop_indicator()
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._reorder_drag_active = False
        self._hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._reorder_drag_active = False
        if event.mimeData().hasFormat(REORDER_MIME):
            event.acceptProposedAction()
            sc_id = event.mimeData().data(REORDER_MIME).data().decode("utf-8")
            insert_idx = self._drop_insert_index   # save before hide clears it
            self._hide_drop_indicator()
            self._on_reorder_drop(sc_id, insert_idx)
            return
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        event.acceptProposedAction()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._handle_drop(path)

    # ------------------------------------------------------------------
    # Reorder drop handling
    # ------------------------------------------------------------------

    def _show_drop_indicator(self, pos: QPoint = None):
        """Position the drop indicator line based on cursor position."""
        if self._grid_widget is None or not hasattr(self, '_drop_indicator'):
            return
        shortcuts = self._active_desktop.get("shortcuts", []) if self._active_desktop else []
        n = len(shortcuts)
        if n == 0:
            self._drop_indicator.hide()
            return

        # Use global cursor position — reliable regardless of which child widget
        # the event was forwarded from via eventFilter
        grid_pos = self._grid_widget.mapFromGlobal(QCursor.pos())
        gy = grid_pos.y()

        row_height = TILE_H + TILE_SPACING
        num_rows = (n + TILES_PER_ROW - 1) // TILES_PER_ROW
        row = max(0, gy // row_height)

        # Snap: top half of row → insert before, bottom half → insert after
        row_local_y = gy - row * row_height
        if row_local_y < row_height // 2:
            insert_before_row = row
        else:
            insert_before_row = row + 1
        insert_before_row = max(0, min(insert_before_row, num_rows))

        # Column-aware insertion within a row
        gx = grid_pos.x()
        col_width = TILE_W + TILE_SPACING
        col = max(0, min(gx // col_width, TILES_PER_ROW - 1))

        if insert_before_row < num_rows:
            self._drop_insert_index = min(insert_before_row * TILES_PER_ROW + col, n)
        else:
            self._drop_insert_index = n

        # Position the indicator line (in _body coordinates)
        grid_top_in_body = self._grid_widget.pos().y()
        indicator_y = grid_top_in_body + insert_before_row * row_height - _DropIndicator._HEIGHT // 2
        # Clamp so it doesn't go above the grid
        indicator_y = max(grid_top_in_body - _DropIndicator._HEIGHT, indicator_y)

        self._drop_indicator.move(TILE_MARGIN, indicator_y)
        self._drop_indicator.raise_()
        self._drop_indicator.show()

    def _hide_drop_indicator(self):
        if hasattr(self, '_drop_indicator'):
            self._drop_indicator.hide()
        self._drop_insert_index = None

    def _on_reorder_drop(self, sc_id: str, insert_idx: int | None = None):
        """Reorder shortcuts after a drag-and-drop within the grid."""
        if self._active_desktop is None:
            return
        shortcuts = self._active_desktop.get("shortcuts", [])
        if insert_idx is None:
            logger.warning("_on_reorder_drop: no insertion index")
            return

        ordered_ids = [sc["id"] for sc in shortcuts]
        if sc_id not in ordered_ids:
            logger.warning(f"_on_reorder_drop: '{sc_id}' not found")
            return

        src_idx = ordered_ids.index(sc_id)
        ordered_ids.pop(src_idx)

        # Adjust insertion index when source was before target
        adj = insert_idx if src_idx >= insert_idx else insert_idx - 1
        adj = max(0, min(adj, len(ordered_ids)))
        ordered_ids.insert(adj, sc_id)

        desktop_id = self._active_desktop["id"]
        if self.config.reorder_shortcuts(desktop_id, ordered_ids):
            self._active_desktop = self.config.get_desktop_by_id(desktop_id)
            self._render_body()
            if self._manage_visible:
                self._refresh_manage_list()
            logger.info(f"Shortcuts reordered for desktop '{desktop_id}'")

    def _handle_drop(self, path: str):
        """Process a single dropped path — .lnk or any file/folder."""
        original_desktop_path: str | None = None

        if path.lower().endswith(".lnk"):
            resolved = extract_lnk_target(path)
            # If the .lnk lives on the shared desktop, remember it for removal prompt
            try:
                if os.path.normcase(os.path.dirname(path)) == os.path.normcase(DESKTOP_DIR):
                    original_desktop_path = path
            except Exception:
                pass
            target_path = resolved if resolved else path
        else:
            target_path = path

        # Auto-create profile entry if no active desktop
        if self._active_desktop is None:
            name = self._current_vd_name or "New Desktop"
            vd_id_str = str(self._last_vd_id) if self._last_vd_id else None
            self._active_desktop = self.config.add_desktop(name, windows_vd_id=vd_id_str)
            logger.info(f"_handle_drop: auto-created desktop '{name}'")

        # Duplicate check
        existing_paths = [
            sc.get("path", "") for sc in self._active_desktop.get("shortcuts", [])
        ]
        if target_path in existing_paths:
            QMessageBox.information(
                self, "Already Added",
                f"'{os.path.basename(target_path)}' is already in this desktop."
            )
            return

        auto_name = get_display_name(target_path)
        dialog = NameConfirmDialog(auto_name, target_path, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        label = dialog.get_name()

        lnk_path = create_lnk(target_path, label, self._active_desktop["id"])
        sc_type = _infer_type(target_path)
        shortcut = {
            "label": label,
            "type":  sc_type,
            "path":  target_path,
            "lnk_path": lnk_path,
            "status": validate_path(target_path),
        }
        self.config.add_shortcut(self._active_desktop["id"], shortcut)
        self._active_desktop = self.config.get_desktop_by_id(self._active_desktop["id"])
        self._render_body()
        self._refresh_manage_list()

        logger.info(f"_handle_drop: added '{label}' → {target_path}")

        # Offer to remove the original .lnk from the shared desktop
        if original_desktop_path:
            reply = QMessageBox.question(
                self, "Remove Original",
                f"Remove the original shortcut from the Desktop?\n{os.path.basename(original_desktop_path)}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(original_desktop_path)
                except Exception as e:
                    QMessageBox.warning(
                        self, "Remove Failed",
                        f"Could not delete original shortcut:\n{e}"
                    )

    # ------------------------------------------------------------------
    # Z-order — stay at desktop level
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_mask()
        QTimer.singleShot(50, self._send_to_bottom)
        self._reposition_progress_bar()
        # Start OLE drop-target registration.  _poll_shell_and_register() waits
        # until Shell_TrayWnd exists (proof the taskbar is running), then calls
        # setAcceptDrops(True).  Periodic re-registration for 5 minutes catches
        # any invalidation caused by Explorer rebuilding its OLE dispatch table.
        if not self._drop_registered:
            QTimer.singleShot(0, self._poll_shell_and_register)

    def _poll_shell_and_register(self):
        """Poll for Explorer's taskbar window, then kick off OLE registration.

        Shell_TrayWnd is Explorer's taskbar window — its existence means the
        shell is running.  The shop window is now launched by Task Scheduler
        with a 30-second delay after logon, so Explorer's OLE infrastructure
        is already stable by the time we get here.  A brief 500 ms buffer is
        kept just for safety, but the old 3-second wait is no longer needed.
        """
        if self._drop_registered:
            return
        if ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None):
            logger.debug("Shell_TrayWnd found — registering OLE drop target in 500 ms")
            QTimer.singleShot(500, self._do_register_drop)
        else:
            logger.debug("Waiting for Shell_TrayWnd…")
            QTimer.singleShot(500, self._poll_shell_and_register)

    def _do_register_drop(self):
        """Register OLE IDropTarget via Qt's setAcceptDrops.

        Previous implementations used RevokeDragDrop as a "probe" to verify
        registration.  This was DESTRUCTIVE — it removed the working registration,
        and the subsequent re-registration via setAcceptDrops(True) did not always
        call RegisterDragDrop again internally (PySide6 caching).  Result: the log
        said "registered" but drops silently stopped working.

        New approach: just register, trust it, and periodically re-register for
        5 minutes as a safety net (handles boot-time OLE instability and Explorer
        restarts).  The 30-second startup delay already ensures OLE is stable for
        the normal boot path.
        """
        hwnd = int(self.winId())
        self.setAcceptDrops(False)
        self.setAcceptDrops(True)
        logger.debug(f"OLE IDropTarget registered (HWND={hwnd:#010x})")
        self._drop_registered = True

        # Periodic re-registration: every 30 s for 5 minutes.
        # Catches boot-time OLE instability and Explorer restarts that
        # invalidate our IDropTarget registration.
        self._reregister_count = 0
        if not hasattr(self, '_reregister_timer') or self._reregister_timer is None:
            self._reregister_timer = QTimer(self)
            self._reregister_timer.timeout.connect(self._periodic_reregister)
        self._reregister_timer.start(30000)

    def _periodic_reregister(self):
        """Re-register OLE IDropTarget periodically as a safety net."""
        self._reregister_count += 1
        if self._reregister_count > 10:  # 5 minutes (10 × 30 s)
            self._reregister_timer.stop()
            logger.debug("OLE periodic re-registration complete (5 min)")
            return
        hwnd = int(self.winId())
        self.setAcceptDrops(False)
        self.setAcceptDrops(True)
        logger.debug(
            f"OLE periodic re-registration #{self._reregister_count} (HWND={hwnd:#010x})"
        )

    # ------------------------------------------------------------------
    # Drag to move (by header)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag from header area (top 44px)
            if event.position().y() <= 44:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Paint — window border and background
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QBrush(QColor(18, 18, 18)))   # solid — no per-pixel alpha
        painter.setPen(QPen(QColor(BRONZE), 1.5))
        painter.drawRoundedRect(rect, CORNER_RADIUS, CORNER_RADIUS)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_mask()
        self._reposition_progress_bar()
        # Capture user-dragged height (skip when triggered by adjustSize)
        if not self._in_adjust_size and event.oldSize().height() > 0:
            if event.oldSize().height() != event.size().height():
                self._user_height = event.size().height()
                self._persist_height()

    def _reposition_progress_bar(self):
        """Keep the progress bar pinned to the bottom edge regardless of window height."""
        if hasattr(self, "_progress_bar"):
            h = _ThinProgressBar._HEIGHT
            self._progress_bar.setGeometry(0, self.height() - h, self.width(), h)

    def _apply_mask(self):
        """Clip the window to a rounded rectangle so corners look clean."""
        from PySide6.QtGui import QRegion, QPainterPath
        path = QPainterPath()
        path.addRoundedRect(self.rect(), CORNER_RADIUS, CORNER_RADIUS)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------

    def _footer_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(self._footer_btn_base_style())
        return btn

    @staticmethod
    def _footer_btn_base_style() -> str:
        return (
            f"QPushButton {{ background: rgba(50,50,50,180); color: {TEXT_PRIMARY};"
            f"border: 1px solid rgba(80,80,80,150); border-radius: 4px;"
            f"padding: 4px 10px; font-family: Segoe UI; font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(70,70,70,200); border-color: {BRONZE}; }}"
            f"QPushButton:checked {{ background: rgba(80,60,30,200); border-color: {BRONZE}; }}"
        )

    @staticmethod
    def _primary_btn_style() -> str:
        return (
            f"QPushButton {{ background: {BRONZE}; color: #1A1A1A; font-weight: bold;"
            f"border: none; border-radius: 4px; padding: 7px 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ background: #7DD4F8; }}"
        )

    @staticmethod
    def _manage_btn_style() -> str:
        return (
            f"QPushButton {{ background: rgba(50,50,50,180); color: {TEXT_PRIMARY};"
            f"border: 1px solid rgba(80,80,80,150); border-radius: 4px;"
            f"padding: 6px 14px; font-family: Segoe UI; font-size: 12px; }}"
            f"QPushButton:hover {{ background: rgba(70,70,70,200); border-color: {BRONZE}; }}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_type(path: str) -> str:
    if os.path.isdir(path):
        return "folder"
    if path.lower().endswith(".exe"):
        return "app"
    return "file"
