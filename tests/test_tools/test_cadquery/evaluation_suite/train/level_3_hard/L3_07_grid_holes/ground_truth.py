"""Ground truth CadQuery code for L3_07: Plate with Grid of Holes.

This creates a plate with a rectangular array of holes.

Design decisions:
- Plate: 120mm x 100mm x 10mm
- Grid: 3 columns x 4 rows of 6mm diameter holes
- First hole 15mm from edges
- Spacing: (120-30)/(3-1) = 45mm in X, (100-30)/(4-1) = 23.33mm in Y
"""

import cadquery as cq

# Calculate grid spacing
# Available space: 120 - 2*15 = 90mm in X, 100 - 2*15 = 70mm in Y
# Spacing: 90/2 = 45mm in X (3 columns), 70/3 ≈ 23.33mm in Y (4 rows)
x_spacing = 45
y_spacing = 70 / 3  # ≈ 23.33mm

# Create plate with grid of holes
result = (
    cq.Workplane("XY")
    .box(120, 100, 10)
    .faces(">Z")
    .workplane()
    .rarray(x_spacing, y_spacing, 3, 4)  # 3 columns, 4 rows
    .hole(6)  # 6mm diameter holes
)

# Expected properties:
# - Volume: 120*100*10 - 12*π*3²*10 ≈ 120,000 - 3,393 ≈ 116,607 mm³
# - Faces: 6 + 12 = 18 (plate faces + 12 hole surfaces)
# - Edges: 12 + 24 = 36 (plate edges + 24 hole circles)
