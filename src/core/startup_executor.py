import os
import sys
import time
from src.core.config_manager import ConfigManager
from src.core.virtual_desktop_manager import VirtualDesktopManager
from src.core.shortcut_manager import place_control_panel_shortcut
from src.utils.logger import get_logger

logger = get_logger("StartupExecutor")


class StartupExecutor:
    def __init__(self):
        self.config = ConfigManager()
        self.vdm = VirtualDesktopManager()

    def run(self) -> None:
        start = time.time()
        logger.info("Startup sequence begin.")

        try:
            profile = self.config.load_profile()
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            return

        all_desktops = self.config.get_all_desktops()
        enabled = [d for d in all_desktops if d.get("enabled", True)]
        logger.info(f"{len(enabled)} enabled desktop(s) in profile.")

        if not all_desktops:
            logger.info("No desktops in profile — nothing to do.")

        # Sync virtual desktops and apply wallpapers
        created = self.vdm.sync_desktops(all_desktops)
        for desktop_def in enabled:
            name = desktop_def["name"]
            bg = desktop_def.get("background_path")
            if bg:
                self.vdm.set_wallpaper(name, bg)

        # Place Control Panel shortcut on Desktop (idempotent)
        place_control_panel_shortcut()

        # Background shortcut validation — runs after startup returns
        self._start_validation(profile)

        elapsed = time.time() - start
        logger.info(
            f"Startup complete. {len(created)} desktop(s) created in {elapsed:.2f}s."
        )
        # Launch the shop window as a detached process with a 30-second delay.
        # The delay ensures Explorer's OLE drag-and-drop infrastructure is fully
        # stable before the shop window registers its IDropTarget.
        # Launching from here (rather than a Registry Run key) is more reliable
        # because this Task Scheduler task is guaranteed to run on every logon.
        # If you previously added a Registry Run key for "--delay 30", remove it
        # to avoid two shop window instances opening on each logon.
        self._launch_shop_window()

    def _launch_shop_window(self) -> None:
        """Launch the shop window as a detached process with a 30-second delay.

        Uses pythonw.exe (no console window).  The 30-second delay is applied
        via the --delay flag in main.py, which sleeps before any Qt/COM
        initialisation — by then Explorer's OLE routing is always stable.
        """
        try:
            import subprocess
            pythonw = sys.executable
            # Prefer pythonw.exe (no console window) when running from python.exe
            if pythonw.lower().endswith("python.exe"):
                candidate = pythonw[:-10] + "pythonw.exe"
                if os.path.isfile(candidate):
                    pythonw = candidate
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            main_py = os.path.join(project_root, "main.py")
            subprocess.Popen(
                [pythonw, main_py, "--delay", "30"],
                cwd=project_root,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )
            logger.info("Shop window launch scheduled (30 s delay).")
        except Exception as e:
            logger.error(f"Failed to schedule shop window launch: {e}")

    def _start_validation(self, profile: dict) -> None:
        """
        Launch ShortcutValidator on a background thread.
        Results are written back to the profile via ConfigManager.
        Runs silently — does not block startup.

        In --startup mode (no QApplication), validation is intentionally skipped.
        The shop window process runs start_validation() asynchronously after it shows,
        so duplicating it here only adds blocking delay to the startup sequence.
        """
        try:
            from PySide6.QtWidgets import QApplication
            if QApplication.instance() is None:
                logger.info("Startup mode: validation deferred to shop window process.")
                return

            from src.core.shortcut_validator import ShortcutValidator
            self._validator = ShortcutValidator(profile)
            self._validator.shortcut_validated.connect(self._on_shortcut_validated)
            self._validator.validation_complete.connect(self._on_validation_complete)
            self._validator.start()
            logger.info("Background shortcut validation started.")

        except Exception as e:
            logger.error(f"Failed to start shortcut validation: {e}")

    def _on_shortcut_validated(self, desktop_id: str, shortcut_id: str, status: str) -> None:
        self.config.update_shortcut_status(desktop_id, shortcut_id, status)

    def _on_validation_complete(self, counts: dict) -> None:
        logger.info(
            f"Validation done — available: {counts.get('available', 0)}, "
            f"unavailable: {counts.get('unavailable', 0)}, "
            f"dead: {counts.get('dead', 0)}"
        )
