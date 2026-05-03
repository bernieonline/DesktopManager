"""
Quick manual test for ConfigManager.
Run with: .venv/Scripts/python.exe tests/test_config_manager.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import ConfigManager

def test_config_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = os.path.join(tmpdir, "profile.json")
        cm = ConfigManager(profile_path=profile_path)

        # Load creates empty profile
        profile = cm.load_profile()
        assert profile["version"] == 1
        assert profile["desktops"] == []
        print("PASS: load creates empty profile")

        # Add desktop
        d1 = cm.add_desktop("CCLUB")
        assert d1["name"] == "CCLUB"
        assert d1["enabled"] is True
        assert d1["background_path"] is None
        print(f"PASS: add_desktop → id={d1['id']}")

        d2 = cm.add_desktop("Development")
        print(f"PASS: add second desktop → id={d2['id']}")

        # get_all_desktops
        all_desktops = cm.get_all_desktops()
        assert len(all_desktops) == 2
        print(f"PASS: get_all_desktops → {len(all_desktops)} desktops")

        # get_desktop_by_id
        found = cm.get_desktop_by_id(d1["id"])
        assert found["name"] == "CCLUB"
        print("PASS: get_desktop_by_id")

        # update_desktop
        cm.update_desktop(d1["id"], {"enabled": False, "background_path": "C:\\test.png"})
        updated = cm.get_desktop_by_id(d1["id"])
        assert updated["enabled"] is False
        assert updated["background_path"] == "C:\\test.png"
        print("PASS: update_desktop")

        # get_enabled_desktops
        enabled = cm.get_enabled_desktops()
        assert len(enabled) == 1
        assert enabled[0]["name"] == "Development"
        print("PASS: get_enabled_desktops filters correctly")

        # delete_desktop
        cm.delete_desktop(d1["id"])
        assert cm.get_desktop_by_id(d1["id"]) is None
        assert len(cm.get_all_desktops()) == 1
        print("PASS: delete_desktop")

        # Reload from disk
        cm2 = ConfigManager(profile_path=profile_path)
        reloaded = cm2.load_profile()
        assert len(reloaded["desktops"]) == 1
        assert reloaded["desktops"][0]["name"] == "Development"
        print("PASS: profile persists and reloads correctly")

    print("\nAll tests passed.")

if __name__ == "__main__":
    test_config_manager()
