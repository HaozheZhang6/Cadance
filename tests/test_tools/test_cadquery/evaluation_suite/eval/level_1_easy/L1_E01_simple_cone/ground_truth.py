"""Ground truth CadQuery code for L1_E01: Simple Cone.

This creates a simple cone with specified base radius and height.

Design decisions:
- Use Solid.makeCone() for direct cone creation
- Base radius: 30mm, top radius: 0mm (pointed cone)
- Height: 50mm
- Cone apex at top, base on XY plane
"""

import cadquery as cq
from cadquery import Solid

# Create a simple cone: base radius 30mm, height 50mm
cone = Solid.makeCone(30, 0, 50)
result = cq.Workplane("XY").newObject([cone])

# Expected properties:
# - Volume: (1/3) * π * r² * h = (1/3) * π * 30² * 50 ≈ 47,123.89 mm³
# - Faces: 2 (base circle, conical surface)
# - Edges: 2 (base circle, apex point is vertex not edge)
