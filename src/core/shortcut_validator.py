"""
ShortcutValidator: background thread that validates all shortcut paths
on startup without blocking the UI.

Emits per-shortcut results as they complete so the shop window can
update status indicators incrementally.
"""

from PySide6.QtCore import QThread, Signal

from src.core.shortcut_manager import validate_path
from src.utils.logger import get_logger

logger = get_logger("ShortcutValidator")


class ShortcutValidator(QThread):
    """
    Validates all shortcuts in the profile on a background thread.

    Signals:
        shortcut_validated(desktop_id, shortcut_id, status)
            Emitted after each individual shortcut is checked.
            status is one of: "available", "unavailable", "dead"

        validation_complete(counts)
            Emitted when all shortcuts have been checked.
            counts = {"available": N, "unavailable": N, "dead": N}
    """

    shortcut_validated = Signal(str, str, str)
    validation_complete = Signal(dict)

    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self._profile = profile

    def run(self):
        counts = {"available": 0, "unavailable": 0, "dead": 0}

        desktops = self._profile.get("desktops", [])
        enabled = [d for d in desktops if d.get("enabled", True)]

        total = sum(len(d.get("shortcuts", [])) for d in enabled)
        logger.info(f"Validating {total} shortcut(s) across {len(enabled)} desktop(s).")

        for desktop in enabled:
            desktop_id = desktop["id"]
            for shortcut in desktop.get("shortcuts", []):
                shortcut_id = shortcut["id"]
                path = shortcut.get("path", "")

                try:
                    status = validate_path(path)
                except Exception as e:
                    logger.error(f"Validation error for '{shortcut.get('label')}': {e}")
                    status = "unavailable"

                counts[status] = counts.get(status, 0) + 1
                logger.debug(
                    f"  [{status.upper()}] {shortcut.get('label', shortcut_id)} — {path}"
                )
                self.shortcut_validated.emit(desktop_id, shortcut_id, status)

        logger.info(
            f"Validation complete — "
            f"available: {counts['available']}, "
            f"unavailable: {counts['unavailable']}, "
            f"dead: {counts['dead']}"
        )
        self.validation_complete.emit(counts)
