"""Ground truth CadQuery code for L1_05: L-Shape Extrusion.

This creates an L-shaped profile extruded 40mm.
- Vertical leg: 60mm tall, 15mm wide
- Horizontal leg: 50mm wide, 15mm tall
- Legs meet at inside corner

Design decisions:
- Using polyline/lineTo to define the L-shape profile
- Starting at origin, drawing counterclockwise
- Profile drawn in XZ plane, extruded in Y direction for clarity
- Could also be constructed as union of two boxes

Profile coordinates (in XZ plane):
  (0,0) -> (50,0) -> (50,15) -> (15,15) -> (15,60) -> (0,60) -> close

Cross-sectional area:
  - Full rectangle: 50 * 60 = 3000
  - Minus cutout: 35 * 45 = 1575
  - L-area = 3000 - 1575 = 1425 mm²
  - Or: (60*15) + (35*15) = 900 + 525 = 1425 mm²

Volume = 1425 * 40 = 57,000 mm³
"""

import cadquery as cq

# Create L-shaped profile in XZ plane
result = (
    cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(50, 0)  # Bottom of horizontal leg
    .lineTo(50, 15)  # Right side of horizontal leg
    .lineTo(15, 15)  # Inside corner
    .lineTo(15, 60)  # Left side of vertical leg
    .lineTo(0, 60)  # Top of vertical leg
    .close()  # Back to start
    .extrude(40)  # Extrude in Y direction
)

# Expected properties:
# - Volume: 1425 * 40 = 57,000 mm³
# - Bounding box: 50 x 40 x 60
# - Faces: 8 (top, bottom, 6 sides of L-shape)
# - Edges: 18 (6 on top, 6 on bottom, 6 vertical)
