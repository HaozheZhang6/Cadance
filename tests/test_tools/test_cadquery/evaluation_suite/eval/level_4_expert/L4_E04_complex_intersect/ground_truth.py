"""Ground truth CadQuery code for L4_E04: Complex Intersect.

This creates the intersection of a cylinder and a cone.

Design decisions:
- Vertical cylinder: 40mm diameter, 60mm height, centered
- Cone: 60mm base diameter, 80mm height, apex pointing up
- Both centered at origin
- Result is a complex curved shape
"""

import cadquery as cq
from cadquery import Solid

# Create cylinder
cylinder = (
    cq.Workplane("XY")
    .circle(20)  # 40mm diameter
    .extrude(60)
    .translate((0, 0, -30))  # Center vertically
)

# Create cone
cone_solid = Solid.makeCone(30, 0, 80)  # Base radius 30, top 0, height 80
cone = cq.Workplane("XY").newObject([cone_solid])
cone = cone.translate((0, 0, -20))  # Position so it overlaps cylinder

# Intersect cylinder and cone
result = cylinder.intersect(cone)

# Expected properties:
# - Complex curved intersection surface
# - Shape varies with cylinder/cone proportions
# - Creates a "bullet" or "nose cone" like shape
