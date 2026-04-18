"""Ground truth CadQuery code for L3_01: Mounting Plate with Counterbored Holes.

This creates a 120x90x12mm plate with four M8 counterbored holes, 15mm from edges.

Design decisions:
- Use cboreHole() for counterbored holes (standard for socket head cap screws)
- Plate centered at origin, holes at (±45, ±30) from center
- Counterbore: 14mm diameter, 8mm deep; through hole: 9mm diameter

Geometry:
- Plate: 120 x 90 x 12 mm (centered)
- Hole positions: 15mm inset from edges → (±45, ±30)
- Each hole: counterbore (r=7, h=8) + through section (r=4.5, h=4)

Volume: 129,600 - 4×1,485.97 = 123,656 mm³
"""

import cadquery as cq

# Create plate with four counterbored holes
result = (
    cq.Workplane("XY")
    .box(120, 90, 12)
    .faces(">Z")
    .workplane()
    .pushPoints([(-45, -30), (-45, 30), (45, -30), (45, 30)])
    .cboreHole(9, 14, 8)  # hole diameter, cbore diameter, cbore depth
)

# Expected properties:
# - Volume: ≈ 123,656.12 mm³
# - Bounding box: 120 x 90 x 12
# - Faces: 14 (6 plate + 4 counterbore floors + 4 hole cylinders)
# - Edges: 36 (complex due to counterbores)
