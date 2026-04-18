"""Ground truth CadQuery code for L2_09: Box with Corner Holes.

This creates a rectangular block with holes near each corner.

Design decisions:
- Block: 100mm x 80mm x 15mm
- Holes: 8mm diameter at 10mm from each edge
- Use pushPoints to position holes at corner locations
- Hole centers at: (±40, ±30) relative to center
"""

import cadquery as cq

# Calculate hole positions (10mm from edges)
# Block is 100x80, so corners relative to center are at ±50, ±40
# Holes 10mm from edge: ±(50-10), ±(40-10) = ±40, ±30
hole_positions = [
    (40, 30),  # Top right
    (-40, 30),  # Top left
    (-40, -30),  # Bottom left
    (40, -30),  # Bottom right
]

# Create block with corner holes
result = (
    cq.Workplane("XY")
    .box(100, 80, 15)
    .faces(">Z")
    .workplane()
    .pushPoints(hole_positions)
    .hole(8)  # 8mm diameter through holes
)

# Expected properties:
# - Volume: 100*80*15 - 4*π*4²*15 ≈ 120,000 - 3,016 ≈ 116,984 mm³
# - Faces: 6 + 4 = 10 (box faces + 4 cylindrical hole surfaces)
# - Edges: 12 + 8 = 20 (box edges + 8 circles from holes)
