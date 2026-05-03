# Desktop Workspaces

A Windows 10/11 tool for organized professionals that creates and manages multiple curated desktop workspaces. Each workspace is a named virtual desktop populated with shortcuts to folders and applications, persisting across restarts.

## Features

- **Named virtual desktops** — create workspaces like "Design", "Development", "Writing"
- **Shortcut management** — add shortcuts to folders and apps on each desktop
- **Persistence** — desktops and shortcuts recreate automatically on startup
- **Shop window launcher** — frameless overlay shows shortcuts for the active virtual desktop
- **Background per desktop** — set a distinct wallpaper for each workspace
- **Enable/disable desktops** — skip desktops you don't need on a given day
- **Path validation** — shortcuts show ✅ available / ⚠️ unavailable / ❌ dead status
- **Network path support** — non-blocking validation with 3-second timeout
- **Export/import profiles** — move your setup to another machine with a path adjustment wizard
- **Safe mode** — if startup crashes, next launch opens in safe mode instead of looping

## Requirements

- Windows 10 or 11
- Python 3.10+

## Setup

```bash
# Clone the repo
git clone https://github.com/bernieonline/DesktopManager.git
cd DesktopManager

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Launch the shop window (system tray / overlay launcher)
.venv\Scripts\pythonw.exe main.py

# Launch in startup mode (used by Task Scheduler)
.venv\Scripts\pythonw.exe main.py --startup

# Open the full control panel directly
.venv\Scripts\pythonw.exe main.py --control-panel
```

## Startup Integration

To run automatically at Windows startup, use the included PowerShell script:

```powershell
.\register_startup.ps1
```

This registers a Task Scheduler entry that launches the app at login.

## Project Structure

```
src/
  core/
    config_manager.py       # Load/save profiles and settings
    virtual_desktop_manager.py  # Windows virtual desktop WinAPI wrapper
    shortcut_manager.py     # Create/delete .lnk shortcut files
    shortcut_validator.py   # Async path validation (QThread)
    startup_executor.py     # Startup pipeline orchestrator
  ui/
    shop_window.py          # Frameless overlay launcher
    shortcut_tile.py        # Individual shortcut tile widget
    control_panel.py        # Full configuration panel
    add_shortcut_dialog.py  # Add shortcut workflow
    add_desktop_dialog.py   # Add desktop workflow
    desktop_card.py         # Desktop card widget
    styles.py               # Shared stylesheet constants
  utils/
    logger.py               # Structured logging to AppData
    schema.py               # JSON schema validation and repair
main.py                     # Entry point
requirements.txt
register_startup.ps1
```

## Data Storage

- **Profile:** `%LOCALAPPDATA%\DesktopWorkspaces\profile.json`
- **Shortcuts:** `%LOCALAPPDATA%\DesktopWorkspaces\shortcuts\{desktop_id}\`
- **Logs:** `%LOCALAPPDATA%\DesktopWorkspaces\logs\app.log`

## Tech Stack

- Python 3.13
- PySide6 6.11 (UI)
- pywin32 (Windows API)
- pyvda (virtual desktop management)
- pyshortcuts (`.lnk` file creation)
- jsonschema (profile validation)

## License

MIT — free to use, modify, and distribute.

## Status

**Phase 2 complete** — core workflows tested and working. See [Issues](https://github.com/bernieonline/DesktopManager/issues) for upcoming work.
