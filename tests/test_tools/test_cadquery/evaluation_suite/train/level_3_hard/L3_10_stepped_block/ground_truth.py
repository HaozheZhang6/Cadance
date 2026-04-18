"""Ground truth CadQuery code for L3_10: Stepped Block.

This creates a stepped pyramid-like structure with three levels.

Design decisions:
- Bottom: 80mm x 80mm x 20mm
- Middle: 60mm x 60mm x 20mm, centered on bottom
- Top: 40mm x 40mm x 20mm, centered on middle
- Build by stacking centered boxes
"""

import cadquery as cq

# Create stepped block by stacking centered boxes
bottom = cq.Workplane("XY").box(80, 80, 20)

middle = cq.Workplane("XY").workplane(offset=20).box(60, 60, 20)  # At top of bottom

top = cq.Workplane("XY").workplane(offset=40).box(40, 40, 20)  # At top of middle

# Union all levels
result = bottom.union(middle).union(top)

# Expected properties:
# - Volume: 80*80*20 + 60*60*20 + 40*40*20 = 128,000 + 72,000 + 32,000 = 232,000 mm³
# - Faces: 14 (6 per level minus shared, plus step faces)
# - Edges: complex stepped topology
