"""Ground truth CadQuery code for L4_E05: Multi-Primitive Assembly.

This creates a decorative shape combining a wedge base with a torus ring.

Design decisions:
- Wedge base: 60mm x 40mm, 25mm height
- Torus ring sitting on top: major radius 15mm, minor radius 5mm
- Torus centered on top of wedge
- Union of both shapes
"""

import cadquery as cq
from cadquery import Solid

# Create wedge base
wedge_solid = Solid.makeWedge(60, 40, 25, 0, 0, 30, 25)
wedge = cq.Workplane("XY").newObject([wedge_solid])
# Center the wedge
wedge = wedge.translate((-30, -20, 0))

# Create torus on top
# Torus sits at height where wedge has width ~30mm
torus_solid = Solid.makeTorus(15, 5)
torus = cq.Workplane("XY").newObject([torus_solid])
# Position torus on top of wedge (at height ~15mm where there's flat surface)
torus = torus.translate((0, 0, 15))

# Union the shapes
result = wedge.union(torus)

# Expected properties:
# - Complex combined shape
# - Wedge volume + torus volume
# - Interesting silhouette from different angles
