"""
Check what properties pyvda VirtualDesktop exposes.
Run with: .venv/Scripts/python.exe tests/spike_vd_properties.py
"""
from pyvda import VirtualDesktop, get_virtual_desktops

d = get_virtual_desktops()[0]
print("Attributes:", [a for a in dir(d) if not a.startswith("_")])

current = VirtualDesktop.current()
print("\nCurrent desktop id:", current.id if hasattr(current, "id") else "no .id")
print("Current desktop name:", current.name if hasattr(current, "name") else "no .name")
print("Current desktop number:", current.number if hasattr(current, "number") else "no .number")
