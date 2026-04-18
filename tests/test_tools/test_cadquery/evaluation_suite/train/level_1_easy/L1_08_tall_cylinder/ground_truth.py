"""Ground truth CadQuery code for L1_08: Tall Cylinder.

This creates a tall vertical cylinder with specified diameter and height.

Design decisions:
- Use cylinder() with height and radius parameters
- Diameter 25mm means radius 12.5mm
- Tall aspect ratio (height >> diameter) tests different proportions than L1_02
"""

import cadquery as cq

# Create tall cylinder: diameter 25mm (radius 12.5mm), height 100mm
result = cq.Workplane("XY").cylinder(height=100, radius=12.5)

# Expected properties:
# - Volume: π * r² * h = π * 12.5² * 100 ≈ 49,087.39 mm³
# - Faces: 3 (top, bottom, curved surface)
# - Edges: 3 (top circle, bottom circle, seam)
