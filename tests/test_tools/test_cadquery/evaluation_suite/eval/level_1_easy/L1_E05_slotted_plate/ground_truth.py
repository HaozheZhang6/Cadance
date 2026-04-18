"""Ground truth CadQuery code for L1_E05: Slotted Plate.

This creates a simple plate with a slot shape extruded (stadium/discorectangle).

Design decisions:
- Use slot2D() to create a slot (rectangle with semicircular ends)
- Slot dimensions: 60mm long x 20mm wide
- Extrude height: 10mm
- Creates a stadium-shaped prism
"""

import cadquery as cq

# Create slotted plate: 60mm x 20mm slot, 10mm height
result = (
    cq.Workplane("XY")
    .slot2D(60, 20)  # 60mm length, 20mm width (stadium shape)
    .extrude(10)
)

# Expected properties:
# - Slot area: rectangle + 2 semicircles = (60-20)*20 + π*10² ≈ 800 + 314.16 ≈ 1,114.16 mm²
# - Volume: 1,114.16 * 10 ≈ 11,141.59 mm³
# - Faces: 3 (top, bottom, curved side)
# - Edges: 2 (top and bottom slot curves)
