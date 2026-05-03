"""
Profile schema definition, validation, and repair.
All profile load/save operations pass through validate_profile()
before touching disk.
"""

import uuid
from datetime import datetime, timezone

import jsonschema

from src.utils.logger import get_logger

logger = get_logger("Schema")

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

SHORTCUT_SCHEMA = {
    "type": "object",
    "required": ["id", "label", "type", "path"],
    "additionalProperties": True,
    "properties": {
        "id":         {"type": "string", "minLength": 1},
        "label":      {"type": "string", "minLength": 1},
        "type":       {"type": "string", "enum": ["folder", "app", "file"]},
        "path":       {"type": "string", "minLength": 1},
        "lnk_path":   {"type": ["string", "null"]},
        "status":     {"type": ["string", "null"],
                       "enum": ["available", "unavailable", "dead", None]},
        "created_at": {"type": ["string", "null"]},
    },
}

DESKTOP_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "enabled", "shortcuts"],
    "additionalProperties": True,
    "properties": {
        "id":              {"type": "string", "minLength": 1},
        "name":            {"type": "string", "minLength": 1},
        "enabled":         {"type": "boolean"},
        "shortcuts":       {"type": "array", "items": SHORTCUT_SCHEMA},
        "background_path": {"type": ["string", "null"]},
        "created_at":      {"type": ["string", "null"]},
    },
}

PROFILE_SCHEMA = {
    "type": "object",
    "required": ["version", "name", "desktops"],
    "additionalProperties": True,
    "properties": {
        "version":  {"type": "integer", "minimum": 1},
        "name":     {"type": "string", "minLength": 1},
        "desktops": {"type": "array", "items": DESKTOP_SCHEMA},
    },
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_profile(profile: dict) -> tuple[bool, str]:
    """
    Validate profile against PROFILE_SCHEMA.
    Returns (True, "Valid") or (False, "error description").
    """
    try:
        jsonschema.validate(instance=profile, schema=PROFILE_SCHEMA)
        return True, "Valid"
    except jsonschema.ValidationError as e:
        msg = f"{e.message} (path: {' -> '.join(str(p) for p in e.absolute_path)})"
        logger.warning(f"Profile validation failed: {msg}")
        return False, msg
    except jsonschema.SchemaError as e:
        logger.error(f"Schema definition error: {e.message}")
        return False, f"Internal schema error: {e.message}"


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

def repair_profile(profile: dict) -> tuple[dict, list[str]]:
    """
    Attempt to repair a profile by removing invalid desktops and shortcuts.
    Preserves as much valid data as possible.
    Returns (repaired_profile, list of repair descriptions).
    """
    repairs = []

    # Ensure top-level required fields exist with safe defaults
    if not isinstance(profile.get("version"), int):
        profile["version"] = 1
        repairs.append("Reset missing/invalid 'version' to 1.")

    if not isinstance(profile.get("name"), str) or not profile["name"].strip():
        profile["name"] = "My Workspaces"
        repairs.append("Reset missing/invalid 'name' to 'My Workspaces'.")

    if not isinstance(profile.get("desktops"), list):
        profile["desktops"] = []
        repairs.append("Reset missing/invalid 'desktops' to empty list.")
        return profile, repairs

    # Repair each desktop
    valid_desktops = []
    for i, desktop in enumerate(profile["desktops"]):
        if not isinstance(desktop, dict):
            repairs.append(f"Removed desktop at index {i}: not an object.")
            continue

        tag = desktop.get("name") or desktop.get("id") or f"index {i}"

        # Required desktop fields
        if not isinstance(desktop.get("id"), str) or not desktop["id"].strip():
            new_id = f"repaired-{uuid.uuid4().hex[:8]}"
            desktop["id"] = new_id
            repairs.append(f"Desktop '{tag}': assigned new id '{new_id}'.")

        if not isinstance(desktop.get("name"), str) or not desktop["name"].strip():
            desktop["name"] = "Unnamed Desktop"
            repairs.append(f"Desktop '{tag}': reset name to 'Unnamed Desktop'.")

        if not isinstance(desktop.get("enabled"), bool):
            desktop["enabled"] = True
            repairs.append(f"Desktop '{tag}': reset enabled to True.")

        if not isinstance(desktop.get("shortcuts"), list):
            desktop["shortcuts"] = []
            repairs.append(f"Desktop '{tag}': reset shortcuts to empty list.")

        # Repair shortcuts
        valid_shortcuts = []
        for j, sc in enumerate(desktop["shortcuts"]):
            if not isinstance(sc, dict):
                repairs.append(f"Desktop '{tag}': removed shortcut at index {j}: not an object.")
                continue

            sc_tag = sc.get("label") or sc.get("id") or f"index {j}"
            missing = [k for k in ("id", "label", "type", "path") if not sc.get(k)]

            if missing:
                repairs.append(
                    f"Desktop '{tag}': removed shortcut '{sc_tag}' — missing required fields: {missing}."
                )
                continue

            if sc["type"] not in ("folder", "app", "file"):
                repairs.append(
                    f"Desktop '{tag}': removed shortcut '{sc_tag}' — invalid type '{sc['type']}'."
                )
                continue

            # Ensure optional fields are present with null defaults
            sc.setdefault("lnk_path", None)
            sc.setdefault("status", None)
            sc.setdefault("created_at", datetime.now(timezone.utc).isoformat())

            valid_shortcuts.append(sc)

        desktop["shortcuts"] = valid_shortcuts
        valid_desktops.append(desktop)

    profile["desktops"] = valid_desktops

    if repairs:
        logger.warning(f"Profile repaired — {len(repairs)} issue(s) fixed.")
        for r in repairs:
            logger.warning(f"  Repair: {r}")
    else:
        logger.info("Profile repair check passed — no issues found.")

    return profile, repairs
