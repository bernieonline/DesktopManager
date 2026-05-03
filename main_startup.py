"""
Entry point for DesktopWorkspacesStartup.exe (PyInstaller bundle).

Runs the startup sequence: syncs virtual desktops, places the Control Panel
shortcut, and launches DesktopWorkspaces.exe as a detached process.
"""
from src.core.startup_executor import StartupExecutor

StartupExecutor().run()
