"""Ground truth CadQuery code for L3_13: Counterbore Block.

This creates a mounting block with counterbored holes at corners.

Design decisions:
- Block: 100mm x 70mm x 20mm
- 4 counterbored holes at corners, 15mm from edges
- Through hole: 9mm diameter
- Counterbore: 16mm diameter, 8mm depth
- Use cboreHole() for counterbored holes
"""

import cadquery as cq

# Calculate hole positions (15mm from edges)
# Block is 100x70, corners at ±50, ±35
# Holes at ±(50-15), ±(35-15) = ±35, ±20
hole_positions = [
    (35, 20),  # Top right
    (-35, 20),  # Top left
    (-35, -20),  # Bottom left
    (35, -20),  # Bottom right
]

# Create block with counterbored holes
result = (
    cq.Workplane("XY")
    .box(100, 70, 20)
    .faces(">Z")
    .workplane()
    .pushPoints(hole_positions)
    .cboreHole(9, 16, 8)  # 9mm through, 16mm counterbore dia, 8mm cbore depth
)

# Expected properties:
# - Volume: block - 4*(counterbore + through hole)
# - Counterbore: π*8²*8 = 1,608 mm³ each
# - Through: π*4.5²*12 = 763 mm³ each
# - Total holes: 4*(1,608 + 763) = 9,484 mm³
# - Net volume: 140,000 - 9,484 ≈ 130,516 mm³
# - Faces: 6 + 4*2 = 14 (block + counterbore + through per hole)
# - Edges: complex topology
