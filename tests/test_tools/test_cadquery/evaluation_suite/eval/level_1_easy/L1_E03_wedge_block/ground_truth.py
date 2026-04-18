"""Ground truth CadQuery code for L1_E03: Wedge Block.

This creates a wedge (triangular prism) shape.

Design decisions:
- Use Solid.makeWedge() for direct wedge creation
- Base dimensions: 60mm x 40mm
- Height: 30mm
- Wedge tapers to a line at top (xmax at top = 0)
"""

import cadquery as cq
from cadquery import Solid

# Create a wedge: dx=60, dy=40, dz=30
# makeWedge(dx, dy, dz, xmin, zmin, xmax, zmax)
# For a simple wedge tapering to top edge: xmin=0, zmin=0, xmax=0, zmax=dz
wedge = Solid.makeWedge(60, 40, 30, 0, 0, 0, 30)
result = cq.Workplane("XY").newObject([wedge])

# Expected properties:
# - Volume: (1/2) * base_area * height = (1/2) * 60 * 40 * 30 = 36,000 mm³
# - Faces: 5 (bottom rect, 2 triangular ends, 2 sloped sides)
# - Edges: 9 (4 bottom, 1 top, 4 vertical/sloped)
