"""
Manual test for StartupExecutor.
Creates real desktops — check Win+Tab during the test.
Run with: .venv/Scripts/python.exe tests/test_startup_executor.py
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import ConfigManager
from src.core.virtual_desktop_manager import VirtualDesktopManager
from src.core.startup_executor import StartupExecutor


def main():
    vdm = VirtualDesktopManager()
    before = vdm.get_desktop_count()

    # Build a temp profile with 2 enabled, 1 disabled
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = os.path.join(tmpdir, "profile.json")
        cm = ConfigManager(profile_path=profile_path)
        cm.load_profile()
        cm.add_desktop("STARTUP-A")
        cm.add_desktop("STARTUP-B")
        d3 = cm.add_desktop("STARTUP-C")
        cm.update_desktop(d3["id"], {"enabled": False})

        executor = StartupExecutor.__new__(StartupExecutor)
        executor.config = cm
        executor.vdm = vdm
        executor.run()

    assert vdm.get_desktop_count() == before + 2, "Expected 2 new desktops"
    assert vdm.find_desktop_by_name("STARTUP-A") is not None
    assert vdm.find_desktop_by_name("STARTUP-B") is not None
    assert vdm.find_desktop_by_name("STARTUP-C") is None
    print("PASS: StartupExecutor created 2 enabled desktops, skipped disabled")

    # Cleanup
    vdm.delete_desktop("STARTUP-A")
    vdm.delete_desktop("STARTUP-B")
    assert vdm.get_desktop_count() == before
    print("PASS: cleanup complete")

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
