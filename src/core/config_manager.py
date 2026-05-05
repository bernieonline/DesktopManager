import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from src.utils.logger import get_logger
from src.utils.schema import validate_profile, repair_profile

logger = get_logger("ConfigManager")

PROFILE_VERSION = 1
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DesktopWorkspaces")
PROFILE_PATH = os.path.join(APP_DIR, "profile.json")
SHORTCUTS_DIR = os.path.join(APP_DIR, "shortcuts")

EMPTY_PROFILE = {
    "version": PROFILE_VERSION,
    "name": "My Workspaces",
    "desktops": []
}


class ConfigError(Exception):
    pass


class ConfigManager:
    def __init__(self, profile_path: str = PROFILE_PATH):
        self.profile_path = profile_path
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        self._profile = None

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load_profile(self) -> dict:
        if not os.path.exists(self.profile_path):
            logger.info("No profile found — creating empty profile.")
            self._profile = dict(EMPTY_PROFILE)
            self._profile["desktops"] = []
            self.save_profile(self._profile)
            return self._profile

        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load profile: {e} — attempting repair from .bak.")
            data = self._load_backup_or_default()

        valid, msg = validate_profile(data)
        if not valid:
            logger.warning(f"Profile invalid ({msg}) — attempting repair.")
            data, repairs = repair_profile(data)
            valid2, msg2 = validate_profile(data)
            if not valid2:
                logger.error(f"Repair failed ({msg2}) — falling back to empty profile.")
                data = dict(EMPTY_PROFILE)
                data["desktops"] = []
            else:
                logger.info(f"Profile repaired successfully ({len(repairs)} fix(es)).")
                self.save_profile(data)

        if data.get("version", 1) != PROFILE_VERSION:
            raise ConfigError(
                f"Unsupported profile version {data['version']} (expected {PROFILE_VERSION})."
            )

        self._profile = data
        logger.info(f"Profile loaded: {len(data['desktops'])} desktop(s).")
        return self._profile

    def _load_backup_or_default(self) -> dict:
        bak_path = self.profile_path + ".bak"
        if os.path.exists(bak_path):
            try:
                with open(bak_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Loaded profile from .bak file.")
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Backup also unreadable: {e}")
        default = dict(EMPTY_PROFILE)
        default["desktops"] = []
        return default

    def save_profile(self, profile: dict = None) -> bool:
        """
        Safe save: write to .tmp → verify readable → backup existing → replace original.
        Returns True on success, False on failure.
        """
        if profile is not None:
            self._profile = profile
        if self._profile is None:
            raise ConfigError("No profile loaded to save.")

        valid, msg = validate_profile(self._profile)
        if not valid:
            logger.error(f"Refusing to save invalid profile: {msg}")
            return False

        tmp_path = self.profile_path + ".tmp"
        bak_path = self.profile_path + ".bak"

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._profile, f, indent=2)

            # Verify the temp file is readable
            with open(tmp_path, "r", encoding="utf-8") as f:
                json.load(f)

            # Backup the existing profile
            if os.path.exists(self.profile_path):
                shutil.copy2(self.profile_path, bak_path)

            # Replace original
            shutil.move(tmp_path, self.profile_path)
            logger.info("Profile saved.")
            return True

        except OSError as e:
            logger.error(f"Failed to save profile: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

    # ------------------------------------------------------------------
    # Desktop Operations
    # ------------------------------------------------------------------

    def add_desktop(self, name: str, windows_vd_id: str = None) -> dict:
        if self._profile is None:
            self.load_profile()

        slug = (name or "desktop").lower().replace(" ", "-")
        desktop_id = f"{slug}-{uuid.uuid4().hex[:6]}"

        desktop = {
            "id": desktop_id,
            "name": name or "New Desktop",
            "enabled": True,
            "shortcuts": [],
            "background_path": None,
            "windows_vd_id": windows_vd_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._profile["desktops"].append(desktop)
        self.save_profile()
        logger.info(f"Desktop added: '{name}' (id: {desktop_id}, vd_id: {windows_vd_id})")
        return desktop

    def delete_desktop(self, desktop_id: str) -> None:
        if self._profile is None:
            self.load_profile()

        before = len(self._profile["desktops"])
        self._profile["desktops"] = [
            d for d in self._profile["desktops"] if d["id"] != desktop_id
        ]
        if len(self._profile["desktops"]) == before:
            logger.warning(f"Delete: desktop id '{desktop_id}' not found.")
            return
        self.save_profile()
        logger.info(f"Desktop deleted: {desktop_id}")

    def update_desktop(self, desktop_id: str, updates: dict) -> None:
        if self._profile is None:
            self.load_profile()

        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            logger.warning(f"Update: desktop id '{desktop_id}' not found.")
            return

        protected = {"id", "created_at"}
        for key, value in updates.items():
            if key not in protected:
                desktop[key] = value
        self.save_profile()
        logger.info(f"Desktop updated: {desktop_id} — {list(updates.keys())}")

    def get_desktop_by_id(self, desktop_id: str) -> dict | None:
        if self._profile is None:
            self.load_profile()
        for desktop in self._profile["desktops"]:
            if desktop["id"] == desktop_id:
                return desktop
        return None

    def get_all_desktops(self) -> list:
        if self._profile is None:
            self.load_profile()
        return self._profile["desktops"]

    def get_enabled_desktops(self) -> list:
        return [d for d in self.get_all_desktops() if d.get("enabled", True)]

    # ------------------------------------------------------------------
    # Shortcut Operations
    # ------------------------------------------------------------------

    def add_shortcut(self, desktop_id: str, shortcut: dict) -> bool:
        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            logger.warning(f"add_shortcut: desktop '{desktop_id}' not found.")
            return False

        shortcut.setdefault("id", f"sc-{uuid.uuid4().hex[:8]}")
        shortcut.setdefault("status", None)
        shortcut.setdefault("lnk_path", None)
        shortcut.setdefault("created_at", datetime.now(timezone.utc).isoformat())

        desktop.setdefault("shortcuts", [])
        desktop["shortcuts"].append(shortcut)
        self.save_profile()
        logger.info(f"Shortcut added: '{shortcut['label']}' → desktop '{desktop_id}'")
        return True

    def remove_shortcut(self, desktop_id: str, shortcut_id: str) -> bool:
        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            logger.warning(f"remove_shortcut: desktop '{desktop_id}' not found.")
            return False

        before = len(desktop.get("shortcuts", []))
        desktop["shortcuts"] = [
            s for s in desktop.get("shortcuts", []) if s["id"] != shortcut_id
        ]
        if len(desktop["shortcuts"]) == before:
            logger.warning(f"remove_shortcut: shortcut '{shortcut_id}' not found.")
            return False

        self.save_profile()
        logger.info(f"Shortcut removed: '{shortcut_id}' from desktop '{desktop_id}'")
        return True

    def reorder_shortcuts(self, desktop_id: str, ordered_ids: list) -> bool:
        """Rebuild the shortcuts list for *desktop_id* in the order given by
        *ordered_ids*.  Any shortcuts not listed are appended at the end."""
        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            logger.warning(f"reorder_shortcuts: desktop '{desktop_id}' not found.")
            return False

        current = {sc["id"]: sc for sc in desktop.get("shortcuts", [])}
        seen: set = set()
        reordered = []
        for sc_id in ordered_ids:
            if sc_id in current and sc_id not in seen:
                reordered.append(current[sc_id])
                seen.add(sc_id)
        # Safety net: append any shortcuts missing from ordered_ids
        for sc in desktop.get("shortcuts", []):
            if sc["id"] not in seen:
                reordered.append(sc)
        desktop["shortcuts"] = reordered
        self.save_profile()
        logger.info(f"Shortcuts reordered for desktop '{desktop_id}'")
        return True

    def update_shortcut_status(self, desktop_id: str, shortcut_id: str, status: str) -> bool:
        shortcut = self.get_shortcut_by_id(desktop_id, shortcut_id)
        if shortcut is None:
            return False
        shortcut["status"] = status
        self.save_profile()
        logger.debug(f"Shortcut status updated: '{shortcut_id}' → {status}")
        return True

    def update_shortcut_lnk_path(self, desktop_id: str, shortcut_id: str, lnk_path: str) -> bool:
        shortcut = self.get_shortcut_by_id(desktop_id, shortcut_id)
        if shortcut is None:
            return False
        shortcut["lnk_path"] = lnk_path
        self.save_profile()
        return True

    def get_shortcut_by_id(self, desktop_id: str, shortcut_id: str) -> dict | None:
        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            return None
        for sc in desktop.get("shortcuts", []):
            if sc["id"] == shortcut_id:
                return sc
        return None

    def get_shortcuts_for_desktop(self, desktop_id: str) -> list:
        desktop = self.get_desktop_by_id(desktop_id)
        if desktop is None:
            return []
        return desktop.get("shortcuts", [])

    # ------------------------------------------------------------------
    # Backup & Import
    # ------------------------------------------------------------------

    def backup_profile(self, destination_path: str) -> bool:
        """Save a timestamped copy of the current profile to destination_path."""
        if self._profile is None:
            self.load_profile()
        try:
            with open(destination_path, "w", encoding="utf-8") as f:
                json.dump(self._profile, f, indent=2)
            logger.info(f"Profile backed up to: {destination_path}")
            return True
        except OSError as e:
            logger.error(f"Backup failed: {e}")
            return False

    def import_profile(self, source_path: str) -> tuple[bool, str]:
        """
        Load and validate a backup file.
        If valid, auto-backs up the current profile then replaces it.
        Returns (success, message).
        """
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            msg = f"Cannot read file: {e}"
            logger.error(f"Import failed: {msg}")
            return False, msg

        valid, err = validate_profile(data)
        if not valid:
            msg = f"File is not a valid profile: {err}"
            logger.error(f"Import failed: {msg}")
            return False, msg

        # Auto-backup current profile before replacing
        if os.path.exists(self.profile_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            auto_bak = self.profile_path.replace(".json", f"_before_import_{ts}.json.bak")
            try:
                shutil.copy2(self.profile_path, auto_bak)
                logger.info(f"Auto-backup before import: {auto_bak}")
            except OSError as e:
                logger.warning(f"Could not create auto-backup: {e}")

        self._profile = data
        self.save_profile()
        desktops = len(data.get("desktops", []))
        shortcuts = sum(len(d.get("shortcuts", [])) for d in data.get("desktops", []))
        msg = f"Imported: {desktops} desktop(s), {shortcuts} shortcut(s)."
        logger.info(f"Profile imported from: {source_path} — {msg}")
        return True, msg

    def profile_summary(self) -> dict:
        """Return a dict with desktop and shortcut counts for display."""
        if self._profile is None:
            self.load_profile()
        desktops = self._profile.get("desktops", [])
        return {
            "desktops": len(desktops),
            "shortcuts": sum(len(d.get("shortcuts", [])) for d in desktops),
        }
