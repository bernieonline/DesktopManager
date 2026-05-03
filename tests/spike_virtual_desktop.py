"""
Spike test for pyvda on Windows 11 24H2 (build 26200).
Tests: list desktops, create, delete. Does NOT switch desktops.
Run with: .venv/Scripts/python.exe tests/spike_virtual_desktop.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pyvda
    print(f"pyvda version: {pyvda.__version__}")
except AttributeError:
    print("pyvda imported (no __version__)")

from pyvda import VirtualDesktop, get_virtual_desktops

def main():
    # 1. List current desktops
    desktops = get_virtual_desktops()
    print(f"\nCurrent desktops: {len(desktops)}")
    for i, d in enumerate(desktops):
        marker = " <-- current" if d == VirtualDesktop.current() else ""
        print(f"  [{i}] {d}{marker}")

    # 2. Create a test desktop
    print("\nCreating test desktop...")
    new_desktop = VirtualDesktop.create()
    print(f"Created: {new_desktop}")

    desktops_after = get_virtual_desktops()
    print(f"Desktops after create: {len(desktops_after)}")

    # 3. Remove the test desktop
    print("\nRemoving test desktop...")
    new_desktop.remove()

    desktops_final = get_virtual_desktops()
    print(f"Desktops after remove: {len(desktops_final)}")

    print("\nSpike complete — pyvda is working.")

if __name__ == "__main__":
    main()
