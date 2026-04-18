"""Ground truth CadQuery code for L3_E02: Revolved Cut.

This creates a cylinder with a revolved groove cut into it.

Design decisions:
- Base cylinder: 50mm diameter, 40mm height
- V-groove cut around the circumference at mid-height
- Groove profile: triangular, 5mm deep, 8mm wide
- Groove created by revolving a triangular profile
"""

import cadquery as cq

# Create base cylinder
base = cq.Workplane("XY").circle(25).extrude(40)

# Create the groove cut profile and revolve
# Profile is a triangle on the outer surface
groove = (
    cq.Workplane("XZ")
    .moveTo(25, 20)  # Start at outer surface, mid-height
    .lineTo(20, 24)  # Go inward and up (5mm in, 4mm up)
    .lineTo(20, 16)  # Go down (4mm down from start)
    .close()
    .revolve(360, (0, 0, 0), (0, 0, 1))
)

# Cut the groove from the cylinder
result = base.cut(groove)

# Expected properties:
# - Base volume: π * 25² * 40 ≈ 78,539.82 mm³
# - Minus groove volume
# - Faces: 3 cylinder faces + groove surfaces
# - Edges: Multiple including groove edges
