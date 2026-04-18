"""Ground truth CadQuery code for L2_12: Double Chamfer Box.

This creates a box with chamfered edges on top and bottom.

Design decisions:
- Box: 70mm x 50mm x 40mm
- Chamfer: 4mm on top and bottom horizontal edges
- Use edges("|Z") to select all vertical edges (wrong approach)
- Actually use edges(">Z") and edges("<Z") separately for top and bottom
"""

import cadquery as cq

# Create box with chamfers on top and bottom edges
result = (
    cq.Workplane("XY")
    .box(70, 50, 40)
    .edges(">Z")  # Select top face edges
    .chamfer(4)
    .edges("<Z")  # Select bottom face edges
    .chamfer(4)
)

# Expected properties:
# - Volume: box volume minus chamfer volumes ≈ 140,000 - chamfers
# - Faces: 6 original + 8 chamfer faces = 14
# - Edges: complex due to chamfer transitions
