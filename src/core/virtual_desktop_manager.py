import os
import time
from pyvda import VirtualDesktop, get_virtual_desktops
from src.utils.logger import get_logger

logger = get_logger("VirtualDesktopManager")


class VirtualDesktopManager:

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_all_desktops(self) -> list[VirtualDesktop]:
        return get_virtual_desktops()

    def get_desktop_count(self) -> int:
        return len(get_virtual_desktops())

    def find_desktop_by_name(self, name: str) -> VirtualDesktop | None:
        for d in get_virtual_desktops():
            if d.name.strip().lower() == name.strip().lower():
                return d
        return None

    def get_current_desktop(self) -> VirtualDesktop:
        return VirtualDesktop.current()

    # ------------------------------------------------------------------
    # Create / Delete
    # ------------------------------------------------------------------

    def create_desktop(self, name: str) -> VirtualDesktop | None:
        existing = self.find_desktop_by_name(name)
        if existing:
            logger.info(f"Desktop '{name}' already exists — skipping create.")
            return existing
        try:
            desktop = VirtualDesktop.create()
            time.sleep(0.3)  # allow Windows to initialise the desktop before renaming/wallpaper
            desktop.rename(name)
            logger.info(f"Created desktop: '{name}' (number={desktop.number})")
            return desktop
        except Exception as e:
            logger.error(f"Failed to create desktop '{name}': {e}")
            return None

    def delete_desktop(self, name: str) -> bool:
        desktop = self.find_desktop_by_name(name)
        if desktop is None:
            logger.warning(f"Delete: desktop '{name}' not found.")
            return False
        try:
            desktop.remove()
            logger.info(f"Deleted desktop: '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete desktop '{name}': {e}")
            return False

    # ------------------------------------------------------------------
    # Rename / Wallpaper
    # ------------------------------------------------------------------

    def rename_desktop(self, name: str, new_name: str) -> bool:
        desktop = self.find_desktop_by_name(name)
        if desktop is None:
            logger.warning(f"Rename: desktop '{name}' not found.")
            return False
        try:
            desktop.rename(new_name)
            logger.info(f"Renamed desktop '{name}' → '{new_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to rename desktop '{name}': {e}")
            return False

    def set_wallpaper(self, name: str, image_path: str) -> bool:
        desktop = self.find_desktop_by_name(name)
        if desktop is None:
            logger.warning(f"Set wallpaper: desktop '{name}' not found.")
            return False
        # Normalise path: forward slashes → backslashes, resolve to absolute
        image_path = os.path.normpath(os.path.abspath(image_path))
        if not os.path.isfile(image_path):
            logger.warning(f"Set wallpaper: file not found: {image_path}")
            return False
        try:
            desktop.set_wallpaper(image_path)
            logger.info(f"Set wallpaper on '{name}': {image_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to set wallpaper on '{name}': {e}")
            return False

    # ------------------------------------------------------------------
    # Switch
    # ------------------------------------------------------------------

    def switch_to_desktop(self, name: str) -> bool:
        desktop = self.find_desktop_by_name(name)
        if desktop is None:
            logger.warning(f"Switch: desktop '{name}' not found.")
            return False
        try:
            desktop.go()
            logger.info(f"Switched to desktop: '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to desktop '{name}': {e}")
            return False

    # ------------------------------------------------------------------
    # Sync (startup / refresh)
    # ------------------------------------------------------------------

    def sync_desktops(self, profile_desktops: list[dict]) -> dict[str, VirtualDesktop]:
        """
        Match existing Windows virtual desktops to profile entries.
        Does NOT create or delete desktops — the user manages those via Windows
        (Win+Ctrl+D to create, right-click taskbar to remove).
        Returns a mapping of active desktop name -> VirtualDesktop for desktops
        that exist in both Windows and the profile.
        """
        result = {}
        for desktop_def in profile_desktops:
            if not desktop_def.get("enabled", True):
                continue
            name = desktop_def["name"]
            existing = self.find_desktop_by_name(name)
            if existing:
                result[name] = existing
                logger.info(f"Matched profile desktop '{name}' to existing virtual desktop.")
            else:
                logger.info(f"Profile desktop '{name}' not found in Windows — skipping.")
        logger.info(f"Sync complete: {len(result)} desktop(s) matched.")
        return result
