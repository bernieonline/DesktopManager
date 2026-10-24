# Desktop Workspaces — Context Statement

## What This Is

Desktop Workspaces is a Windows 10/11 tool that lets professionals create named virtual desktop workspaces, each populated with curated shortcuts to folders and applications. Shortcuts persist across restarts, are validated for availability, and are managed through a frameless overlay launcher (the "shop window") that detects the active virtual desktop and shows only that desktop's shortcuts.

Target user: experienced Windows users — developers, designers, professionals — who think in workspaces and waste time recreating their setup after every reboot.

## Tech Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13 | Runtime (venv at `.venv\`) |
| PySide6 | 6.11.0 | GUI framework (project brief says PyQt6 but PySide6 is used throughout) |
| pywin32 | 311 | Windows COM APIs (WScript.Shell for .lnk creation) |
| pyvda | 0.5.0 | Windows virtual desktop management (IVirtualDesktopManager wrapper) |
| pyshortcuts | 1.9.7 | Listed in requirements but not directly imported — .lnk creation uses win32com instead |
| comtypes | 1.4.16 | COM type library support (pyvda dependency) |
| jsonschema | 4.26.0 | Profile JSON validation |
| PyInstaller | 6.20.0 | Builds frozen .exe for distribution |
| NSIS | 3.x | Installer script (per-user install, no admin required) |

## File Structure

```
D:\DesktopProject\
  main.py                          # Entry point: no flag = shop window, --startup = startup executor,
                                   #   --control-panel = full management UI, --delay N = sleep before init
  main_startup.py                  # Alternate entry point for PyInstaller DesktopWorkspacesStartup.exe
  register_startup.ps1             # PowerShell: registers Task Scheduler logon task (WARNING: has RunLevel Highest — should be Limited)
  requirements.txt                 # pip dependencies
  README.md                        # GitHub-facing README

  src/
    core/
      config_manager.py            # Load/save profile.json, desktop CRUD, shortcut CRUD, backup/import.
                                   #   Safe save: .tmp -> verify -> .bak -> replace original.
      virtual_desktop_manager.py   # pyvda wrapper: create/delete/rename/wallpaper/switch/sync virtual desktops.
                                   #   sync_desktops() is match-only — does NOT auto-create or delete.
      shortcut_manager.py          # Create/delete .lnk files via WScript.Shell, validate paths (with
                                   #   timeout for network), extract shell icons, place Control Panel shortcut on Desktop.
      shortcut_validator.py        # QThread that validates all shortcut paths in background, emits per-shortcut
                                   #   signals so the shop window can update status dots incrementally.
      startup_executor.py          # Runs on logon: loads profile, syncs desktops, sets wallpapers, places
                                   #   Control Panel shortcut, launches shop window as detached process with 15s delay.

    ui/
      shop_window.py               # The main UI. Frameless overlay, top-right of screen, shows current desktop's
                                   #   shortcuts as a 3-column tile grid. OLE drag-and-drop, manage panel, backup/import.
                                   #   ~1100 lines — the largest and most complex module.
      shortcut_tile.py             # Single clickable tile: 116x104 px, shell icon, label, status dot, hover
                                   #   highlight, click-to-launch, press-and-hold drag-to-reorder.
      control_panel.py             # Full QMainWindow management UI (Phase 1). Desktop cards, add/delete/enable
                                   #   desktops, set wallpapers, diagnostics. Accessible via --control-panel flag.
      desktop_card.py              # Per-desktop card widget used in control_panel.py. Shows name, enabled
                                   #   checkbox, wallpaper selector, delete button.
      add_shortcut_dialog.py       # Two-step dialog: pick type (file/folder) -> file picker -> name confirmation.
                                   #   NameConfirmDialog is public — also used by shop_window's drag-and-drop handler.
      add_desktop_dialog.py        # Simple name-prompt dialog for adding a new desktop.
      styles.py                    # Shared colour constants and QSS stylesheets. BRONZE is currently #4FC3F7
                                   #   (bright blue — was changed from bronze #B8956A during Phase 2).

    utils/
      logger.py                    # get_logger() -> rotating file logger to %LOCALAPPDATA%\DesktopWorkspaces\logs\app.log.
                                   #   TimedRotatingFileHandler, midnight rotation, 7-day retention.
      schema.py                    # PROFILE_SCHEMA (jsonschema), validate_profile(), repair_profile().
                                   #   All profile load/save operations validate through here.

  tests/
    test_config_manager.py         # Manual test script for ConfigManager CRUD (not pytest).
    test_startup_executor.py       # (unverified — not read during this review)
    test_virtual_desktop_manager.py  # (unverified — not read during this review)
    spike_vd_properties.py         # Research spike: virtual desktop properties
    spike_virtual_desktop.py       # Research spike: pyvda virtual desktop API
    spike_wallpaper.py             # Research spike: per-desktop wallpaper API

  installer/
    DesktopWorkspaces.nsi          # NSIS installer script. Per-user install to %LOCALAPPDATA%\Programs\.
                                   #   Registers HKCU Run key for startup. Creates Start Menu shortcuts.

  build/                           # PyInstaller build artifacts
  dist/                            # PyInstaller output (DesktopWorkspaces.exe + DesktopWorkspacesStartup.exe)
```

## What Currently Works

### Phase 1 (POC) — Complete
- Create/delete named virtual desktops via the control panel
- Enable/disable desktops (disabled desktops skipped on startup sync)
- Per-desktop wallpaper (images copied to local store, handles OneDrive cloud-only files)
- Profile persistence across restarts — desktops recreate on Windows logon
- Diagnostics panel showing profile vs Windows desktop counts
- All actions logged to rotating log file

### Phase 2 (Shortcuts & Shop Window) — Feature Complete
- **Shop window**: frameless overlay, positioned top-right, 3-column tile grid
- **Desktop detection**: polls `pyvda.VirtualDesktop.current()` every 500ms, re-renders on switch
- **Unrecognised desktop**: shows "Add to Profile" prompt with auto-naming
- **Empty desktop**: shows "Add Shortcut" prompt
- **Tile interaction**: click to launch (os.startfile), status dots (green/amber/red/grey)
- **Add shortcut**: two-step dialog (type picker -> file picker -> name confirmation)
- **Remove shortcut**: via manage panel, with confirmation
- **Drag-and-drop**: OLE IDropTarget — drag files/folders from Explorer into the shop window
  - .lnk files resolve to their target automatically
  - .lnk from shared Desktop: prompt to remove original after adding
  - Deduplication: already-added paths are rejected with a message
- **Drag-to-reorder**: press-and-hold (300ms) a tile, then drag to rearrange
  - Drop indicator line shows insertion point
  - Saves new order to profile immediately
- **Manage panel**: expandable footer section, shortcut list with remove buttons
- **Backup**: timestamped JSON export to user-chosen location
- **Import**: validate -> preview (current vs backup counts) -> auto-backup current -> load
- **Background validation**: QThread, non-blocking, 3s timeout for network paths
  - Progress bar (3px, bottom of window) shown during validation
  - Status badge in footer shows problem count
- **Profile safety**: schema validation on every load/save, safe save (.tmp->.bak->replace), auto-repair
- **Startup integration**: Task Scheduler task runs `--startup`, which syncs desktops + launches shop window
- **Control Panel shortcut**: placed on shared Desktop (appears on all virtual desktops)

## Where Data Lives

| Data | Path |
|------|------|
| Profile JSON | `%LOCALAPPDATA%\DesktopWorkspaces\profile.json` |
| Profile backup (auto) | `%LOCALAPPDATA%\DesktopWorkspaces\profile.json.bak` |
| Pre-import backups | `%LOCALAPPDATA%\DesktopWorkspaces\profile_before_import_TIMESTAMP.json.bak` |
| Shortcut .lnk files | `%LOCALAPPDATA%\DesktopWorkspaces\shortcuts\{desktop_id}\` |
| Cached icons (PNG) | `%LOCALAPPDATA%\DesktopWorkspaces\icons\{shortcut_id}.png` |
| Wallpapers (local copies) | `%LOCALAPPDATA%\DesktopWorkspaces\wallpapers\` |
| Logs | `%LOCALAPPDATA%\DesktopWorkspaces\logs\app.log` (+ rotated backups) |
| Control Panel shortcut | `%USERPROFILE%\Desktop\Desktop Workspaces.lnk` (or OneDrive Desktop) |
| Installed app (NSIS) | `%LOCALAPPDATA%\Programs\DesktopWorkspaces\` |
| Start Menu | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Desktop Workspaces\` |

The Desktop path is read from the Registry (`HKCU\...\Shell Folders\Desktop`) to handle OneDrive redirection correctly. On the dev machine it resolves to `C:\Users\berna\OneDrive\Desktop`.

## Architecture: How the Pieces Fit Together

### Startup Flow (logon)

```
Task Scheduler (AtLogOn)
  -> pythonw.exe main.py --startup
     -> StartupExecutor.run()
        1. Load profile.json
        2. sync_desktops(): match profile entries to existing Windows virtual desktops (no create/delete)
        3. Apply wallpapers for matched desktops
        4. place_control_panel_shortcut() on shared Desktop
        5. subprocess.Popen([pythonw, main.py, --delay, 15]) as DETACHED_PROCESS
           (startup executor exits here — shop window runs independently)

  ... 15 seconds pass ...

  -> pythonw.exe main.py --delay 15
     1. time.sleep(15)  -- let Explorer stabilise
     2. OleInitialize(None) -- BEFORE QApplication
     3. QApplication created
     4. ShopWindow created and shown
     5. _poll_shell_and_register(): wait for Shell_TrayWnd, then setAcceptDrops(True)
     6. QTimer.singleShot(500, start_validation) -- background path validation
```

### Shop Window (runtime)

```
ShopWindow (QWidget, frameless, Tool window type)
  |
  |- Polls VirtualDesktop.current() every 500ms
  |    -> On desktop switch: reload shortcuts from profile, re-render tile grid
  |
  |- Tile grid: 3 columns, tiles derive size from window width
  |    -> Click: os.startfile(path)
  |    -> Press-and-hold 300ms: drag-to-reorder (internal QDrag with custom MIME)
  |
  |- OLE drag-and-drop (IDropTarget)
  |    -> Files/folders from Explorer: resolve .lnk targets, show NameConfirmDialog, add to profile
  |    -> CRITICAL: app must run non-elevated or UIPI blocks drops from Explorer
  |
  |- Manage panel (expandable)
  |    -> Shortcut list with remove buttons
  |    -> Backup / Import buttons
  |
  |- ShortcutValidator (QThread)
       -> Validates all shortcut paths in background
       -> Emits per-shortcut signals -> tiles update status dots
```

### Control Panel (legacy)

The full `ControlPanel` QMainWindow (from Phase 1) is still accessible via `--control-panel` but is not the primary UI. It manages desktops at a higher level: create/delete desktops, toggle enabled state, select wallpapers, run diagnostics. The shop window has absorbed most day-to-day shortcut management.

### Profile JSON flow

```
ConfigManager
  |- load_profile() -> validate_profile() -> repair_profile() if invalid
  |- save_profile() -> validate_profile() -> write .tmp -> verify -> backup .bak -> replace
  |- All CRUD operations (add/delete desktop, add/remove/reorder shortcuts) -> save_profile()
```

---

*Generated 2026-10-24 from codebase at commit b6e87db*
