"""Ground truth CadQuery code for L1_02: Cylinder.

This creates a vertical cylinder with diameter 40mm and height 60mm.

Design decisions:
- Intent says "diameter 40mm" but CadQuery cylinder() takes radius
- Must convert: radius = diameter / 2 = 20mm
- Using cylinder(height, radius) for vertical orientation
"""

import cadquery as cq

# Create cylinder: height=60mm, radius=20mm (from diameter 40mm)
result = cq.Workplane("XY").cylinder(60, 20)

# Expected properties:
# - Volume: π * r² * h = π * 20² * 60 ≈ 75,398.22 mm³
# - Bounding box: 40 x 40 x 60 (diameter in X and Y)
# - Faces: 3 (top circle, bottom circle, curved surface)
# - Edges: 2 (top circle edge, bottom circle edge)
