"""Ground truth CadQuery code for L2_E01: Countersunk Holes.

This creates a plate with countersunk holes for flat-head screws.

Design decisions:
- Base plate: 80mm x 50mm x 12mm
- Two countersunk holes, M6 (6mm diameter), 90-degree countersink
- Holes positioned at ±25mm from center along X axis
- Countersink diameter: 12mm (standard for M6)
"""

import cadquery as cq

# Create plate with countersunk holes
result = (
    cq.Workplane("XY")
    .box(80, 50, 12)
    .faces(">Z")
    .workplane()
    .pushPoints([(-25, 0), (25, 0)])
    .cskHole(6, 12, 82)  # 6mm hole, 12mm countersink dia, 82° angle (standard)
)

# Expected properties:
# - Base volume: 80 * 50 * 12 = 48,000 mm³
# - Minus hole and countersink volumes
# - Faces: 6 box faces + countersink surfaces
# - Edges: Multiple due to countersinks
