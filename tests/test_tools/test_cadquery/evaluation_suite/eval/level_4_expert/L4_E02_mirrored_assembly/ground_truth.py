"""Ground truth CadQuery code for L4_E02: Mirrored Assembly.

This creates a complex bracket with holes, then mirrors it for symmetry.

Design decisions:
- Base L-bracket with mounting holes
- Fillet on inner corner
- Mirror about center plane to create symmetric mount
- Total width after mirroring: 120mm
"""

import cadquery as cq

# Create half of the bracket
half_bracket = (
    cq.Workplane("XY")
    # L-shaped profile
    .moveTo(0, 0)
    .lineTo(60, 0)
    .lineTo(60, 10)
    .lineTo(10, 10)
    .lineTo(10, 50)
    .lineTo(0, 50)
    .close()
    .extrude(25)
    # Add mounting hole on horizontal leg
    .faces(">Z")
    .workplane()
    .center(35, 5)
    .hole(8)
    # Add mounting hole on vertical leg
    .faces(">Z")
    .workplane()
    .center(5, 30)
    .hole(8)
    # Fillet the inner corner
    .edges("|Z")
    .edges(cq.selectors.NearestToPointSelector((10, 10, 12.5)))
    .fillet(5)
)

# Mirror about YZ plane to create full symmetric bracket
result = half_bracket.mirror(mirrorPlane="YZ", basePointVector=(0, 0, 0), union=True)

# Expected properties:
# - Symmetric L-bracket assembly
# - 4 mounting holes total (2 on each side)
# - Filleted corners
# - Complex face and edge count
