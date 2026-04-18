"""Ground truth CadQuery code for L4_E03: Drafted Enclosure.

This creates a hollow box (enclosure) with draft angles for moldability.

Design decisions:
- Outer dimensions: 80mm x 60mm base, 40mm height
- Wall thickness: 3mm
- Draft angle: 3 degrees on all walls
- Open top (shell operation)
"""

import cadquery as cq

# Create outer drafted box
outer = cq.Workplane("XY").rect(80, 60).extrude(40, taper=3)  # 3-degree draft

# Shell to create hollow interior (remove top face)
result = outer.faces(">Z").shell(-3)  # 3mm wall thickness, inward

# Expected properties:
# - Hollow box with tapered walls
# - Open top
# - Wall thickness: 3mm
# - Draft angle visible on all 4 sides
# - Faces: 5 outer walls + 4 inner walls + bottom inner = 10
