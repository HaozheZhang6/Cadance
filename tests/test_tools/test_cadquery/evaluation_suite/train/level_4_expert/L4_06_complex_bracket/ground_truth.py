"""Ground truth CadQuery code for L4_06: Complex L-Bracket with Holes.

This creates an L-bracket with mounting holes on both faces.

Design decisions:
- Vertical plate: 80mm (Z) x 60mm (X) x 8mm (Y thick)
- Horizontal plate: 50mm (Y) x 60mm (X) x 8mm (Z thick)
- Vertical holes: 2x 10mm dia, 15mm from top, 15mm from sides
- Horizontal holes: 2x 8mm dia, 15mm from outer edge, 15mm from sides
"""

import cadquery as cq

# Create L-bracket base shape
# Horizontal plate at bottom
horizontal = cq.Workplane("XY").box(60, 50, 8)

# Vertical plate
# Position at back of horizontal plate
vertical = (
    cq.Workplane("XY")
    .workplane(offset=8)  # Above horizontal
    .transformed(offset=(0, -21, 0))  # Shift to back edge (50/2 - 8/2 - adjust)
    .box(60, 8, 80)
)

# Union plates
bracket = horizontal.union(vertical)

# Add holes on vertical plate (back face, YZ plane)
# Holes at 15mm from top (80-15=65mm from base), 15mm from sides
vert_hole_positions = [
    (15, 65 + 8),  # Left hole (from center X, height from XY plane)
    (-15, 65 + 8),  # Right hole
]

# Holes need to be drilled through the vertical plate
result = (
    bracket.faces(">Y")  # Select back vertical face
    .workplane()
    .pushPoints([(15, 80 - 15), (-15, 80 - 15)])  # 15mm from sides, 15mm from top
    .hole(10)  # 10mm diameter through holes
    .faces("<Z")  # Select bottom horizontal face
    .workplane()
    .pushPoints(
        [(15, -50 / 2 + 15), (-15, -50 / 2 + 15)]
    )  # 15mm from sides, 15mm from outer
    .hole(8)  # 8mm diameter through holes
)

# Expected properties:
# - Volume: bracket volume - 4 hole volumes
# - Vertical: 60*8*80 = 38,400 mm³
# - Horizontal: 60*50*8 = 24,000 mm³ (overlap with vertical)
# - Holes: 2*π*5²*8 + 2*π*4²*8 ≈ 1,257 + 804 = 2,061 mm³
