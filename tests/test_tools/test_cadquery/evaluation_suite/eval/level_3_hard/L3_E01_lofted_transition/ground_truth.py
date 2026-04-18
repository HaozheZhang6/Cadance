"""Ground truth CadQuery code for L3_E01: Lofted Transition.

This creates a lofted transition from a square to a circle.

Design decisions:
- Bottom profile: 40mm x 40mm square
- Top profile: 30mm diameter circle
- Loft height: 50mm
- Smooth transition between profiles
"""

import cadquery as cq

# Create square profile on bottom
square = cq.Workplane("XY").rect(40, 40)

# Create circle profile on top
circle = cq.Workplane("XY").workplane(offset=50).circle(15)

# Loft between the two profiles
result = cq.Workplane("XY").rect(40, 40).workplane(offset=50).circle(15).loft()

# Expected properties:
# - Transitions smoothly from square to circle
# - Volume is between a 40x40x50 prism and a cylinder
# - Approximate volume: ~45,000 mm³
# - Faces: 2 end caps + ruled surface
# - Complex curved surface
