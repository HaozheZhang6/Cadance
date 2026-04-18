"""Ground truth CadQuery code for L2_E02: Mirrored Bracket.

This creates an L-bracket and mirrors it to create a symmetric U-bracket.

Design decisions:
- Start with an L-shaped profile
- Base: 30mm x 10mm, vertical leg: 10mm x 40mm
- Depth (extrusion): 20mm
- Mirror about the YZ plane to create symmetric bracket
"""

import cadquery as cq

# Create L-bracket profile and extrude, then mirror
half_bracket = (
    cq.Workplane("XY")
    .moveTo(0, 0)
    .lineTo(30, 0)
    .lineTo(30, 10)
    .lineTo(10, 10)
    .lineTo(10, 40)
    .lineTo(0, 40)
    .close()
    .extrude(20)
)

# Mirror about YZ plane (X=0)
result = half_bracket.mirror(mirrorPlane="YZ", basePointVector=(0, 0, 0), union=True)

# Expected properties:
# - Half bracket area: 30*10 + 10*30 = 600 mm²
# - Half bracket volume: 600 * 20 = 12,000 mm³
# - Total volume: 12,000 * 2 = 24,000 mm³ (but overlapping center reduces this)
# - Actual: (30*10 + 10*30) * 2 - 10*10 = 1100 mm² * 20 = 22,000 mm³
