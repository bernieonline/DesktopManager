; Desktop Workspaces — NSIS Installer Script
;
; Prerequisites:
;   • NSIS 3.x installed (https://nsis.sourceforge.io)
;   • PyInstaller build complete: dist\DesktopWorkspaces\ must exist
;
; Build command (run from project root):
;   "C:\Program Files (x86)\NSIS\makensis.exe" installer\DesktopWorkspaces.nsi
;
; Output: dist\DesktopWorkspaces_Setup.exe
; No admin rights required — installs to %LOCALAPPDATA%\Programs\

Unicode True

; ── Metadata ─────────────────────────────────────────────────────────────────

!define APP_NAME        "Desktop Workspaces"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Bernard"
!define APP_EXE         "DesktopWorkspaces.exe"
!define STARTUP_EXE     "DesktopWorkspacesStartup.exe"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\DesktopWorkspaces"
!define RUN_KEY         "Software\Microsoft\Windows\CurrentVersion\Run"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\dist\DesktopWorkspaces_Setup.exe"

; Per-user install — no UAC prompt needed
InstallDir "$LOCALAPPDATA\Programs\DesktopWorkspaces"
RequestExecutionLevel user

; ── Pages ────────────────────────────────────────────────────────────────────

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

; ── Install ──────────────────────────────────────────────────────────────────

Section "Desktop Workspaces" SecMain

  SetOutPath "$INSTDIR"

  ; Copy the entire PyInstaller output folder
  File /r "..\dist\DesktopWorkspaces\*.*"

  ; Start Menu shortcut (per-user)
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                  "$INSTDIR\${APP_EXE}"
  CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                  "$INSTDIR\Uninstall.exe"

  ; Register startup — runs DesktopWorkspacesStartup.exe at Windows logon
  WriteRegStr HKCU "${RUN_KEY}" "${APP_NAME}" '"$INSTDIR\${STARTUP_EXE}"'

  ; Uninstall registry entry (per-user, no admin required)
  WriteRegStr   HKCU "${UNINSTALL_KEY}" "DisplayName"          "${APP_NAME}"
  WriteRegStr   HKCU "${UNINSTALL_KEY}" "DisplayVersion"       "${APP_VERSION}"
  WriteRegStr   HKCU "${UNINSTALL_KEY}" "Publisher"            "${APP_PUBLISHER}"
  WriteRegStr   HKCU "${UNINSTALL_KEY}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKCU "${UNINSTALL_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify"             1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair"             1

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Launch the shop window immediately so the user sees it right away
  Exec '"$INSTDIR\${APP_EXE}"'

SectionEnd

; ── Uninstall ────────────────────────────────────────────────────────────────

Section "Uninstall"

  ; Remove startup registration
  DeleteRegValue HKCU "${RUN_KEY}" "${APP_NAME}"

  ; Remove Start Menu
  RMDir /r "$SMPROGRAMS\${APP_NAME}"

  ; Remove install folder
  RMDir /r "$INSTDIR"

  ; Remove uninstall entry
  DeleteRegKey HKCU "${UNINSTALL_KEY}"

SectionEnd
