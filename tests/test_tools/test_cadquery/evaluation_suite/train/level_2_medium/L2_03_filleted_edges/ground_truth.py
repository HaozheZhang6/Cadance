"""Ground truth CadQuery code for L2_03: Block with Filleted Vertical Edges.

This creates a 60mm cube with 8mm fillets on all vertical edges.

Design decisions:
- Create cube first with box(60, 60, 60)
- Use edges("|Z") to select only edges parallel to Z axis
- 8mm fillet on 60mm edge is safe (8 < 60/2)

Volume calculation:
- Original cube: 60³ = 216,000 mm³
- Each fillet removes: (1 - π/4) * 8² * 60 ≈ 1,034.29 mm³
- 4 fillets remove: ≈ 4,137.17 mm³
- Net: ≈ 211,862.83 mm³
"""

import cadquery as cq

# Create cube with filleted vertical edges
result = (
    cq.Workplane("XY")
    .box(60, 60, 60)
    .edges("|Z")  # Select edges parallel to Z axis (4 vertical edges)
    .fillet(8)  # 8mm fillet radius
)

# Expected properties:
# - Volume: ≈ 211,862.83 mm³
# - Bounding box: 60 x 60 x 60 (unchanged by fillets)
# - Faces: 10 (6 original - reduced by fillets + 4 fillet surfaces)
# - Edges: 20 (original 12 edges reconfigured + fillet junction edges)
