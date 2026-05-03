**Desktop Workspaces: Project Brief**

**Project Vision**

Windows 10 and 11 Environment. A tool for organized, project-minded professionals that creates and manages multiple curated desktop workspaces. Each desktop is populated with shortcuts to folders and applications, persists across restarts, and syncs across machines via optional export/import.

**Target User:** Experienced Windows users, developers, designers, and professionals who think in workspaces and value organization. They hate wasting time on repetitive setup.

---

**Problem Statement**

* **Desktop Persistence:** Windows doesn't persist desktop contents across restarts, made worse when the desktop folder syncs to OneDrive  
* **Workspace Fragmentation:** Apps and project folders scattered across Start Menu, File Explorer, and taskbar — no coherent workspace organization  
* **Repeated Setup:** Every startup requires manual recreation of workspace layouts  
* **Multi-Machine Sync:** Different machines have different paths; syncing raw paths breaks shortcuts

---

**Core Solution — Desktop Profiles with Shortcuts**

Users create named desktop profiles (e.g., "Design," "Development," "Writing"). Each profile contains curated shortcuts to folders (project assets, reference materials) and applications. On startup, the app automatically creates the defined desktops and populates them with shortcuts. During the day, users can modify desktops via a control panel; on shutdown, new items trigger an optional save prompt.

**Why Shortcuts?**

* Lightweight: Just pointers, not actual files or copies  
* Stable: Won't be corrupted by OneDrive sync  
* Leverages existing structure: Users already have organized folders; shortcuts link directly to them  
* One-click access: No nested Start Menu archaeology, no folder drilling  
* App shortcuts on every desktop: The control panel itself is shortcut-accessible for instant edits

---

**Key Features (v1)**

*Desktop Management:* Create, delete, enable/disable named desktops. Each desktop is a Windows virtual desktop linked to a profile. Desktops recreate on startup (instant, atomic process).

*Shortcut Management:* Add shortcuts to folders and apps (via file/app picker). Edit labels, remove shortcuts. Visual status indicators (available, unavailable, dead).

*Profile System:* Profiles stored locally as JSON. User can enable/disable desktops (disabled desktops don't recreate on startup). Delta detection on shutdown: if new items added to desktop during session, prompt user to save them.

*Export/Import (Multi-Machine Support):* Export: User saves current profile to OneDrive (or any cloud storage/file share). Import: User imports on new machine. Path Adjustment Wizard: During import, user confirms or adjusts paths for each shortcut. Paths that exist locally are auto-confirmed; paths that don't exist require the user to pick the correct location via folder picker. Network paths: usually unchanged, user confirms once. No automatic path mapping; user explicitly owns the adaptation to new machine.

*Control Panel:* View all defined desktops and their shortcuts. Add/remove desktops. Add/remove/edit shortcuts per desktop. Enable/disable desktops. Export current setup. Check Network Paths button (validates availability of all shortcuts). Accessible via shortcut on every desktop for quick edits.

*Startup Integration:* App runs at Windows startup (Task Scheduler or registry run key). Creates desktops and populates shortcuts in \<2 seconds. Validates shortcuts asynchronously in background (non-blocking).

*Network Path Handling:* Network shortcuts (e.g., `\\NAS\Projects`) handled gracefully. Validation doesn't block startup (3-second timeout per path). Status indicators show: Available (✅), Unavailable (⚠️), Dead (❌). User can manually revalidate via "Check Network Paths" button. Clicking an unavailable shortcut shows Windows error (expected behaviour, not app crash).

*Logging & Diagnostics:* Detailed logs saved to `AppData\Local\DesktopWorkspaces\logs\`. Safe mode: if startup crashes, next launch runs in safe mode (doesn't create desktops, opens config panel). One-click "Generate Diagnostic Report" in control panel. Reports include: Windows version, Python version, desktop list, shortcut paths, last error log.

---

**Data Model**

*Profile Structure (JSON):*

json  
{  
  "version": 1,  
  "name": "My Workspaces",  
  "desktops": \[  
    {  
      "id": "design-desktop",  
      "name": "Design",  
      "enabled": true,  
      "shortcuts": \[  
        {  
          "id": "shortcut-1",  
          "label": "Design Projects",  
          "type": "folder",  
          "path": "C:\\\\Users\\\\Bernard\\\\Projects\\\\Design",  
          "status": "available"  
        },  
        {  
          "id": "shortcut-2",  
          "label": "Photoshop",  
          "type": "app",  
          "path": "C:\\\\Program Files\\\\Adobe\\\\Photoshop\\\\Photoshop.exe",  
          "status": "available"  
        },  
        {  
          "id": "shortcut-3",  
          "label": "Team Assets",  
          "type": "folder",  
          "path": "\\\\\\\\NAS\\\\team\\\\assets",  
          "status": "unavailable"  
        }  
      \]  
    },  
    {  
      "id": "dev-desktop",  
      "name": "Development",  
      "enabled": true,  
      "shortcuts": \[...\]  
    }  
  \]  
}

*Config Structure (JSON):*

json  
{  
  "startup\_enabled": true,  
  "validate\_network\_on\_startup": true,  
  "validation\_timeout\_seconds": 3,  
  "safe\_mode\_on\_error": true,  
  "save\_new\_items\_on\_shutdown": true  
}  
---

**Architecture — Modules (v1)**

* **ConfigManager:** Load/save profiles and settings; validate JSON structure; handle config versioning  
* **VirtualDesktopManager:** Wrapper around Windows WinAPI (IVirtualDesktopManager); create, delete, switch desktops; get desktop count and IDs  
* **ShortcutManager:** Create .lnk files programmatically; place shortcuts on specific desktops; delete shortcuts; resolve shortcut targets (for status checking)  
* **ShortcutValidator:** Check if paths are reachable (async, with timeout); distinguish between "unavailable" (offline) and "dead" (doesn't exist); run in background thread on startup; expose manual revalidation  
* **DesktopChangeDetector:** On shutdown, scan desktop folder for new items; compare against last saved profile; prompt user: "Save new items to profile?"; handle user response (save, ignore, or review)  
* **StartupExecutor:** Runs on Windows startup; loads profiles, validates against system state; creates desktops in sequence (with brief pauses to avoid race conditions); places shortcuts on each desktop; starts background validation  
* **SafeMode:** If startup crashes, flag for safe mode; next launch: skip desktop creation, open control panel; user disables problematic desktops, restarts normally  
* **ControlPanel (UI):** Desktop list view with enable/disable toggles; shortcut list per desktop (add/remove/edit); status indicators (path validation results); export/import workflows; settings panel; diagnostic report generator. PyQt6 — dark aesthetic with warm metallic accents, consistent with MediaVerse

---

**UI Principles**

* Dark aesthetic with warm metallic accents (bronze `#B8956A`, consistent with MediaVerse)  
* No complexity: Straightforward workflows, no hidden features  
* Status visibility: Always show which paths are available, unavailable, or dead  
* Accessibility: All actions (add, remove, export, import) are one or two clicks  
* Minimal: Settings are sparse; most config is profile-driven

---

**Startup Pipeline**

1. Check for crashes: If previous session crashed, run in safe mode  
2. Load profiles: Read config and desktop definitions  
3. Create desktops: Use WinAPI to create/enable defined virtual desktops  
4. Place shortcuts: Create and position shortcuts on each desktop  
5. Background validation: Asynchronously validate all shortcut paths (3-sec timeout each, non-blocking)  
6. Return to user: Desktop ready in \<2 seconds, validation continues in background

---

**Shutdown Behaviour**

* Scan desktop folder: Detect new items (files, folders, shortcuts)  
* Compare to saved profile: Identify items not in current profile  
* Prompt user: "New items detected. Save them to this desktop's profile?" → Yes / No / Review  
* Clean exit: Gracefully disconnect from virtual desktop manager

---

**Path Handling & Multi-Machine Support**

*v1 (Single Machine):* Paths stored as absolute (e.g., `C:\Users\Bernard\Projects\Design`). Network paths supported as-is. No path abstraction.

*v2 (Future):* Export/import with path adjustment wizard. No automatic path mapping; user's intent is explicit. Transparent, no hidden sync logic.

---

**Testing Strategy**

*Phase 1 — Local Testing:* Core workflows, startup sequence, shutdown delta detection, OneDrive edge case, multi-monitor, clean uninstall/reinstall cycle.

*Phase 2 — Beta Testing (3–5 users):* Different Windows versions (10 and 11), different setups (OneDrive vs. local, network drives, external drives), feedback form. Duration: 2 weeks.

*Phase 3 — Public Release:* Verbose error logging, graceful degradation, safe mode, diagnostic report generation, clear documentation and troubleshooting guide.

---

**Publishing Strategy**

*Deliverables:* GitHub repository (open source, MIT license) with clean README, releases tab with .exe installer, known issues and troubleshooting sections, GitHub Issues template. NSIS or MSI installer (one-click, no dependencies, adds to Start Menu, sets up startup task). Optional GitHub Pages landing page.

*Announcement order:* r/Windows, r/productivity, r/AutoHotkey, r/devtools → niche communities → Twitter/X → ProductHunt (optional).

*Support model:* GitHub Issues; README troubleshooting; "I respond within a week, maintenance is spare-time"; logs \+ diagnostic reports \= async debugging.

---

**Commercial Model**

Launch as freeware. Free tool \= faster adoption, word-of-mouth, stronger portfolio piece. Future expansion: cloud sync subscription, profile marketplace, cross-machine sync premium feature.

---

**Development Approach**

*Workflow:* Use Claude Code with Pro account for iterative, file-level edits. Start with briefing docs to preserve context across sessions. Build module by module, test incrementally. Use `view` and `str_replace` tools for targeted edits, not full codebase regeneration.

*Tech Stack:* Python 3.10+ inside VS Code · PyQt6 · pywin32 (virtual desktops) · WinShellLink (shortcut creation) · JSON for profiles · NSIS or MSI installer.

*Estimated Timeline:* MVP 2–3 weeks · Polish 1–2 weeks · Beta testing 2 weeks · v1 Release \~6 weeks total.

---

**Known Constraints & Decisions**

* No automatic path mapping (multi-machine) — user manually adjusts paths during import  
* No OS sync of desktop contents — app manages sync via export/import, not relying on Windows or OneDrive  
* Network paths require timeout validation — 3-second timeout per path, non-blocking  
* Shortcuts-only for desktop content — avoids OneDrive conflicts, keeps solution focused  
* Safe mode for crash recovery — if startup fails, next launch opens in safe mode  
* User manages delta on shutdown — app asks, doesn't auto-save

---

**Success Criteria (v1)**

* Desktops persist across restarts  
* Shortcuts to folders and apps work reliably  
* Startup is fast (\<2 seconds to user desktop)  
* Network paths don't block startup  
* Export/import with path adjustment wizard works smoothly  
* No crashes on unknown machines (beta test)  
* Logs are detailed enough to diagnose issues  
* Users find it solves their workspace organization problem

---

**Future Directions (v2+)**

Cloud sync of profiles (OneDrive, Dropbox, or custom backend) · Profile templates / marketplace · App auto-detection (suggest shortcuts for installed apps) · Snapshot desktop window positions and restore on startup · Cross-monitor workspace layouts · Conditional shortcuts (only show if app is installed) · Scheduled desktop rotation.

---

**Questions for Claude Code Sessions**

When starting a coding session, clarify: which module(s) are we building? · What's the MVP for this module? · What are the failure modes we need to handle? · How do we test this module in isolation? · Where does error logging go?

---

*Document Version: 1.0 · Last Updated: 2026-04-30 · Author: Bernard · Status: Ready for development (Claude Code hand-off)*

