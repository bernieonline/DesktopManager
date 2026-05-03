# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Desktop Workspaces
#
# Produces two executables in a single dist folder:
#   DesktopWorkspaces.exe         — shop window (normal launch)
#   DesktopWorkspacesStartup.exe  — startup sequence (registered with Windows)
#
# Build command (run from project root):
#   .venv\Scripts\pyinstaller.exe installer\DesktopWorkspaces.spec

import os
from PyInstaller.utils.hooks import collect_all

# Resolve paths relative to this spec file
SPEC_DIR    = os.path.dirname(os.path.abspath(SPEC))   # installer\
PROJECT_DIR = os.path.dirname(SPEC_DIR)                 # project root

# comtypes generates COM interface code dynamically — collect everything
# so the generated typelibs are available at runtime
comtypes_datas, comtypes_binaries, comtypes_hiddenimports = collect_all("comtypes")

HIDDEN_IMPORTS = [
    # pywin32
    "win32api",
    "win32con",
    "win32gui",
    "win32com",
    "win32com.shell",
    "win32com.shell.shell",
    "pywintypes",
    # comtypes (dynamic COM dispatch)
    *comtypes_hiddenimports,
    # pyvda — virtual desktop COM wrapper
    "pyvda",
    # jsonschema (used by schema.py)
    "jsonschema",
    "jsonschema.validators",
    "jsonschema._format_validators",
]

# ── Shop window ──────────────────────────────────────────────────────────────

a_shop = Analysis(
    [os.path.join(PROJECT_DIR, "main.py")],
    pathex=[PROJECT_DIR],
    binaries=comtypes_binaries,
    datas=comtypes_datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz_shop = PYZ(a_shop.pure)

exe_shop = EXE(
    pyz_shop,
    a_shop.scripts,
    [],
    exclude_binaries=True,          # binaries go into COLLECT below
    name="DesktopWorkspaces",
    debug=False,
    strip=False,
    upx=False,                      # UPX can break pywin32 DLLs — leave off
    console=False,                  # no console window (equivalent to pythonw)
    icon=None,                      # add an .ico path here when you have one
)

# ── Startup executor ─────────────────────────────────────────────────────────

a_startup = Analysis(
    [os.path.join(PROJECT_DIR, "main_startup.py")],
    pathex=[PROJECT_DIR],
    binaries=comtypes_binaries,
    datas=comtypes_datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz_startup = PYZ(a_startup.pure)

exe_startup = EXE(
    pyz_startup,
    a_startup.scripts,
    [],
    exclude_binaries=True,
    name="DesktopWorkspacesStartup",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

# ── Single output folder (shared DLLs, both exes) ───────────────────────────

coll = COLLECT(
    exe_shop,
    a_shop.binaries,
    a_shop.datas,
    exe_startup,
    a_startup.binaries,
    a_startup.datas,
    strip=False,
    upx=False,
    name="DesktopWorkspaces",       # → dist\DesktopWorkspaces\
)
