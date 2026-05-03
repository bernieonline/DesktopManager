"""
Spike: test pyvda set_wallpaper on the current desktop.
Run with: .venv/Scripts/python.exe tests/spike_wallpaper.py "C:\path\to\image.jpg"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyvda import VirtualDesktop

if len(sys.argv) < 2:
    print("Usage: spike_wallpaper.py <path_to_image>")
    sys.exit(1)

path = os.path.normpath(os.path.abspath(sys.argv[1]))
print(f"Image path: {path}")
print(f"File exists: {os.path.isfile(path)}")

current = VirtualDesktop.current()
print(f"Current desktop: number={current.number}, name='{current.name}'")

try:
    current.set_wallpaper(path)
    print("set_wallpaper() called — check if your wallpaper changed.")
except Exception as e:
    print(f"ERROR: {e}")
