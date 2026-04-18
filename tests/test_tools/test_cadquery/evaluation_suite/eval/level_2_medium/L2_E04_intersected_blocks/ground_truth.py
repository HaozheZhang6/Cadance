"""Ground truth CadQuery code for L2_E04: Intersected Blocks.

This creates the intersection of two overlapping boxes at an angle.

Design decisions:
- First box: 60mm x 60mm x 30mm, centered at origin
- Second box: 60mm x 60mm x 30mm, rotated 45 degrees about Z axis
- Result is the intersection (common volume) of both boxes
"""

import cadquery as cq

# Create first box
box1 = cq.Workplane("XY").box(60, 60, 30)

# Create second box rotated 45 degrees
box2 = cq.Workplane("XY").box(60, 60, 30).rotate((0, 0, 0), (0, 0, 1), 45)

# Intersect the two boxes
result = box1.intersect(box2)

# Expected properties:
# - Intersection creates an octagonal prism
# - The intersection of two identical squares at 45° is a regular octagon
# - Volume depends on exact geometry
# - Faces: 10 (top, bottom, 8 sides from octagon)
# - Edges: 24
