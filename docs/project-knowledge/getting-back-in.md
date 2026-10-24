# Desktop Workspaces — Getting Back In (Runbook)

## Repository

- **GitHub:** `https://github.com/bernieonline/DesktopManager.git`
- **Local path:** `D:\DesktopProject\`

## Activating the Environment

```bash
# IMPORTANT: plain `python` on this machine points to Python 3.9 (MediaVerse project).
# Always use the venv Python explicitly.

# Activate venv (PowerShell)
D:\DesktopProject\.venv\Scripts\Activate.ps1

# Or just use the full path directly
D:\DesktopProject\.venv\Scripts\python.exe
D:\DesktopProject\.venv\Scripts\pythonw.exe   # GUI (no console window)
```

## Running the App

| Mode | Command |
|------|---------|
| **Shop window** (normal use) | `.venv\Scripts\pythonw.exe main.py` |
| **Shop window** (with console for debugging) | `.venv\Scripts\python.exe main.py` |
| **Startup mode** (what runs at logon) | `.venv\Scripts\pythonw.exe main.py --startup` |
| **Full control panel** (Phase 1 management UI) | `.venv\Scripts\pythonw.exe main.py --control-panel` |

The shop window appears in the top-right corner of the screen. Switch between Windows virtual desktops (Win+Ctrl+Left/Right) and the shop window will update to show the active desktop's shortcuts.

## Running Tests

Tests are manual scripts, not pytest:

```bash
.venv\Scripts\python.exe tests\test_config_manager.py
.venv\Scripts\python.exe tests\test_startup_executor.py
.venv\Scripts\python.exe tests\test_virtual_desktop_manager.py
```

There are also research spikes in `tests/spike_*.py` — these are exploratory scripts, not automated tests.

## Startup Task Registration

### Development machine (Task Scheduler)

The dev machine uses a Task Scheduler task named `DesktopWorkspaces`:

```powershell
# View current task
schtasks /query /tn "DesktopWorkspaces" /fo LIST /v

# Register (or re-register) — MUST use RunLevel Limited, not Highest!
$action = New-ScheduledTaskAction `
    -Execute "D:\DesktopProject\.venv\Scripts\pythonw.exe" `
    -Argument '"D:\DesktopProject\main.py" --startup' `
    -WorkingDirectory "D:\DesktopProject"
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
Register-ScheduledTask -TaskName "DesktopWorkspaces" `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force

# Remove the task entirely
schtasks /delete /tn "DesktopWorkspaces" /f
```

**WARNING:** `register_startup.ps1` in the repo still has `RunLevel Highest` — this will break drag-and-drop. Always use `Limited`.

### Installed builds (Registry Run key)

The NSIS installer writes a Run key at `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Desktop Workspaces` pointing to `DesktopWorkspacesStartup.exe`.

To check/remove:
```powershell
# Check
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Desktop Workspaces" -ErrorAction SilentlyContinue

# Remove
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Desktop Workspaces"

# Also check for legacy entries
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Desktop Workspaces Startup" -ErrorAction SilentlyContinue
```

## Where to Look When Something Breaks

### 1. Logs (first stop)

```
%LOCALAPPDATA%\DesktopWorkspaces\logs\app.log
```

Structured format: `[timestamp] [LEVEL] [ModuleName] message`. Rotated at midnight, 7-day retention.

If two instances run simultaneously (e.g., startup + debug), the log file rotation will fail with a harmless error in the console. The log file is still written to.

### 2. Profile corruption

```
%LOCALAPPDATA%\DesktopWorkspaces\profile.json      # Current
%LOCALAPPDATA%\DesktopWorkspaces\profile.json.bak   # Auto-backup from last save
```

If the profile is corrupted, the app will attempt auto-repair via `repair_profile()` in `src/utils/schema.py`. If repair fails, it falls back to an empty profile. The `.bak` file preserves the previous state.

### 3. Drag-and-drop not working

Check in this order:
1. **Is the app running elevated?** DnD will silently fail. Check Task Manager -> right-click the process -> Properties. If elevated, fix the Task Scheduler task (`RunLevel: Limited`).
2. **Was VS Code launched as Admin?** All child processes inherit elevation.
3. **Third-party shell extensions?** TeraCopy, certain antivirus OLE hooks, and other copy handlers can intercept the Windows OLE drag pipeline globally.
4. **Check logs** for `OleInitialize` result and `_do_register_drop` messages.

### 4. Virtual desktops not appearing

- The app does NOT create virtual desktops — it only matches existing ones. Create desktops manually with Win+Ctrl+D.
- `sync_desktops()` matches by name (case-insensitive). If you renamed a desktop in Windows, the profile won't match.

### 5. Shop window not showing after reboot

Check the Task Scheduler task is running:
```powershell
schtasks /query /tn "DesktopWorkspaces" /fo LIST
```

Check logs for `StartupExecutor` entries. The shop window launches with a 15-second delay after the startup executor finishes.

## Building the Installer

```bash
# 1. Build with PyInstaller (from project root, venv activated)
pyinstaller --name DesktopWorkspaces --noconsole main.py
pyinstaller --name DesktopWorkspacesStartup --noconsole main_startup.py

# 2. Build NSIS installer
"C:\Program Files (x86)\NSIS\makensis.exe" installer\DesktopWorkspaces.nsi

# Output: dist\DesktopWorkspaces_Setup.exe
```

## Gotchas You'll Forget

1. **`python` is Python 3.9.** Always use `.venv\Scripts\python.exe`.

2. **RunLevel must be `Limited`.** If DnD stops working after a reboot, the first thing to check is whether the Task Scheduler task or the process is running elevated. `register_startup.ps1` in the repo has `RunLevel Highest` — do not run it as-is.

3. **`BRONZE` is blue.** `styles.py` defines `BRONZE = "#4FC3F7"` (bright blue). The original bronze was `#B8956A`. The variable was never renamed.

4. **Shop window is ~1100 lines.** `shop_window.py` is the largest module. Most bugs and features live here. Read it before making changes.

5. **`setAcceptDrops(True)` is cached by PySide6.** After an external `RevokeDragDrop`, calling `setAcceptDrops(True)` does NOT re-register the IDropTarget. Only destroying and recreating the native window forces re-registration. Never use `RevokeDragDrop` as a diagnostic probe.

6. **OleInitialize must happen before QApplication.** This is done in `main.py` line 35. If you refactor the entry point, keep this order.

7. **Desktop folder may be on OneDrive.** The app reads the Desktop path from the Registry (`HKCU\...\Shell Folders\Desktop`), not from `%USERPROFILE%\Desktop`. On this machine it resolves to `C:\Users\berna\OneDrive\Desktop`.

8. **Log rotation conflict.** If you run the app in debug mode (with console) while the startup task is also running, the rotating log handler will fail to rotate. Harmless, but noisy.

9. **Wallpapers are copied locally.** When the user selects a wallpaper, it's copied to `%LOCALAPPDATA%\DesktopWorkspaces\wallpapers\`. The profile stores the local path, not the original.

10. **`pyshortcuts` is in requirements.txt but not used.** `.lnk` creation uses `win32com.client.Dispatch("WScript.Shell")` directly.

---

*Generated 2026-10-24 from codebase at commit b6e87db*
