"""
ShortcutManager: create, delete, and validate .lnk shortcuts.
Also responsible for placing the Control Panel shortcut on the shared Desktop.
"""

import os
import sys
import concurrent.futures
import winreg
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo

from src.utils.logger import get_logger

logger = get_logger("ShortcutManager")


def _get_desktop_dir() -> str:
    """
    Return the real Desktop folder path from the Registry.
    Handles OneDrive-redirected Desktops correctly.
    Falls back to %USERPROFILE%\\Desktop if the Registry key is unavailable.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        path, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        return path
    except OSError:
        return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DesktopWorkspaces")
SHORTCUTS_DIR = os.path.join(APP_DIR, "shortcuts")
ICONS_DIR = os.path.join(APP_DIR, "icons")
DESKTOP_DIR = _get_desktop_dir()

# Project root = three levels up from this file (src/core/shortcut_manager.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_SCRIPT = str(_PROJECT_ROOT / "main.py")

CONTROL_PANEL_LNK_NAME = "Desktop Workspaces.lnk"
CONTROL_PANEL_LNK_PATH = os.path.join(DESKTOP_DIR, CONTROL_PANEL_LNK_NAME)

VALIDATION_TIMEOUT = 3  # seconds


# ---------------------------------------------------------------------------
# Display name
# ---------------------------------------------------------------------------

def get_display_name(target_path: str) -> str:
    """
    Extract a clean label from a file or folder path.
    'C:\\Program Files\\Adobe\\Photoshop\\Photoshop.exe' → 'Photoshop'
    'C:\\Users\\Bernard\\Projects\\Design'               → 'Design'
    """
    name = Path(target_path).stem  # strips extension
    return name if name else Path(target_path).name


# ---------------------------------------------------------------------------
# Create / delete .lnk
# ---------------------------------------------------------------------------

def create_lnk(target_path: str, label: str, desktop_id: str) -> str | None:
    """
    Create a .lnk shortcut for target_path, stored under:
        %LOCALAPPDATA%\\DesktopWorkspaces\\shortcuts\\{desktop_id}\\{label}.lnk

    Returns the path to the created .lnk, or None on failure.
    """
    try:
        import win32com.client  # noqa: PLC0415

        shortcut_dir = os.path.join(SHORTCUTS_DIR, desktop_id)
        os.makedirs(shortcut_dir, exist_ok=True)

        # Sanitise label for use as filename
        safe_label = _safe_filename(label)
        lnk_path = os.path.join(shortcut_dir, f"{safe_label}.lnk")

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = (
            str(Path(target_path).parent) if os.path.isfile(target_path) else target_path
        )
        shortcut.Description = label
        shortcut.save()

        logger.info(f"Created .lnk: '{label}' → {target_path}")
        return lnk_path

    except Exception as e:
        logger.error(f"Failed to create .lnk for '{label}': {e}")
        return None


def delete_lnk(lnk_path: str) -> bool:
    """Delete a .lnk file. Returns True on success."""
    if not lnk_path or not os.path.exists(lnk_path):
        logger.debug(f"delete_lnk: file not found (already deleted?): {lnk_path}")
        return True
    try:
        os.remove(lnk_path)
        logger.info(f"Deleted .lnk: {lnk_path}")
        return True
    except OSError as e:
        logger.error(f"Failed to delete .lnk '{lnk_path}': {e}")
        return False


def extract_lnk_target(lnk_path: str) -> str | None:
    """Parse a .lnk file and return its target path, or None on failure."""
    try:
        import win32com.client  # noqa: PLC0415
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        return shortcut.TargetPath or None
    except Exception as e:
        logger.error(f"Failed to read .lnk target '{lnk_path}': {e}")
        return None


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def validate_path(target_path: str) -> str:
    """
    Check whether a path is accessible.
    Returns one of: "available", "unavailable", "dead"

    - "available"   — path exists and is reachable right now
    - "unavailable" — timed out (network path unreachable but may come back)
    - "dead"        — definitively does not exist (local path confirmed missing)
    """
    if not target_path:
        return "dead"

    is_network = target_path.startswith("\\\\") or target_path.startswith("//")

    if is_network:
        return _validate_with_timeout(target_path, VALIDATION_TIMEOUT)
    else:
        # Local path — fast check, no timeout needed
        return "available" if os.path.exists(target_path) else "dead"


def _validate_with_timeout(path: str, timeout: float) -> str:
    """Run os.path.exists in a thread with a timeout for network paths."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(os.path.exists, path)
        try:
            exists = future.result(timeout=timeout)
            return "available" if exists else "dead"
        except concurrent.futures.TimeoutError:
            logger.warning(f"Path validation timed out ({timeout}s): {path}")
            return "unavailable"
        except Exception as e:
            logger.error(f"Path validation error for '{path}': {e}")
            return "unavailable"


# ---------------------------------------------------------------------------
# Shell icon
# ---------------------------------------------------------------------------

def get_shell_icon(target_path: str) -> QIcon:
    """
    Return the Windows shell icon for target_path.
    Falls back to a generic file/folder/app icon if the path doesn't exist.
    """
    provider = QFileIconProvider()

    if os.path.exists(target_path):
        info = QFileInfo(target_path)
        return provider.icon(info)

    # Fallback based on extension / type hint
    if target_path.lower().endswith(".exe"):
        return provider.icon(QFileIconProvider.IconType.File)
    if os.path.sep in target_path or "/" in target_path:
        return provider.icon(QFileIconProvider.IconType.Folder)
    return provider.icon(QFileIconProvider.IconType.File)


# ---------------------------------------------------------------------------
# Control Panel shortcut (placed on the shared Desktop)
# ---------------------------------------------------------------------------

def place_control_panel_shortcut() -> bool:
    """
    Place 'Desktop Workspaces.lnk' in %USERPROFILE%\\Desktop if not already present.
    Target: pythonw.exe  Argument: main.py  (no console window)
    Returns True if the shortcut exists (was placed or already present).
    """
    if os.path.exists(CONTROL_PANEL_LNK_PATH):
        logger.debug("Control Panel shortcut already on Desktop.")
        return True

    pythonw = _find_pythonw()
    if not pythonw:
        logger.error("Cannot place Control Panel shortcut: pythonw.exe not found.")
        return False

    if not os.path.exists(MAIN_SCRIPT):
        logger.error(f"Cannot place Control Panel shortcut: main.py not found at {MAIN_SCRIPT}")
        return False

    try:
        import win32com.client  # noqa: PLC0415

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(CONTROL_PANEL_LNK_PATH)
        shortcut.TargetPath = pythonw
        shortcut.Arguments = f'"{MAIN_SCRIPT}"'
        shortcut.WorkingDirectory = str(_PROJECT_ROOT)
        shortcut.Description = "Desktop Workspaces Control Panel"
        shortcut.save()

        logger.info(f"Control Panel shortcut placed on Desktop: {CONTROL_PANEL_LNK_PATH}")
        return True

    except Exception as e:
        logger.error(f"Failed to place Control Panel shortcut: {e}")
        return False


def _find_pythonw() -> str | None:
    """Return path to pythonw.exe alongside the current interpreter."""
    python_dir = Path(sys.executable).parent
    candidates = [
        python_dir / "pythonw.exe",
        python_dir / "python.exe",  # fallback if pythonw not present
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


# ---------------------------------------------------------------------------
# Icon caching
# ---------------------------------------------------------------------------

def cache_icon(source_path: str, shortcut_id: str) -> str | None:
    """
    Cache the shell icon of source_path as a PNG in ICONS_DIR.

    For .url files: reads the IconFile field from the INI and loads it directly.
    For .lnk files: reads the IconLocation property via COM.
    Falls back to QFileIconProvider for everything else.

    Returns the PNG path, or None on failure.
    """
    try:
        os.makedirs(ICONS_DIR, exist_ok=True)
        png_path = os.path.join(ICONS_DIR, f"{shortcut_id}.png")

        pixmap = _extract_custom_icon(source_path)

        if pixmap is None or pixmap.isNull():
            # Fallback: QFileIconProvider (generic file-type icon)
            provider = QFileIconProvider()
            icon = provider.icon(QFileInfo(source_path))
            pixmap = icon.pixmap(256, 256)

        if pixmap is None or pixmap.isNull():
            logger.warning(f"cache_icon: null pixmap for '{source_path}'")
            return None

        if pixmap.save(png_path, "PNG"):
            logger.info(f"Cached icon for '{shortcut_id}' → {png_path}")
            return png_path
        else:
            logger.warning(f"cache_icon: failed to save PNG for '{source_path}'")
            return None
    except Exception as e:
        logger.error(f"cache_icon failed for '{source_path}': {e}")
        return None


def _extract_custom_icon(source_path: str):
    """
    Try to extract the real custom icon from a .url or .lnk file.
    Returns a QPixmap or None.
    """
    from PySide6.QtGui import QPixmap, QImage

    lower = source_path.lower()

    # --- .url files: read IconFile from INI ---
    if lower.endswith(".url"):
        icon_file = _read_url_icon_file(source_path)
        if icon_file:
            pixmap = _load_icon_from_path(icon_file)
            if pixmap and not pixmap.isNull():
                return pixmap

    # --- .lnk files: read IconLocation via COM ---
    elif lower.endswith(".lnk"):
        icon_location = _read_lnk_icon_location(source_path)
        if icon_location:
            icon_file, icon_index = icon_location
            if icon_file:
                pixmap = _load_icon_from_resource(icon_file, icon_index)
                if pixmap and not pixmap.isNull():
                    return pixmap

    # --- SHGetFileInfo as a middle-ground fallback ---
    return _shgetfileinfo_icon(source_path)


def _read_url_icon_file(url_path: str) -> str | None:
    """Read the IconFile field from a .url file."""
    try:
        import configparser
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(url_path, encoding="utf-8")
        icon_file = cp.get("InternetShortcut", "IconFile", fallback=None)
        if icon_file and os.path.isfile(icon_file):
            logger.debug(f"_read_url_icon_file: '{url_path}' → IconFile='{icon_file}'")
            return icon_file
    except Exception as e:
        logger.debug(f"_read_url_icon_file failed for '{url_path}': {e}")
    return None


def _read_lnk_icon_location(lnk_path: str) -> tuple[str, int] | None:
    """Read IconLocation from a .lnk file via COM. Returns (icon_file, icon_index) or None."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        loc = shortcut.IconLocation  # e.g. "C:\path\icon.ico, 0"
        if loc:
            parts = loc.rsplit(",", 1)
            icon_file = parts[0].strip()
            icon_index = int(parts[1].strip()) if len(parts) > 1 else 0
            if icon_file and os.path.isfile(icon_file):
                logger.debug(f"_read_lnk_icon_location: '{lnk_path}' → '{icon_file}', {icon_index}")
                return icon_file, icon_index
    except Exception as e:
        logger.debug(f"_read_lnk_icon_location failed for '{lnk_path}': {e}")
    return None


def _load_icon_from_path(icon_path: str):
    """Load an icon file (.ico, .png, .bmp) as a QPixmap."""
    from PySide6.QtGui import QPixmap
    try:
        icon = QIcon(icon_path)
        sizes = icon.availableSizes()
        if sizes:
            # Pick the largest available size
            best = max(sizes, key=lambda s: s.width() * s.height())
            pixmap = icon.pixmap(best)
        else:
            pixmap = icon.pixmap(256, 256)
        if not pixmap.isNull():
            return pixmap
    except Exception as e:
        logger.debug(f"_load_icon_from_path failed for '{icon_path}': {e}")
    return None


def _load_icon_from_resource(icon_file: str, icon_index: int):
    """Extract an icon from an .exe/.dll/.ico resource using win32gui."""
    from PySide6.QtGui import QPixmap
    try:
        import win32gui
        import win32ui
        import win32con

        # ExtractIconEx returns (large_icons, small_icons) — each a tuple of HICONs
        large, small = win32gui.ExtractIconEx(icon_file, icon_index, 1)
        hicon = large[0] if large else (small[0] if small else None)
        if not hicon:
            # Try loading as plain icon file
            return _load_icon_from_path(icon_file)

        try:
            pixmap = _hicon_to_pixmap(hicon)
            return pixmap
        finally:
            # Clean up all extracted icons
            for h in large:
                win32gui.DestroyIcon(h)
            for h in small:
                win32gui.DestroyIcon(h)

    except Exception as e:
        logger.debug(f"_load_icon_from_resource failed for '{icon_file}': {e}")
        return _load_icon_from_path(icon_file)


def _hicon_to_pixmap(hicon):
    """Convert a Windows HICON to a QPixmap using pywin32."""
    from PySide6.QtGui import QPixmap, QImage
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
    except ImportError:
        logger.debug("_hicon_to_pixmap: pywin32 not available")
        return None

    try:
        info = win32gui.GetIconInfo(hicon)
        # info = (fIcon, xHotspot, yHotspot, hbmMask, hbmColor)
        hbm_color = info[4]
        hbm_mask = info[3]
        src_bmp = hbm_color or hbm_mask

        # Get bitmap dimensions
        bmp_info = win32gui.GetObject(src_bmp)
        w = bmp_info.bmWidth
        h = bmp_info.bmHeight

        # Create a compatible DC and 32-bit DIB section
        hdc_screen = win32gui.GetDC(0)
        hdc_mem = win32gui.CreateCompatibleDC(hdc_screen)

        import ctypes
        import ctypes.wintypes

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", ctypes.wintypes.WORD),
                ("biBitCount", ctypes.wintypes.WORD),
                ("biCompression", ctypes.wintypes.DWORD),
                ("biSizeImage", ctypes.wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", ctypes.wintypes.DWORD),
                ("biClrImportant", ctypes.wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB

        # Create DIB section
        ppvBits = ctypes.c_void_p()
        hbm_dib = ctypes.windll.gdi32.CreateDIBSection(
            hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(ppvBits), None, 0
        )
        old_bmp = win32gui.SelectObject(hdc_mem, hbm_dib)

        # Draw the icon into the DIB
        # Fill with transparent black first
        buf_size = w * h * 4
        ctypes.memset(ppvBits, 0, buf_size)
        win32gui.DrawIconEx(hdc_mem, 0, 0, hicon, w, h, 0, 0,
                            win32con.DI_NORMAL)

        # Copy pixel data
        raw = (ctypes.c_char * buf_size).from_address(ppvBits.value)
        data = bytes(raw)

        # Cleanup GDI
        win32gui.SelectObject(hdc_mem, old_bmp)
        ctypes.windll.gdi32.DeleteObject(hbm_dib)
        win32gui.DeleteDC(hdc_mem)
        win32gui.ReleaseDC(0, hdc_screen)
        if hbm_color:
            win32gui.DeleteObject(hbm_color)
        if hbm_mask:
            win32gui.DeleteObject(hbm_mask)

        # BGRA bytes -> QImage -> QPixmap
        img = QImage(data, w, h, w * 4, QImage.Format.Format_ARGB32)
        pixmap = QPixmap.fromImage(img.copy())
        return pixmap if not pixmap.isNull() else None

    except Exception as e:
        logger.debug(f"_hicon_to_pixmap failed: {e}")
        return None


def _shgetfileinfo_icon(path: str):
    """Use SHGetFileInfo to get the icon Windows Explorer displays."""
    from PySide6.QtGui import QPixmap
    try:
        import ctypes
        import ctypes.wintypes

        class SHFILEINFOW(ctypes.Structure):
            _fields_ = [
                ("hIcon", ctypes.wintypes.HANDLE),
                ("iIcon", ctypes.c_int),
                ("dwAttributes", ctypes.wintypes.DWORD),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80),
            ]

        SHGFI_ICON = 0x000000100
        SHGFI_LARGEICON = 0x000000000

        sfi = SHFILEINFOW()
        # SHGetFileInfoW requires backslash paths on Windows
        norm_path = os.path.normpath(path)
        result = ctypes.windll.shell32.SHGetFileInfoW(
            norm_path, 0, ctypes.byref(sfi), ctypes.sizeof(sfi),
            SHGFI_ICON | SHGFI_LARGEICON
        )
        if result and sfi.hIcon:
            try:
                return _hicon_to_pixmap(sfi.hIcon)
            finally:
                ctypes.windll.user32.DestroyIcon(sfi.hIcon)
    except Exception as e:
        logger.debug(f"_shgetfileinfo_icon failed for '{path}': {e}")
    return None


# ---------------------------------------------------------------------------
# .url file parsing
# ---------------------------------------------------------------------------

def parse_url_file(url_path: str) -> str | None:
    """
    Read a .url (web shortcut) file and return the URL it points to.
    .url files use INI format: [InternetShortcut]\\nURL=https://...
    Returns None if the file can't be read or has no URL= line.
    """
    try:
        import configparser
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(url_path, encoding="utf-8")
        url = cp.get("InternetShortcut", "URL", fallback=None)
        if url:
            logger.info(f"Parsed .url file: '{url_path}' → {url}")
        return url
    except Exception as e:
        logger.error(f"Failed to parse .url file '{url_path}': {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Strip characters that are invalid in Windows filenames."""
    invalid = r'\/:*?"<>|'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip() or "shortcut"
