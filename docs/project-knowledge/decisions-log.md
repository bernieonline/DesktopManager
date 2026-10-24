# Desktop Workspaces — Decisions Log

Newest first. Each entry records what was decided, why, and what alternatives were considered or rejected.

---

## 2026-05 — Session 12

### Startup delay reduced from 30s to 15s
**Decision:** Reduce the `--delay` flag passed to the shop window process from 30s to 15s.
**Why:** The 30-second delay was introduced during the "OLE timing" investigation (Sessions 9-10), which turned out to be a misdiagnosis — the real issue was UIPI elevation. The delay is kept as a UX buffer (let Explorer finish loading) but 30s was arbitrary and too long.
**Commit:** `6a9ff62` Reduce shop window startup delay from 30s to 15s

### Resize cursor fixed with pure Qt mouse events
**Decision:** Replace `WM_NCHITTEST`/`HTBOTTOM` native resize handling with pure Qt `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent`.
**Why:** WM_NCHITTEST returning HTBOTTOM for the bottom resize zone caused Windows to set the resize cursor globally across the entire frameless window, making footer buttons unclickable.
**Commit:** `942b504` Fix shop window resize cursor sticking over entire window

---

## 2026-05 — Session 11

### UIPI elevation identified as root cause of all drag-and-drop failures
**Decision:** Task Scheduler task changed from `RunLevel: Highest` to `RunLevel: Limited`. App must never run elevated.
**Why:** Windows UIPI (User Interface Privilege Isolation) blocks OLE drag-and-drop from non-elevated processes (Explorer, Medium integrity) to elevated processes. The Task Scheduler task had `RunLevel: Highest`, making the entire app chain run elevated. Explorer runs at Medium integrity. Windows silently blocks all OLE drop routing across this boundary — no error, no log, just the "blocked" cursor.
**Why it took so long to find:** VS Code was running as Administrator, so all processes launched from its terminal also inherited elevation. Every manual test was doomed to fail for the same reason as the boot-time test. The `RevokeDragDrop` probe returning S_OK was a red herring — registration existed at the COM level, but drops were blocked by UIPI at the kernel level.
**Rejected alternative:** The "OLE timing at boot" diagnosis from Sessions 9-10 was incorrect. The 30-second delay appeared to help by coincidence.

### Destructive RevokeDragDrop probe removed
**Decision:** Remove `RevokeDragDrop` as an OLE registration "probe" from `_do_register_drop()`.
**Why:** RevokeDragDrop is destructive — it removes the working IDropTarget registration. PySide6 caches the `acceptDrops` state internally, so a subsequent `setAcceptDrops(True)` does NOT call `RegisterDragDrop` again. This was a secondary bug that made boot-time DnD unreliable even after the elevation fix.
**Replacement:** Simple `setAcceptDrops(False)` then `setAcceptDrops(True)`, plus periodic re-registration (30s x 10 = 5 min) as a safety net.

---

## 2026-05 — Session 10

### Shop window launched via subprocess.Popen from startup executor
**Decision:** `StartupExecutor._launch_shop_window()` spawns `[pythonw, main.py, --delay, N]` as `DETACHED_PROCESS | CREATE_NO_WINDOW`.
**Why:** The Task Scheduler task reliably runs on every logon, so it can spawn the shop window. The startup executor exits quickly (< 2s), and the shop window starts independently after the delay.
**Rejected alternative:** Registry Run key (`HKCU\...\Run`) was tried in Session 9 (Fix 7) but failed — the shop window process never started after reboot. The Run key approach was abandoned.
**Commits:** `a151f39`, `b1a6061`

---

## 2026-05 — Session 8

### Consolidated to single startup Run key (later revised)
**Decision:** Removed the duplicate Registry Run key entry that was spawning a second shop window instance.
**Why:** Both the Task Scheduler task and a Registry Run key were launching the startup executor, resulting in two shop window processes.
**Commit:** `b6e87db` Fix duplicate process spawning: consolidate to single startup Run key

---

## 2026-05 — Session 5-7

### TeraCopy identified as shell extension blocker
**Decision:** Documented that TeraCopy (third-party file manager) intercepts Windows OLE drag pipeline globally, preventing all file drops from reaching any drop target.
**Why:** Removing TeraCopy unblocked OLE drag-and-drop routing. This was purely a user-machine configuration issue, not a code bug.
**Rule going forward:** If drag-and-drop stops working, check for third-party shell extensions (TeraCopy, copy handlers, antivirus OLE hooks) before debugging window flags.

### WA_TranslucentBackground removed, replaced with setMask()
**Decision:** Use `WA_NoSystemBackground` + `setMask()` via `QPainterPath.addRoundedRect()` for rounded corners instead of `WA_TranslucentBackground`.
**Why:** During DnD investigation, `WA_TranslucentBackground` was suspected of causing issues (it makes Qt use `UpdateLayeredWindow` / per-pixel alpha / `WS_EX_LAYERED`, which Windows 11 24H2 may skip for OLE drop routing). Later confirmed that TeraCopy was the actual blocker, but the change was kept as it's simpler and avoids a known Windows edge case.
**Trade-off:** No wallpaper bleed-through in the rounded corners. Could be restored if desired.

### WS_EX_NOACTIVATE replaced with WM_MOUSEACTIVATE handler
**Decision:** Use `WM_MOUSEACTIVATE` -> `MA_NOACTIVATE` in `nativeEvent` instead of the `WS_EX_NOACTIVATE` extended window style.
**Why:** `WS_EX_NOACTIVATE` signals to the shell that the window cannot receive input. Windows 11 skips such windows for OLE drop routing entirely.

### HWND_BOTTOM replaced with HWND_NOTOPMOST
**Decision:** Use `HWND_NOTOPMOST` instead of `HWND_BOTTOM` for z-order positioning.
**Why:** `HWND_BOTTOM` placed the window behind `SysListView32` (the desktop icon layer). `WindowFromPoint` found the icon layer first, so OLE drops never reached the shop window.

---

## 2026-05 — Phase 2 Design

### Shared Desktop folder discovery — pivot to the shop window
**Decision:** Abandon per-desktop shortcut placement on the Windows Desktop. Instead, use a "shop window" overlay that detects the active virtual desktop and shows only that desktop's shortcuts.
**Why:** Windows virtual desktops share a single filesystem folder (`%USERPROFILE%\Desktop`). Any file placed there appears on every virtual desktop simultaneously. Per-desktop shortcut isolation via the Desktop folder is architecturally impossible.
**What was dropped from the Phase 2 brief:**
- Shortcut placement on the Windows Desktop folder
- Shortcut position persistence via Registry/desktop.ini
- Shutdown auto-sync by scanning the Desktop folder
- DesktopChangeDetector module (no longer needed)
**What was kept:** A single Control Panel .lnk in the shared Desktop folder — it naturally appears on every virtual desktop.

### Desktop matching uses pyvda GUID (`windows_vd_id`)
**Decision:** Each profile desktop stores a `windows_vd_id` field containing the pyvda GUID of the Windows virtual desktop it's linked to.
**Why:** Desktop names can be duplicated or changed by the user. The GUID is a stable identifier. Matching falls back to name match and upgrades old entries that lack a GUID.

### No explicit "create desktop" flow in shop window
**Decision:** The shop window does not create Windows virtual desktops. The user creates them via Windows (Win+Ctrl+D). The shop window auto-registers a new desktop in the profile when the user first adds a shortcut to an unrecognised desktop.
**Why:** Simpler UX — users already know how to create virtual desktops. The shop window focuses on shortcut management.

### sync_desktops() is match-only
**Decision:** `VirtualDesktopManager.sync_desktops()` matches profile entries to existing Windows desktops but does NOT create or delete desktops.
**Why:** The user manages virtual desktops via Windows. The app only provides shortcuts and wallpapers.

---

## 2026-05 — Phase 2 Infrastructure

### OleInitialize before QApplication
**Decision:** Call `ctypes.windll.ole32.OleInitialize(None)` in `main.py` before creating `QApplication`.
**Why:** PySide6 6.11.0 does not reliably call `OleInitialize` before `RegisterDragDrop`. Without it, `setAcceptDrops(True)` silently fails to register the IDropTarget, and OLE drag-and-drop never fires.

### QApplication.setQuitOnLastWindowClosed(False)
**Decision:** Prevent the app from exiting when the full control panel window is closed.
**Why:** The shop window is the primary UI and should keep running even if the user opens and closes the control panel.

### Safe save for profile.json
**Decision:** Write to `.tmp` -> verify readable -> backup to `.bak` -> replace original. Validate schema before writing.
**Why:** Profile corruption would lose all workspace configuration. The safe save ensures the original is never overwritten with bad data.

### jsonschema for profile validation + repair
**Decision:** Use the `jsonschema` library for strict validation, with a `repair_profile()` function that strips invalid entries while preserving valid data.
**Why:** Users might hand-edit the JSON, or a bug could write partial data. Repair is better than losing everything.

---

## 2026-04 — Phase 1 / Project Start

### PySide6 over PyQt6
**Decision:** Use PySide6 despite the project brief specifying PyQt6.
**Why:** PySide6 is the official Qt for Python binding, has identical API surface, and avoids GPL licensing concerns (PySide6 is LGPL). (unverified — the exact reason may have been pragmatic availability in the venv)

### pyvda as the virtual desktop backend
**Decision:** Use pyvda 0.5.0 for virtual desktop management.
**Why:** pyvda wraps the undocumented Windows `IVirtualDesktopManager` COM interface. It's the most actively maintained Python library for this purpose. Confirmed working on Windows 11 24H2 (build 26200).
**Alternatives rejected:** Direct COM calls via comtypes (lower-level, more fragile), VirtualDesktopAccessor.dll (C++ DLL, harder to bundle).

### Per-user install (no admin required)
**Decision:** NSIS installer uses `RequestExecutionLevel user`, installs to `%LOCALAPPDATA%\Programs\`.
**Why:** The app manages virtual desktops and shortcuts — no system-level changes needed. A per-user install avoids UAC prompts and is consistent with the "must not run elevated" requirement for OLE drag-and-drop.

### Registry Run key for installed builds, Task Scheduler for dev
**Decision:** The NSIS installer registers startup via `HKCU\...\Run` key. The dev environment uses a Task Scheduler task.
**Why:** The Run key is simpler and more reliable for installed builds. Task Scheduler was used during development for easier iteration, but `register_startup.ps1` still has `RunLevel: Highest` which is a known bug (should be `Limited`).

### Accent colour changed from bronze to blue
**Decision:** `styles.py` `BRONZE` constant changed from `#B8956A` to `#4FC3F7` (bright blue).
**Why:** User preference during Phase 2 development. The variable name `BRONZE` was kept for backward compatibility. The shop window border and header still reference it.

---

### Icon caching for .url and custom-icon .lnk files
**Decision:** Cache the shell icon of the **original dropped file** as a PNG at drop time, store the path in the profile's `icon_cache` field, and prefer it in `ShortcutTile._load_icon()`.
**Why:** Two classes of shortcuts lost their icon:
1. `.url` (web shortcut) files — the favicon is only accessible while the `.url` file exists. If the user accepts the "Remove original from Desktop?" prompt, the file is gone and the icon falls back to a generic file icon.
2. Chrome/Edge "Install as app" `.lnk` files — these have a custom `IconLocation` pointing to a cached favicon. `_handle_drop()` resolved the `.lnk` to its target (`chrome_proxy.exe`), so `get_shell_icon()` showed the generic `.exe` icon instead of the web app's icon.
**Implementation:**
- `cache_icon(source_path, shortcut_id)` in `shortcut_manager.py` saves a PNG to `%LOCALAPPDATA%\DesktopWorkspaces\icons\{shortcut_id}.png`.
- Icon extraction chain: `.url` IconFile → `.lnk` IconLocation → `SHGetFileInfoW` → `QFileIconProvider` (fallback).
- `parse_url_file(url_path)` reads the URL from `.url` files (INI format) so `os.startfile()` can open the URL directly without the original file.
- `_handle_drop()` caches the icon from the original dropped file before the removal prompt.
- `_on_add_shortcut()` also caches icons for files added via the dialog.
- `ShortcutTile._load_icon()` checks `icon_cache` first; falls back to live `get_shell_icon()`.
- `SHORTCUT_SCHEMA` includes `icon_cache` as an optional field.
**Pitfalls encountered:**
- `QFileIconProvider` does NOT read custom icon metadata from `.url`/`.lnk` files — returns generic file-type icons only.
- `SHGetFileInfoW` requires backslash-normalised paths (`os.path.normpath`) — forward slashes cause silent failure (returns 0).
- HICON-to-QPixmap via raw ctypes failed with `OverflowError: int too long to convert` on 64-bit handles. Fixed by using pywin32 (`win32gui.DrawIconEx` into a DIB section) instead of raw ctypes `GetObjectW`.
**Commit:** `5889c55` Add icon caching for .url and custom-icon .lnk shortcuts

---

*Updated 2026-10-24 at commit 5889c55*
