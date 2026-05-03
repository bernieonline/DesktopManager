# **Desktop Workspaces \- Phase 2: Shortcuts & Profile Safety**

## **Claude Code Brief**

**Document Version:** 2.0  
 **Status:** Ready for Claude Code Development  
 **Phase:** Phase 2 (Shortcuts & Safety)  
 **Target Timeline:** 2–3 weeks  
 **Language:** Python 3.13 | GUI: PySide6 | Windows API: pywin32

---

## **What Has Been Built (Phase 1 \- Complete)**

### **Working Features**

* ✅ Create named virtual desktops via Control Panel  
* ✅ Delete desktops (removed from Windows and profile)  
* ✅ Enable/disable desktops (disabled desktops don't recreate on startup)  
* ✅ Set per-desktop wallpaper (images copied to local store)  
* ✅ Change wallpaper (reselect replaces existing)  
* ✅ Profile persists across app restarts  
* ✅ Desktops recreate on Windows startup  
* ✅ Diagnostics panel showing profile vs Windows desktop counts  
* ✅ All actions logged to rotating log file

### **Environment**

* **Project:** `D:\DesktopProject\`  
* **Python:** 3.13 virtual environment at `.venv`  
* **Dependencies:** PySide6 6.11.0, pywin32 311, pyshortcuts 1.9.7, pyvda 0.5.0, comtypes 1.4.16  
* **Profile Storage:** `%LOCALAPPDATA%\DesktopWorkspaces\profile.json`  
* **Logs:** `%LOCALAPPDATA%\DesktopWorkspaces\logs\app.log`  
* **VS Code:** Configured to use venv interpreter

### **Project Structure**

D:\\DesktopProject\\  
├── main.py                            \# Entry point: \--startup or GUI  
├── requirements.txt  
├── src/  
│   ├── core/  
│   │   ├── config\_manager.py          \# ✅ DONE  
│   │   ├── virtual\_desktop\_manager.py \# ✅ DONE  
│   │   ├── startup\_executor.py        \# ✅ DONE (needs update for Phase 2\)  
│   │   ├── shortcut\_manager.py        \# 🚧 NEW (Phase 2\)  
│   │   ├── desktop\_change\_detector.py \# 🚧 NEW (Phase 2\)  
│   │   └── schema.py                  \# 🚧 NEW (Phase 2 \- Validation)  
│   ├── ui/  
│   │   ├── control\_panel.py           \# ✅ DONE (needs update for Phase 2\)  
│   │   ├── desktop\_card.py            \# ✅ DONE (needs update for Phase 2\)  
│   │   ├── add\_desktop\_dialog.py      \# ✅ DONE  
│   │   ├── add\_shortcut\_dialog.py     \# 🚧 NEW (Phase 2\)  
│   │   └── styles.py                  \# ✅ DONE  
│   └── utils/  
│       └── logger.py                  \# ✅ DONE  
├── tests/  
│   ├── test\_config\_manager.py  
│   ├── test\_virtual\_desktop\_manager.py  
│   ├── test\_startup\_executor.py  
│   ├── spike\_wallpaper.py  
│   └── spike\_shortcut\_positions.py    \# 🚧 NEW (Phase 2 \- Research)  
└── README.md  
---

## **Phase 2 Scope: Shortcuts & Profile Safety**

### **User-Facing Features**

#### **Feature 1: Add Shortcut to Desktop**

**Workflow:**

1. User opens Control Panel → clicks on a desktop card  
2. User clicks **\[+ Add Shortcut\]** button on that desktop  
3. File explorer opens → user selects target (folder, .exe, or file)  
4. App auto-generates a name from target filename (e.g., "Photoshop" from `Photoshop.exe`)  
5. Simple confirmation dialog appears: `"Shortcut name:"` with auto-filled name  
6. User confirms (Enter or OK) or edits name before confirming  
7. Shortcut is:  
   * Created as `.lnk` file  
   * Placed on the corresponding virtual desktop (during startup)  
   * Added to profile JSON  
   * Displayed in desktop card's shortcuts list with status indicator (✅ available, ⚠️ unavailable, ❌ dead)

#### **Feature 2: Remove Shortcut**

* User clicks **\[🗑 Remove\]** next to shortcut in desktop card  
* Shortcut is deleted from profile and `.lnk` file is cleaned up  
* Desktop refreshes to reflect change

#### **Feature 3: Shortcut Status Indicators**

* ✅ **Available** — path exists and is accessible  
* ⚠️ **Unavailable** — path is offline (e.g., network unreachable)  
* ❌ **Dead** — path doesn't exist

Status is validated on startup (background, non-blocking) and on-demand via "Check Status" button.

#### **Feature 4: Shortcut Icons (User-Controlled)**

* Shortcuts use Windows default icon based on file type  
* User can customize via right-click → Properties → Change Icon (standard Windows)  
* Icon is embedded in `.lnk` file, persists naturally  
* **No Control Panel icon management** in Phase 2

#### **Feature 5: Profile Backup & Import**

**Backup Button (\[💾 Backup\]):**

* User clicks button  
* Save dialog opens (default: Documents)  
* App creates timestamped backup: `DesktopWorkspaces_Backup_2026-05-02_14-30-45.json`  
* Confirmation: "✓ Backup saved to C:\\Users...\\Documents"

**Import Button (\[📥 Import\]):**

* User clicks button  
* File picker opens → user selects backup `.json` file  
* App validates the JSON against schema  
* If valid, show confirmation dialog:

 Replace current profile with this backup?  
    
  Current:  5 desktops, 12 shortcuts  
  Backup:   3 desktops, 8 shortcuts  
    
  (Current profile will be backed up automatically)  
    
  \[Import\]  \[Cancel\]

* If user confirms:  
  * Current profile is auto-backed up to `profile_before_import_TIMESTAMP.json.bak`  
  * New profile is loaded  
  * App refreshes desktops (recreate from imported profile)  
  * Show: "✓ Profile imported. Desktops updated."

#### **Feature 6: Shutdown Auto-Sync (Silent)**

**On app shutdown:**

* Sweep all **enabled desktops** in profile  
* For each desktop:  
  * Switch to that desktop (programmatically)  
  * Scan Windows desktop folder for `.lnk` shortcuts  
  * Compare to profile  
  * **Auto-add** new shortcuts (not in profile)  
  * **Auto-remove** shortcuts no longer on disk  
* Save profile once  
* Log changes (no user prompt)

**Rationale:** If user adds/removes shortcuts via right-click (bypassing Control Panel), they're auto-synced to profile. Control Panel always reflects reality.

#### **Feature 7: Shortcut Position Persistence**

* On shutdown: Capture positions (x, y coordinates) of all shortcuts  
* Store in profile JSON for each shortcut  
* On startup: Restore shortcuts to stored positions (best-effort)  
* If Windows auto-arranges: positions may drift, but we try to restore

---

## **Data Model Update**

### **Profile JSON (Extended)**

json  
{  
  "version": 1,  
  "name": "My Workspaces",  
  "desktops": \[  
    {  
      "id": "cclub-desktop",  
      "name": "CCLUB",  
      "enabled": true,  
      "background\_path": "C:\\\\Users\\\\Bernard\\\\AppData\\\\Local\\\\DesktopWorkspaces\\\\wallpapers\\\\cclub-bg.png",  
      "created\_at": "2026-04-30T10:30:00Z",  
      "shortcuts": \[  
        {  
          "id": "shortcut-uuid-1",  
          "label": "Design Projects",  
          "type": "folder",  
          "path": "C:\\\\Users\\\\Bernard\\\\Projects\\\\Design",  
          "status": "available",  
          "position": {  
            "x": 100,  
            "y": 50  
          },  
          "created\_at": "2026-05-02T14:30:00Z"  
        },  
        {  
          "id": "shortcut-uuid-2",  
          "label": "Photoshop",  
          "type": "app",  
          "path": "C:\\\\Program Files\\\\Adobe\\\\Photoshop\\\\Photoshop.exe",  
          "status": "available",  
          "position": {  
            "x": 200,  
            "y": 50  
          },  
          "created\_at": "2026-05-02T14:32:00Z"  
        },  
        {  
          "id": "shortcut-uuid-3",  
          "label": "Team Assets",  
          "type": "folder",  
          "path": "\\\\\\\\NAS\\\\team\\\\assets",  
          "status": "unavailable",  
          "position": null,  
          "created\_at": "2026-05-02T14:35:00Z"  
        }  
      \]  
    }  
  \]  
}

### **Schema Validation**

* **Strict JSON Schema** defined in `src/utils/schema.py`  
* Validates on load and save  
* Required fields: `version`, `name`, `desktops`  
* Each desktop requires: `id`, `name`, `enabled`, `shortcuts`  
* Each shortcut requires: `id`, `label`, `type`, `path`  
* Optional fields: `background_path`, `position`, `status`, `created_at`

---

## **Modules to Build/Update (Phase 2\)**

### **1\. ShortcutManager (NEW)**

**Responsibility:** Create, delete, validate, and extract info from `.lnk` shortcuts.

**Location:** `src/core/shortcut_manager.py`

**Key Methods:**

python  
def get\_shortcut\_display\_name(target\_path: str) \-\> str  
    \# Extract filename or folder name from path  
    \# Return clean label (no extension for .exe)  
    \# Example: "C:\\Program Files\\Adobe\\Photoshop\\Photoshop.exe" → "Photoshop"

def create\_shortcut(target\_path: str, label: str, output\_dir: str \= None) \-\> str  
    \# Create .lnk file using WScript.Shell  
    \# Store in %APPDATA%\\DesktopWorkspaces\\shortcuts\\ (or specified dir)  
    \# Return path to created .lnk file  
    \# Log success/failure

def delete\_shortcut(shortcut\_path: str) \-\> bool  
    \# Delete .lnk file from disk  
    \# Return True if successful

def validate\_shortcut\_path(target\_path: str) \-\> str  
    \# Check if path exists and is accessible  
    \# Return: "available", "unavailable" (offline), or "dead" (doesn't exist)  
    \# Use 3-second timeout for network paths  
    \# Non-blocking, suitable for background threads

def extract\_lnk\_target(shortcut\_path: str) \-\> str  
    \# Parse .lnk file, extract target path  
    \# Return target path string

def get\_shortcut\_positions\_from\_desktop(desktop\_path: str \= None) \-\> dict  
    \# Read desktop.ini or use Registry to get icon positions  
    \# Return: {shortcut\_name: (x, y), ...}  
    \# If desktop\_path is None, use %USERPROFILE%\\Desktop\\

def set\_shortcut\_position(shortcut\_name: str, x: int, y: int, desktop\_path: str \= None) \-\> bool  
    \# Write position for shortcut to desktop.ini or Registry  
    \# Allow disabling auto-arrange via Registry if needed  
    \# Return True if successful

**Notes:**

* Use `win32com.client.Dispatch("WScript.Shell")` to create `.lnk` files  
* Store shortcuts in `%APPDATA%\DesktopWorkspaces\shortcuts\`  
* Validate paths asynchronously (don't block UI)  
* Log all operations

---

### **2\. DesktopChangeDetector (NEW)**

**Responsibility:** Scan desktops on shutdown, detect new/removed shortcuts, auto-sync profile.

**Location:** `src/core/desktop_change_detector.py`

**Key Methods:**

python  
def scan\_desktop\_for\_shortcuts(desktop\_path: str \= None) \-\> list  
    \# Scan %USERPROFILE%\\Desktop\\ for .lnk files  
    \# Return list of shortcut paths  
    \# If desktop\_path is None, use default Windows desktop folder

def extract\_shortcut\_info(shortcut\_path: str) \-\> dict  
    \# Parse .lnk file, extract: label, target\_path, type (app/folder/file)  
    \# Also get position from desktop.ini/Registry  
    \# Return: {label, target\_path, type, position}

def detect\_changes(actual\_shortcuts: list, profile\_shortcuts: list) \-\> tuple  
    \# Compare actual desktop shortcuts with profile  
    \# Return: (new\_shortcuts, removed\_shortcut\_ids)  
    \# new\_shortcuts: list of shortcut data dicts (not in profile)  
    \# removed\_shortcut\_ids: list of shortcut IDs (in profile but not on disk)

def auto\_sync\_on\_shutdown(profile: dict) \-\> dict  
    \# Main sweep function  
    \# For each enabled desktop:  
    \#   \- Switch to desktop  
    \#   \- Scan for shortcuts  
    \#   \- Detect new/removed  
    \#   \- Auto-add new to profile  
    \#   \- Auto-remove from profile  
    \# Return updated profile  
    \# Log all changes

**Notes:**

* Called on app shutdown  
* Must switch to each desktop to scan its shortcuts  
* Non-blocking, graceful error handling  
* Log all additions/removals

---

### **3\. Schema & Validation (NEW)**

**Responsibility:** Define JSON schema, validate profiles, provide safe load/save.

**Location:** `src/utils/schema.py`

**Key Functions:**

python  
\# PROFILE\_SCHEMA: Full jsonschema definition (see Data Model section above)

def validate\_profile(profile: dict) \-\> tuple\[bool, str\]  
    \# Validate profile against PROFILE\_SCHEMA  
    \# Return: (is\_valid, error\_message or "Valid")

def repair\_profile(profile: dict) \-\> tuple\[dict, list\]  
    \# Remove invalid shortcuts, invalid desktops  
    \# Return: (repaired\_profile, list of repair\_descriptions)  
    \# Log repairs  
---

### **4\. ConfigManager (EXTEND \- Already exists)**

**Updates needed:**

python  
\# Add methods for shortcut management:

def add\_shortcut\_to\_desktop(desktop\_id: str, shortcut: dict) \-\> bool  
    \# Add shortcut dict to desktop's shortcuts list  
    \# Save profile  
    \# Return True if successful

def remove\_shortcut\_from\_desktop(desktop\_id: str, shortcut\_id: str) \-\> bool  
    \# Remove shortcut by ID from desktop  
    \# Save profile  
    \# Return True if successful

def update\_shortcut\_status(desktop\_id: str, shortcut\_id: str, status: str) \-\> bool  
    \# Update shortcut's status field ("available", "unavailable", "dead")  
    \# Save profile  
    \# Return True if successful

def update\_shortcut\_position(desktop\_id: str, shortcut\_id: str, x: int, y: int) \-\> bool  
    \# Update shortcut's position field  
    \# Save profile  
    \# Return True if successful

\# Update existing save/load:

def save\_profile(self, profile: dict) \-\> bool  
    \# Existing implementation, enhance with:  
    \# \- Validate schema before saving  
    \# \- Write to temp file, verify readable, then replace original  
    \# \- Auto-backup previous version to .bak  
    \# Return True if successful, False if validation failed  
    \# Log all operations  
---

### **5\. StartupExecutor (EXTEND \- Already exists)**

**Updates needed:**

python  
def run\_startup():  
    \# Existing: Create desktops, set wallpapers  
    \# NEW: For each desktop:  
    \#   \- Switch to this desktop  
    \#   \- Place shortcuts for this desktop (iterate profile shortcuts)  
    \#   \- Set positions (best-effort)  
    \# NEW: Background validation of shortcut paths (async)  
    \# Return to first desktop on exit

**Key addition:**

python  
def place\_shortcuts\_on\_desktop(desktop\_handle, shortcuts: list) \-\> None  
    \# For each shortcut in list:  
    \#   \- Create/ensure .lnk file exists  
    \#   \- Set position (if available)  
    \#   \- Note: Must be called while target desktop is active  
---

### **6\. ControlPanel UI (EXTEND \- Already exists)**

**Updates needed:**

**Desktop Card Extensions:** Add to each desktop card in the list:

┌─ CCLUB ──────────────────────────────────────────┐  
│ ☑ Enabled                                        │  
│ Background: C:\\Users\\...\\cclub-bg.png           │  
│ \[ Select Background\] \[✕ Delete\]                 │  
├──────────────────────────────────────────────────┤  
│ Shortcuts:                                       │  
│ • Design Projects (folder)    ✅  \[🗑 Remove\]   │  
│ • Photoshop (app)            ✅  \[🗑 Remove\]   │  
│ • Team Assets (network)       ⚠️  \[🗑 Remove\]   │  
├──────────────────────────────────────────────────┤  
│ \[+ Add Shortcut\]                                 │  
└──────────────────────────────────────────────────┘

**Bottom Bar Extensions:** Update button bar to:

\[⚙ Settings\] \[🔧 Diagnostics\] \[💾 Backup\] \[📥 Import\] \[❌ Exit\]

**New UI Components:**

* `DesktopShortcutsWidget` — scrollable list of shortcuts per desktop  
* `ShortcutListItem` — single shortcut display (label, type icon, status indicator, remove button)  
* `AddShortcutDialog` — file picker \+ name confirmation dialog  
* Updated `ControlPanel` — add backup/import button handlers

**New Methods:**

python  
def on\_add\_shortcut\_clicked(self, desktop\_id: str):  
    \# Open AddShortcutDialog  
    \# Get target path and confirmed name  
    \# Create shortcut via ShortcutManager  
    \# Add to profile via ConfigManager  
    \# Refresh desktop card display

def on\_remove\_shortcut\_clicked(self, desktop\_id: str, shortcut\_id: str):  
    \# Confirm: "Remove shortcut?"  
    \# Delete from profile  
    \# Delete .lnk file  
    \# Refresh display

def on\_backup\_clicked(self):  
    \# Open save dialog  
    \# Call ConfigManager.backup\_profile(location)  
    \# Show result dialog

def on\_import\_clicked(self):  
    \# Open file picker  
    \# Validate selected file  
    \# Show preview dialog (current vs. backup desktop/shortcut counts)  
    \# If confirmed: auto-backup current, load imported profile, refresh UI

def refresh\_shortcuts\_for\_desktop(self, desktop\_id: str):  
    \# Reload shortcuts from profile  
    \# Update display (status indicators, list)  
---

### **7\. AddShortcutDialog (NEW)**

**Location:** `src/ui/add_shortcut_dialog.py`

**Responsibility:** File picker \+ name confirmation in two steps.

**Workflow:**

1. User clicks \[+ Add Shortcut\] on desktop card  
2. Dialog opens: "Select a file, folder, or application"  
3. File picker allows multi-file selection, filters by type:  
   * Applications (\*.exe, \*.lnk, \*.com)  
   * Folders (directories)  
   * Files (all files)  
4. User selects one item, clicks Open  
5. Dialog closes, name confirmation dialog appears:

  Shortcut name:  
   \[Photoshop\_\_\_\_\_\_\_\_\_\]  
     
   \[OK\] \[Cancel\]

6. Pre-filled with auto-generated name, user can edit  
7. User confirms  
8. Dialog returns: (target\_path, confirmed\_name)

**Methods:**

python  
def get\_file\_picker\_dialog(self) \-\> tuple\[str, str\]  
    \# Open QFileDialog  
    \# Return: (selected\_path, file\_type)

def get\_name\_confirmation\_dialog(self, auto\_name: str) \-\> tuple\[str, bool\]  
    \# Open simple dialog with text input  
    \# Return: (name\_entered, was\_confirmed)

def exec(self) \-\> tuple\[str, str\] or None  
    \# Main entry point  
    \# Return: (target\_path, confirmed\_name) or None if cancelled  
---

## **Implementation Checklist (Phase 2\)**

### **Module Development**

* **ShortcutManager**  
  * `get_shortcut_display_name()` — smart name extraction  
  * `create_shortcut()` — WScript.Shell .lnk creation  
  * `delete_shortcut()` — file cleanup  
  * `validate_shortcut_path()` — async path validation with timeout  
  * `extract_lnk_target()` — parse .lnk target  
  * `get_shortcut_positions_from_desktop()` — read desktop.ini/Registry  
  * `set_shortcut_position()` — write positions, disable auto-arrange  
  * Unit tests  
* **DesktopChangeDetector**  
  * `scan_desktop_for_shortcuts()` — list .lnk files  
  * `extract_shortcut_info()` — parse .lnk and positions  
  * `detect_changes()` — compare actual vs. profile  
  * `auto_sync_on_shutdown()` — main sweep function  
  * Unit tests  
* **Schema & Validation** (`src/utils/schema.py`)  
  * Define `PROFILE_SCHEMA` (jsonschema)  
  * `validate_profile()` — schema validation  
  * `repair_profile()` — auto-repair corrupted data  
  * Unit tests for validation and repair  
* **ConfigManager Extensions**  
  * `add_shortcut_to_desktop()` — add to profile  
  * `remove_shortcut_from_desktop()` — remove from profile  
  * `update_shortcut_status()` — update status field  
  * `update_shortcut_position()` — update position field  
  * Enhance `save_profile()` — schema validation, temp file, backup  
  * Enhance `load_profile()` — graceful fallback on error  
  * Unit tests  
* **StartupExecutor Updates**  
  * `place_shortcuts_on_desktop()` — create/place .lnk while on desktop  
  * Integrate into `run_startup()` — loop desktops, switch, place shortcuts  
  * Background validation of shortcut paths  
  * Return to first desktop on exit  
  * Test on restart  
* **ControlPanel UI Updates**  
  * Extend `DesktopCard` to display shortcuts list  
  * Create `ShortcutListItem` widget  
  * Create `DesktopShortcutsWidget` container  
  * Add \[+ Add Shortcut\] button per desktop  
  * Add \[🗑 Remove\] button per shortcut  
  * Add status indicators (✅ ⚠️ ❌)  
  * Update bottom button bar: \[💾 Backup\] \[📥 Import\]  
  * Wire up button handlers  
  * Test UI interactions  
* **AddShortcutDialog** (NEW)  
  * Create file picker dialog  
  * Create name confirmation dialog  
  * Integrate auto-name generation  
  * Handle user confirmation  
  * Return (target\_path, confirmed\_name)  
* **Backup & Import Features**  
  * `ConfigManager.backup_profile()` — create timestamped backup  
  * `ConfigManager.import_profile()` — load, validate, auto-backup current, save  
  * \[💾 Backup\] button handler — save dialog, file creation, confirmation  
  * \[📥 Import\] button handler — file picker, preview dialog, confirmation, refresh  
  * Test backup/import round-trip  
  * Test recovery from corrupted profile

---

### **Testing**

* Unit tests for each module (ShortcutManager, DesktopChangeDetector, Schema)  
* Integration test: Create desktop → add shortcuts → restart → verify shortcuts persist  
* Integration test: Shutdown with new/removed shortcuts → verify auto-sync  
* Integration test: Position persistence (best-effort)  
* Integration test: Backup & import workflow  
* Edge cases:  
  * Network paths (with 3-sec timeout)  
  * Invalid/dead shortcuts  
  * Missing .lnk files during sync  
  * Corrupted JSON on load (fallback to default)  
  * Invalid backup file on import (rejection \+ error message)  
* Manual testing:  
  * Add shortcut via Control Panel  
  * Remove shortcut via Control Panel  
  * Add shortcut via right-click (should auto-sync on shutdown)  
  * Remove shortcut via right-click (should auto-sync on shutdown)  
  * Backup profile, delete desktop, import backup, verify restoration  
  * Edit profile.json manually (break it), restart app (fallback \+ log)  
  * Restart computer, verify desktops \+ shortcuts reappear

---

## **Profile Safety Strategy (Bombproof JSON)**

### **1\. Strict Schema Validation**

* JSON Schema defined in `src/utils/schema.py`  
* Validates on load and save  
* Rejects malformed data with clear error messages

### **2\. Safe Load with Fallback**

* If JSON doesn't exist: create default profile  
* If JSON is corrupted: log error, fall back to default, user warned  
* If JSON is valid but schema-invalid: log error, repair or fallback

### **3\. Safe Save with Backup**

* Validate schema before writing  
* Write to temp file (`.tmp`)  
* Verify temp file is readable  
* Auto-backup current file (`.bak`)  
* Replace original only after success  
* Log all operations

### **4\. Migration & Versioning**

* Profile has `"version"` field (currently 1\)  
* Future: detect old version, apply migrations, upgrade  
* Transparent to user

### **5\. Repair Tool**

* `repair_profile()` function removes invalid shortcuts/desktops  
* Preserves as much valid data as possible  
* Logs what was repaired  
* User can trigger via Control Panel \[🔧 Diagnostics\] → "Repair Profile" button

### **6\. Backup & Import Controls**

* \[💾 Backup\] — user manually saves timestamped backup  
* \[📥 Import\] — user imports backup with validation \+ preview  
* Auto-backup before import (current state preserved)  
* Full round-trip recovery possible

---

## **Key Design Principles (Phase 2\)**

1. **User Control:** Shortcuts can be created via Control Panel or Windows right-click  
2. **Auto-Sync:** All changes (via right-click) are silently synced to profile on shutdown  
3. **Simplicity:** No prompts or dialogs during sync; Control Panel always reflects reality  
4. **Safety:** Profile is validated, backed up, and recoverable at every step  
5. **Icon Freedom:** Users customize icons via Windows standard UI (right-click → Properties)  
6. **Position Persistence:** Best-effort; if Windows auto-arranges, that's acceptable  
7. **Graceful Degradation:** Missing paths \= status indicators, not crashes

---

## **Known Constraints & Decisions**

1. **Shortcut Placement:** Virtual desktops are containers, not filesystems. Shortcuts must be placed by switching to each desktop, creating the .lnk while on that desktop.  
2. **Position Storage:** Positions stored in profile \+ written to desktop.ini/Registry. Windows may auto-arrange; we accept this and try to restore.  
3. **No Icon Path Storage:** Icons are embedded in .lnk files (Windows standard). No extra profile field needed.  
4. **Auto-Sync on Shutdown:** No user prompt; changes are silently synced. User can undo via Control Panel.  
5. **Schema Validation:** All profile operations validated against strict schema. Invalid data rejected or repaired.  
6. **Fallback Strategy:** If anything goes wrong, fall back to default profile. User can recover via import.

---

## **Success Criteria (Phase 2\)**

* ✅ User can add shortcut via Control Panel \[+ Add Shortcut\]  
* ✅ User can remove shortcut via Control Panel \[🗑 Remove\]  
* ✅ User can add/remove shortcuts via right-click (auto-synced on shutdown)  
* ✅ Shortcuts persist across restarts  
* ✅ Shortcut status indicators work (✅ ⚠️ ❌)  
* ✅ Shortcut positions are captured and restored (best-effort)  
* ✅ Icons can be customized via Windows standard UI  
* ✅ Profile backup works (\[💾 Backup\])  
* ✅ Profile import works with validation \+ preview (\[📥 Import\])  
* ✅ Profile JSON is safe: validated, backed up, recoverable  
* ✅ Corrupted JSON gracefully falls back to default  
* ✅ All changes logged (startup, shutdown, sync, backups)  
* ✅ No crashes on invalid paths, network timeouts, or missing files  
* ✅ UI is clean, intuitive, one-click actions

---

## **Questions for Claude Code Sessions**

When starting each coding session, clarify:

1. **Which module(s) are we building?** (e.g., ShortcutManager, DesktopChangeDetector, UI)  
2. **What's the MVP for this module?** (minimal viable behavior)  
3. **What are the failure modes we need to handle?** (network timeout, invalid path, etc.)  
4. **How do we test this module in isolation?** (unit tests, manual steps)  
5. **Where does error logging go?** (which method, which file)  
6. **What dependencies does this module have?** (other modules it calls)  
7. **What's the next session's module?** (dependency order)

---

## **Development Approach**

* **Use Claude Code with Pro account** for iterative, file-level edits  
* **Keep this brief as source of truth** across sessions  
* **Build module by module**, test incrementally  
* **Use view and str\_replace tools** for targeted edits, not full codebase regeneration  
* **Commit after each major feature** (e.g., ShortcutManager complete, DesktopChangeDetector complete)  
* **Test early and often** — don't wait until the end

---

## **Reference Context**

**Similar Project:** MediaVerse (same org, same architecture patterns)

* Dark aesthetic with warm metallic accents (`#B8956A` bronze)  
* Config-driven startup pipeline  
* JSON-based state management  
* Iterative UI refinement

**Tech Stack Justification:**

* **Python:** Cross-platform, iterative, good Windows API support  
* **PySide6:** Native Windows feel, good dark theme support  
* **pywin32:** Direct access to Windows virtual desktop API  
* **jsonschema:** Strict profile validation  
* **pathlib:** Cross-platform path handling  
* **logging:** Rotating file logs for diagnostics

---

## **Document Metadata**

**Version:** 2.0  
 **Last Updated:** 2026-05-02  
 **Author:** Bernard (with Claude)  
 **Status:** Ready for Claude Code Handoff  
 **Next Phase:** Phase 3 (Multi-Machine Support / Export-Import with Path Adjustment)

