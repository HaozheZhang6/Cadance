"""Ground truth CadQuery code for L1_01: Simple Box.

This creates a rectangular box 100mm x 50mm x 30mm.

Design decisions:
- Using box() is the most direct approach for rectangular prisms
- Parameters are (length, width, height) which map to (X, Y, Z)
- Box is centered on the workplane origin by default
"""

import cadquery as cq

# Create a simple box: 100mm wide (X), 50mm deep (Y), 30mm tall (Z)
result = cq.Workplane("XY").box(100, 50, 30)

# Expected properties:
# - Volume: 100 * 50 * 30 = 150,000 mm³
# - Bounding box: 100 x 50 x 30
# - Faces: 6 (top, bottom, front, back, left, right)
# - Edges: 12 (4 on top, 4 on bottom, 4 vertical)
