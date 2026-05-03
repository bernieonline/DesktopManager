# Desktop Workspaces — Phase 2 Plan
**Version:** 2.1 (Revised after design review)
**Date:** 2026-05-02
**Status:** Agreed — Ready for development
**Author:** Bernard (with Claude Code)

---

## Design Decisions (Agreed)

### The Windows Desktop Folder Constraint
Windows virtual desktops share a single filesystem folder (`%USERPROFILE%\Desktop`).
Any file placed there appears on every virtual desktop simultaneously.
Per-desktop shortcut isolation via the Desktop folder is not achievable.

### Resolution: The Shop Window
The Control Panel becomes a smart contextual launcher — the "shop window" for shortcuts.

- One `.lnk` shortcut to the Control Panel is placed in the shared Desktop folder.
  It appears on every virtual desktop naturally — this is a legitimate use of the shared folder.
- Opening the Control Panel detects the currently active virtual desktop (via `pyvda`).
- The shop window displays only that desktop's shortcuts as clickable tiles.
- Clicking a tile launches the target. Windows handles window isolation per desktop natively.
- Shortcuts are stored in the profile and accessed via the shop window — not placed on the Desktop folder.

### Window Behaviour (Agreed)
- Frameless, translucent window with a 1px bronze border (#B8956A)
- Background: semi-transparent dark (`rgba(18, 18, 18, 160)`) — desktop wallpaper shows through
- Fixed position: top-right corner of screen (calculated from `QScreen.availableGeometry()`)
- 3 shortcut tiles across, always
- Normal window — not always on top. User goes to get it when needed.
- Draggable by clicking and dragging the header strip

### What Is Dropped from the Original Brief
- Shortcut placement on the Windows Desktop folder (not achievable per-desktop)
- Shortcut position persistence via Registry/desktop.ini (no longer relevant)
- Shutdown auto-sync by scanning the Desktop folder (not applicable)

---

## Phase 2 Scope

### Feature 1 — Shop Window (Primary View)
The Control Panel opens showing the current desktop's shortcuts as tiles.

**States:**
1. **Active managed desktop with shortcuts** — shows tile grid, 3 across
2. **Active managed desktop, no shortcuts yet** — shows "No shortcuts yet. [+ Add Shortcut]"
3. **Unrecognised desktop** (not in profile) — shows "This desktop isn't in your profile. [+ Add to Profile]"

**Tile design:**
- Large clickable area (~100x90px)
- Icon above label (Windows shell icon extracted from target, fallback to type icon)
- Status indicator dot (green / amber / red) in top-right corner of tile
- Single click launches the target via `os.startfile()`
- Tiles wrap into rows of 3; window height grows to fit

### Feature 2 — Add Shortcut
- User clicks **[+ Add Shortcut]** in the shop window bottom bar
- File picker opens (filters: Applications *.exe *.lnk, All Files, Folders)
- App auto-generates name from filename (e.g. "Photoshop.exe" → "Photoshop")
- Name confirmation dialog: pre-filled, user can edit before confirming
- Shortcut added to profile for the current desktop
- Shop window refreshes immediately

### Feature 3 — Remove Shortcut
- User opens manage panel → clicks [🗑] next to a shortcut
- Confirmation prompt: "Remove Photoshop from Design?"
- Removed from profile, shop window refreshes

### Feature 4 — Shortcut Status Indicators
- ✅ Available — path exists and is accessible
- ⚠️ Unavailable — path exists but is offline (network path, timeout)
- ❌ Dead — path does not exist
- Validated on startup (background thread, non-blocking, 3-second timeout)
- Status badge on tile corner
- **[⚠ N]** button in bottom bar shows count of problem shortcuts; click to see detail

### Feature 5 — Unrecognised Desktop Flow
When the active desktop has no profile entry:

```
┌─ Desktop Workspaces ─────────────────── [✕] ┐
│                                              │
│   This desktop isn't in your profile yet.   │
│                                             │
│        [+ Add to Profile]                   │
│                                             │
└──────────────────────────────────────────── ┘
```

Clicking [+ Add to Profile] prompts for a name, creates the profile entry,
and switches the shop window to the empty-shortcuts state.

### Feature 6 — Manage Panel (Expandable)
Bottom bar button **[✎ Manage]** expands the window downward to reveal:

- All desktops list with enable/disable toggles
- Per-desktop shortcut list with [🗑 Remove] buttons
- [+ Add Desktop] button
- Wallpaper selector per desktop (carried forward from Phase 1)
- Collapsible — clicking [✎ Manage] again collapses it

### Feature 7 — Profile Backup & Import
Bottom bar button **[💾 Backup]**:
- Save dialog opens (default: Documents)
- Creates: `DesktopWorkspaces_Backup_2026-05-02_14-30.json`
- Confirmation shown inline in status strip

Bottom bar button **[📥 Import]**:
- File picker opens → user selects backup `.json`
- App validates against schema
- Preview dialog: "Current: 3 desktops, 8 shortcuts → Backup: 5 desktops, 12 shortcuts"
- If confirmed: auto-backs up current profile, loads imported profile, refreshes UI

### Feature 8 — Control Panel Shortcut on Every Desktop
- On startup, a `.lnk` shortcut to `main.py` (or the installed `.exe`) is placed in
  `%USERPROFILE%\Desktop` if not already present.
- Label: "Desktop Workspaces"
- Because it's in the shared Desktop folder, it naturally appears on every virtual desktop.

---

## UI Layout

### Shop Window — Primary View

```
╔══════════════════════════════════════════╗  ← 1px bronze border #B8956A
║  ◆ Design                          [✕]  ║  ← header: rgba(24,24,24,180), bronze name
╠══════════════════════════════════════════╣
║                                          ║  ← body: rgba(18,18,18,160) — translucent
║  ┌────────┐  ┌────────┐  ┌────────┐     ║
║  │   📁 ●│  │   🖼 ●│  │   📁 ●│     ║  ← tiles: rgba(30,30,30,200)
║  │ Design │  │Photoshp│  │ Assets │     ║  ← ● = status dot (green/amber/red)
║  └────────┘  └────────┘  └────────┘     ║
║                                          ║
║  ┌────────┐  ┌────────┐                  ║
║  │   📁 ●│  │   🎨 ●│                  ║
║  │  Ref   │  │ Figma  │                  ║
║  └────────┘  └────────┘                  ║
║                                          ║
╠══════════════════════════════════════════╣
║  [+ Shortcut] [✎ Manage] [💾] [📥] [⚠2]║  ← footer: rgba(24,24,24,180)
╚══════════════════════════════════════════╝
```

### Shop Window — Manage Panel Expanded

```
╠══════════════════════════════════════════╣
║  ▼ Desktops                              ║
║  ● Design ✓   ● Dev ✓   ● Writing ✓     ║
║  [+ Add Desktop]                         ║
╠══════════════════════════════════════════╣
║  ▼ Design Shortcuts                      ║
║  📁 Design Projects  ✅  [🗑]            ║
║  🖼 Photoshop         ✅  [🗑]            ║
║  📁 Team Assets       ⚠️  [🗑]            ║
╚══════════════════════════════════════════╝
```

---

## Modules to Build / Update

### 1. ShortcutManager (NEW) — `src/core/shortcut_manager.py`

```python
def get_display_name(target_path: str) -> str
    # "C:\Program Files\Adobe\Photoshop\Photoshop.exe" → "Photoshop"
    # "C:\Users\Bernard\Projects\Design" → "Design"

def create_lnk(target_path: str, label: str, output_dir: str) -> str
    # Creates .lnk via WScript.Shell
    # Stores in %LOCALAPPDATA%\DesktopWorkspaces\shortcuts\
    # Returns path to .lnk file

def delete_lnk(lnk_path: str) -> bool
    # Deletes .lnk file from disk

def validate_path(target_path: str) -> str
    # Returns "available", "unavailable", or "dead"
    # 3-second timeout for network paths
    # Suitable for background thread use

def extract_lnk_target(lnk_path: str) -> str
    # Reads .lnk and returns the target path

def get_shell_icon(target_path: str) -> QIcon
    # Extracts Windows shell icon for the target
    # Falls back to type-based icon (folder / app / file)

def place_control_panel_shortcut() -> bool
    # Places Desktop Workspaces.lnk in %USERPROFILE%\Desktop
    # Only if not already present
    # Returns True if placed or already exists
```

### 2. ShortcutValidator (NEW) — `src/core/shortcut_validator.py`

```python
class ShortcutValidator(QThread):
    # Background thread — validates all profile shortcuts on startup
    # Emits: validation_complete(desktop_id, shortcut_id, status)
    # Non-blocking — UI remains responsive
    # 3-second timeout per network path
    # Updates profile status fields on completion

    def validate_all(self, profile: dict) -> None
    def validate_desktop(self, desktop: dict) -> None
```

### 3. Schema & Validation (NEW) — `src/utils/schema.py`

```python
PROFILE_SCHEMA = { ... }  # jsonschema definition
    # version: required int
    # name: required str
    # desktops: required list
    #   id, name, enabled: required per desktop
    #   shortcuts: required list (can be empty)
    #     id, label, type, path: required per shortcut
    #     status, created_at: optional

def validate_profile(profile: dict) -> tuple[bool, str]
    # Returns (True, "Valid") or (False, "error description")

def repair_profile(profile: dict) -> tuple[dict, list[str]]
    # Removes invalid shortcuts/desktops
    # Returns (repaired_profile, list of what was repaired)
```

### 4. ConfigManager (EXTEND) — `src/core/config_manager.py`

New methods:
```python
def add_shortcut(desktop_id: str, shortcut: dict) -> bool
def remove_shortcut(desktop_id: str, shortcut_id: str) -> bool
def update_shortcut_status(desktop_id: str, shortcut_id: str, status: str) -> bool
def backup_profile(destination_path: str) -> bool
def import_profile(source_path: str) -> tuple[bool, str]
    # Validates, auto-backs up current, loads new
```

Enhanced existing methods:
```python
def save_profile(...)
    # Write to .tmp → verify readable → backup to .bak → replace original
    # Validate schema before writing

def load_profile(...)
    # On corruption: log, fall back to default, warn user
    # On schema failure: attempt repair_profile(), warn user
```

### 5. StartupExecutor (EXTEND) — `src/core/startup_executor.py`

New behaviour:
```python
def run_startup():
    # Existing: create desktops, apply wallpapers
    # NEW: place Control Panel shortcut on Desktop if not present
    # NEW: start ShortcutValidator background thread
```

### 6. Shop Window UI (NEW) — `src/ui/shop_window.py`

```python
class ShopWindow(QWidget):
    # Frameless, translucent window
    # Fixed: top-right corner of primary screen
    # Draggable by header
    # Detects active virtual desktop on open
    # Renders tile grid (3 across)
    # Bottom bar with action buttons
    # Expandable manage panel
```

### 7. ShortcutTile (NEW) — `src/ui/shortcut_tile.py`

```python
class ShortcutTile(QWidget):
    # ~100x90px clickable tile
    # Shell icon (top, centred)
    # Label (bottom, truncated if long)
    # Status dot (top-right corner)
    # Hover highlight (bronze border)
    # Click: os.startfile(target_path)
```

### 8. AddShortcutDialog (NEW) — `src/ui/add_shortcut_dialog.py`

```python
class AddShortcutDialog:
    # Step 1: QFileDialog — pick file, folder, or exe
    # Step 2: Name confirmation — pre-filled, editable
    # Returns: (target_path, confirmed_name) or None if cancelled
```

### 9. Existing ControlPanel — `src/ui/control_panel.py`

The existing ControlPanel (`QMainWindow`, full management UI) is retained as-is
for now and becomes accessible via the [✎ Manage] panel in the shop window.
It may be progressively merged into the shop window manage panel in Phase 3.

---

## Build Order

| Step | Module | Dependency |
|------|--------|------------|
| 1 | `src/utils/schema.py` | None — foundational |
| 2 | `ConfigManager` extensions | schema.py |
| 3 | `ShortcutManager` | ConfigManager |
| 4 | `ShortcutValidator` | ShortcutManager |
| 5 | `StartupExecutor` update | ShortcutManager |
| 6 | `ShortcutTile` widget | ShortcutManager |
| 7 | `ShopWindow` | ShortcutTile, ConfigManager, VirtualDesktopManager |
| 8 | `AddShortcutDialog` | ShortcutManager |
| 9 | Wire up backup/import | ConfigManager |
| 10 | End-to-end test | All modules |

---

## Profile JSON (Extended for Phase 2)

```json
{
  "version": 1,
  "name": "My Workspaces",
  "desktops": [
    {
      "id": "design-abc123",
      "name": "Design",
      "enabled": true,
      "background_path": "C:\\Users\\Bernard\\AppData\\Local\\DesktopWorkspaces\\wallpapers\\design-bg.png",
      "created_at": "2026-04-30T10:30:00Z",
      "shortcuts": [
        {
          "id": "sc-uuid-1",
          "label": "Design Projects",
          "type": "folder",
          "path": "C:\\Users\\Bernard\\Projects\\Design",
          "lnk_path": "C:\\Users\\Bernard\\AppData\\Local\\DesktopWorkspaces\\shortcuts\\design-abc123\\Design Projects.lnk",
          "status": "available",
          "created_at": "2026-05-02T14:30:00Z"
        },
        {
          "id": "sc-uuid-2",
          "label": "Photoshop",
          "type": "app",
          "path": "C:\\Program Files\\Adobe\\Photoshop\\Photoshop.exe",
          "lnk_path": "C:\\Users\\Bernard\\AppData\\Local\\DesktopWorkspaces\\shortcuts\\design-abc123\\Photoshop.lnk",
          "status": "available",
          "created_at": "2026-05-02T14:32:00Z"
        }
      ]
    }
  ]
}
```

Shortcuts stored at: `%LOCALAPPDATA%\DesktopWorkspaces\shortcuts\{desktop_id}\`

---

## Profile Safety Strategy

1. **Schema validation** on every load and save
2. **Safe save**: write to `.tmp` → verify readable → backup to `.bak` → replace original
3. **Corruption fallback**: log error, fall back to default empty profile, warn user
4. **Repair tool**: `repair_profile()` strips invalid entries, preserves valid data
5. **Backup/import**: user-controlled, timestamped, with preview before import
6. **Auto-backup before import**: current state always preserved

---

## Styling (Consistent with Phase 1)

| Element | Value |
|---------|-------|
| Bronze accent | `#B8956A` |
| Window background | `rgba(18, 18, 18, 160)` |
| Tile background | `rgba(30, 30, 30, 200)` |
| Header/footer strip | `rgba(24, 24, 24, 180)` |
| Window border | `1px solid #B8956A` |
| Status — available | `#4CAF50` (green dot) |
| Status — unavailable | `#FF9800` (amber dot) |
| Status — dead | `#F44336` (red dot) |
| Tile hover border | `#B8956A` |
| Text primary | `#E8E8E8` |
| Text muted | `#888888` |

---

## Success Criteria

- [ ] Control Panel shortcut appears on every virtual desktop after startup
- [ ] Shop window opens in top-right, translucent, bronze-framed
- [ ] Shop window detects active desktop and shows correct shortcuts
- [ ] Unrecognised desktop shows prompt to add to profile
- [ ] Empty desktop shows prompt to add shortcuts
- [ ] Clicking a tile launches the target correctly
- [ ] [+ Add Shortcut] flow works end-to-end (pick → name → saved → tile appears)
- [ ] [🗑 Remove] removes shortcut from profile
- [ ] Status indicators reflect path validity (✅ ⚠️ ❌)
- [ ] Validation runs in background — UI not blocked
- [ ] [💾 Backup] creates timestamped backup file
- [ ] [📥 Import] validates, previews, auto-backs up, and loads new profile
- [ ] Corrupted profile.json falls back to default gracefully
- [ ] All operations logged
- [ ] No crashes on invalid paths or network timeouts
- [ ] Desktops and shortcuts survive a Windows restart

---

## Known Constraints (Confirmed)

1. Windows virtual desktops share one Desktop folder — per-desktop shortcuts on the Desktop not achievable
2. The Control Panel shortcut in the shared Desktop folder is intentional — appears on every desktop naturally
3. Shortcuts are launched via `os.startfile()` — Windows handles window isolation per desktop natively
4. Shortcut position persistence deferred — not applicable to this model
5. Shutdown Desktop folder scanning dropped — not applicable to this model
6. Dynamic shortcut swapping on desktop switch — deferred (responsiveness concern, Phase 3 research item)

---

*Document Version: 2.1 · Date: 2026-05-02 · Status: Agreed — Ready for development*
*Next Phase: Phase 3 — Multi-machine export/import with path adjustment wizard*
