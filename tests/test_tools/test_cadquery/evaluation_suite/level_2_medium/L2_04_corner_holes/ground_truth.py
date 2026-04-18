"""Ground truth CadQuery code for L2_04: Plate with Four Corner Holes.

This creates a 100x80x10mm plate with four 6mm holes, 10mm from each edge.

Design decisions:
- Create plate with box()
- Calculate hole positions: plate is centered, so corners are at (±50, ±40)
- 10mm inset means holes at (±40, ±30)
- Use pushPoints() to define all 4 hole locations at once

Position calculation:
- Plate width 100mm, centered: x ranges from -50 to +50
- 10mm from edge: x = -50+10 = -40 and +50-10 = +40
- Plate depth 80mm, centered: y ranges from -40 to +40
- 10mm from edge: y = -40+10 = -30 and +40-10 = +30
- Holes at: (-40, -30), (-40, +30), (+40, -30), (+40, +30)

Volume calculation:
- Plate: 100 * 80 * 10 = 80,000 mm³
- 4 holes: 4 * π * 3² * 10 ≈ 1,130.97 mm³
- Net: ≈ 78,869.02 mm³
"""

import cadquery as cq

# Create plate with four corner holes
result = (
    cq.Workplane("XY")
    .box(100, 80, 10)
    .faces(">Z")
    .workplane()
    .pushPoints([(-40, -30), (-40, 30), (40, -30), (40, 30)])
    .hole(6)  # 6mm diameter through holes
)

# Expected properties:
# - Volume: ≈ 78,869.02 mm³
# - Bounding box: 100 x 80 x 10
# - Faces: 10 (6 plate + 4 hole cylinders)
# - Edges: 24 (12 plate + 8 hole circles + 4 top/bottom intersections)
