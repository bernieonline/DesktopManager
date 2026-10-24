# Desktop Workspaces — Known Issues and Next Steps

## Bugs and Rough Edges

### `register_startup.ps1` uses RunLevel Highest
**File:** `register_startup.ps1` line 11
**Impact:** If someone runs this script, the Task Scheduler task will use `RunLevel: Highest`, which breaks OLE drag-and-drop (UIPI blocks drops from non-elevated Explorer).
**Fix:** Change `RunLevel Highest` to `RunLevel Limited`.

### BRONZE constant is actually blue
**File:** `src/ui/styles.py` line 1
`BRONZE = "#4FC3F7"` — this is bright blue, not bronze (`#B8956A`). The variable name is misleading. Either rename the constant or restore the original bronze colour. The original brief and design docs specify bronze.

### Log file rotation conflict
**Impact:** When two instances of the app run simultaneously (startup executor + debug session), the `TimedRotatingFileHandler` fails to rotate `app.log` because another process holds the file lock. This produces a noisy error in the console but is otherwise harmless.
**Possible fixes:** Use `delay=True` on the handler, add per-instance log suffixes, or switch to `RotatingFileHandler` with a lockfile.

### `pyshortcuts` in requirements.txt but unused
**File:** `requirements.txt`
The `pyshortcuts` package is listed as a dependency but is never imported. `.lnk` creation uses `win32com.client.Dispatch("WScript.Shell")` directly. Consider removing it from requirements.txt to reduce install size.

### Window is solid, not translucent
**Files:** `src/ui/shop_window.py`
The original design called for a semi-transparent background (`rgba(18, 18, 18, 160)`) so the desktop wallpaper bleeds through. This was removed during DnD debugging (suspected cause — later ruled out; TeraCopy was the actual blocker). The window now uses `WA_NoSystemBackground` + `setMask()` for rounded corners and a solid `QColor(18, 18, 18)` background.
**To restore:** Remove `WA_NoSystemBackground` and `setMask()`, add back `WA_TranslucentBackground`, restore alpha in paintEvent. Should work now that the real DnD issues are fixed.

### ~~.url (web shortcut) files may lose their icon when dragged into the shop window~~
**Fixed.** Icon caching at drop time preserves favicons for `.url` files and custom `IconLocation` for `.lnk` files. `.url` files are now parsed for their URL so the shortcut works without the original file. See decisions-log.md for details.

### Tests are manual scripts, not a proper test suite
**Files:** `tests/test_config_manager.py`, etc.
Tests are `if __name__ == "__main__"` scripts with assert statements. No pytest, no CI, no coverage. This makes it easy to regress.

### No safe mode implementation
The CLAUDE.md brief describes safe mode (if startup crashes, next launch opens in safe mode), but no safe mode logic exists in the code. `StartupExecutor.run()` has basic try/except but does not set or check a crash flag.

### NSIS installer doesn't use Task Scheduler
**File:** `installer/DesktopWorkspaces.nsi`
The installer registers startup via a Registry Run key (`HKCU\...\Run`), not Task Scheduler. The Run key approach was the one that failed during development (Fix 7 — shop window never appeared after reboot). The dev machine uses Task Scheduler instead. These two approaches need to be reconciled. (unverified — the Run key approach in the installer may work for frozen builds because the startup executor is a separate .exe, unlike the dev setup where it's a Python script.)

---

## Unfinished Items from Plans

### From Phase 2 Plan
- **DesktopChangeDetector** — shutdown scan of Desktop folder for new items. Dropped because the shared Desktop folder discovery made it inapplicable, but the concept of detecting user-added shortcuts is still valid for future consideration.
- **Shortcut position persistence** — capturing and restoring x,y positions of shortcuts on the desktop. Dropped because shortcuts are now in the shop window, not on the Desktop folder.
- **Shutdown auto-sync** — scanning Desktop folder on app close. Not applicable in current architecture.

### From CLAUDE.md Brief
- **Export/Import with Path Adjustment Wizard** — Phase 3 feature. During import on a new machine, paths that don't exist locally should prompt the user to pick the correct location. Network paths are confirmed once. No automatic path mapping.
- **Safe mode** — if startup crashes, next launch runs in safe mode (skip desktop creation, open config panel). Not implemented.
- **Check Network Paths button** — manual revalidation of all shortcut paths. The background validator runs on startup but there's no explicit "recheck now" button in the shop window (the manage panel has no revalidation trigger).
- **Diagnostic report generator** — one-click report with Windows version, Python version, desktop list, shortcut paths, last error log. The control panel has a basic diagnostics dialog but not a full report.

---

## Next Features (Rough Priority Order)

### 1. Fix `register_startup.ps1` RunLevel
Trivial fix, high impact. Change `RunLevel Highest` to `RunLevel Limited`. Prevents the most common DnD failure mode.

### 2. Proper test suite
Convert manual test scripts to pytest. Add tests for:
- Schema validation and repair (edge cases)
- ShortcutManager: create/delete .lnk, validate_path
- ConfigManager: full CRUD round-trip, backup/import
- Profile corruption recovery

### 3. Restore window translucency
Add back `WA_TranslucentBackground` now that DnD root cause is confirmed. This gives the designed aesthetic (wallpaper bleed-through behind the dark overlay).

### 4. Safe mode
Implement crash detection: write a "starting" flag before desktop sync, clear it after success. If the flag exists on next startup, skip desktop operations and open the config panel.

### 5. Revalidation button
Add a "Recheck Paths" action to the shop window (footer or manage panel) that re-runs `ShortcutValidator` on demand.

### 6. Phase 3 — Multi-machine export/import with path adjustment wizard
- Export profile to JSON
- Import on a new machine
- For each shortcut path that doesn't exist locally: prompt user to pick the correct location via folder picker
- Auto-confirm paths that exist
- Network paths: confirm once

### 7. Installer reconciliation
Decide whether installed builds should use Registry Run key or Task Scheduler. Test the Run key approach with frozen .exe builds. If it works, keep it (simpler). If not, have the NSIS installer create a Task Scheduler task.

### 8. System tray integration
Consider adding a system tray icon so the app has a persistent presence and can be accessed without the Desktop shortcut. Would also provide a natural place for a "Quit" action.

### 9. Shortcut editing
Allow renaming shortcuts and changing their target path without removing and re-adding.

### 10. Conditional shortcuts
Only show shortcuts for apps that are actually installed. If a shortcut's target doesn't exist, offer to hide it instead of just showing a red status dot.

### 11. Desktop background per desktop (shop window integration)
The control panel can set wallpapers, but the shop window has no wallpaper UI. Consider adding a wallpaper selector to the manage panel.

---

*Generated 2026-10-24 from codebase at commit b6e87db*
