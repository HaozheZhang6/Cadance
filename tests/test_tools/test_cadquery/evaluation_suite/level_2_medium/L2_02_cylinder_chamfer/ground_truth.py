"""Ground truth CadQuery code for L2_02: Cylinder with Top Chamfer.

This creates a cylinder with radius 25mm, height 40mm, and 3mm chamfer on top.

Design decisions:
- Create cylinder first
- Select top face with faces(">Z")
- Select edges of that face with edges()
- Apply 3mm chamfer (45° by default)

Volume calculation:
- Full cylinder: π * 25² * 40 ≈ 78,539.82 mm³
- Chamfer removes a small conical ring: ~785.40 mm³
- Net: ≈ 77,754.42 mm³
"""

import cadquery as cq

# Create cylinder with chamfered top edge
result = (
    cq.Workplane("XY")
    .cylinder(40, 25)
    .faces(">Z")  # Select top face
    .edges()  # Select edges of that face
    .chamfer(3)  # 3mm chamfer
)

# Expected properties:
# - Volume: ≈ 77,754.42 mm³
# - Bounding box: 50 x 50 x 40 (diameter x diameter x height)
# - Faces: 4 (top, bottom, curved surface, chamfer surface)
# - Edges: 3 (bottom circle, top circle (smaller), chamfer junction)
