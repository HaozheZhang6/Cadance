"""Ground truth CadQuery code for L2_05: Hollow Box (Shelled).

This creates an 80x60x50mm box, shelled with 3mm walls, top open.

Design decisions:
- Create solid box first, then shell inward
- Select top face with faces(">Z") - this face becomes the opening
- shell(-3) makes walls 3mm thick by hollowing inward

Geometry:
- Outer: 80 x 60 x 50 mm
- Inner cavity: 74 x 54 x 47 mm (3mm walls on sides, 3mm bottom)
- Top is open (selected face removed during shell)

Volume: 240,000 - 187,812 = 52,188 mm³
"""

import cadquery as cq

# Create hollow box with 3mm walls, top open
# NOTE: .solids() extracts the Solid from the Compound returned by shell
result = (
    cq.Workplane("XY")
    .box(80, 60, 50)
    .faces(">Z")  # Select top face (will be removed)
    .shell(-3)  # Shell inward with 3mm wall thickness
    .solids()  # Extract solid from compound for .val() to work correctly
)

# Expected properties:
# - Volume: 240,000 - 187,812 = 52,188 mm³
# - Bounding box: 80 x 60 x 50 (outer dimensions unchanged)
# - Faces: 10 (5 outer + 5 inner walls/bottom, top is open)
# - Edges: 24 (12 outer + 12 inner at opening rim)
