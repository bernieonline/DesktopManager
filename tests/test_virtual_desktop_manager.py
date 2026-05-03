"""
Manual test for VirtualDesktopManager.
Creates and removes a test desktop — check Task View (Win+Tab) during the test.
Run with: .venv/Scripts/python.exe tests/test_virtual_desktop_manager.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.virtual_desktop_manager import VirtualDesktopManager

def main():
    vdm = VirtualDesktopManager()

    before = vdm.get_desktop_count()
    print(f"Desktops before: {before}")

    # Create
    d = vdm.create_desktop("TEST-WORKSPACE")
    assert d is not None, "Failed to create desktop"
    print(f"PASS: created 'TEST-WORKSPACE' (number={d.number})")

    # Find by name
    found = vdm.find_desktop_by_name("TEST-WORKSPACE")
    assert found is not None, "Could not find desktop by name"
    print(f"PASS: find_desktop_by_name → number={found.number}, name='{found.name}'")

    # Idempotent create
    d2 = vdm.create_desktop("TEST-WORKSPACE")
    assert vdm.get_desktop_count() == before + 1, "Idempotent create failed"
    print("PASS: duplicate create is idempotent")

    # Rename
    ok = vdm.rename_desktop("TEST-WORKSPACE", "TEST-RENAMED")
    assert ok
    assert vdm.find_desktop_by_name("TEST-RENAMED") is not None
    assert vdm.find_desktop_by_name("TEST-WORKSPACE") is None
    print("PASS: rename_desktop")

    # Delete
    ok = vdm.delete_desktop("TEST-RENAMED")
    assert ok
    assert vdm.get_desktop_count() == before
    print("PASS: delete_desktop")

    # sync_desktops
    profile_desktops = [
        {"name": "SYNC-A", "enabled": True},
        {"name": "SYNC-B", "enabled": True},
        {"name": "SYNC-C", "enabled": False},
    ]
    result = vdm.sync_desktops(profile_desktops)
    assert len(result) == 2
    assert "SYNC-A" in result
    assert "SYNC-B" in result
    assert "SYNC-C" not in result
    print(f"PASS: sync_desktops created {len(result)} enabled desktops, skipped disabled")

    # Cleanup
    vdm.delete_desktop("SYNC-A")
    vdm.delete_desktop("SYNC-B")
    assert vdm.get_desktop_count() == before
    print("PASS: cleanup complete")

    print("\nAll tests passed.")

if __name__ == "__main__":
    main()
