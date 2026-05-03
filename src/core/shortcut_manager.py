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
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Strip characters that are invalid in Windows filenames."""
    invalid = r'\/:*?"<>|'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip() or "shortcut"
