"""Ground truth CadQuery code for L1_03: Extruded Rectangle.

This creates a rectangular profile 80mm x 40mm extruded 25mm.

Design decisions:
- Using rect() to create 2D sketch, then extrude() for 3D
- This is the sketch+extrude pattern fundamental to parametric CAD
- Alternative: box(80, 40, 25) would produce identical geometry
- Intent explicitly mentions "extrude" so we use that approach
"""

import cadquery as cq

# Create rectangular sketch and extrude
result = cq.Workplane("XY").rect(80, 40).extrude(25)

# Expected properties:
# - Volume: 80 * 40 * 25 = 80,000 mm³
# - Bounding box: 80 x 40 x 25
# - Faces: 6 (same as box)
# - Edges: 12 (same as box)
