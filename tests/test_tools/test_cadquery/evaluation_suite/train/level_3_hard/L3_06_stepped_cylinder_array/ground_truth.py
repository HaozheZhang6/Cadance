"""Ground truth CadQuery code for L3_06: Stepped Cylinder Array.

This creates a linear array of cylinders with increasing heights (stepped).

Design decisions:
- Base cylinder: 20mm diameter, 10mm height
- 4 cylinders in a row, spaced 30mm apart
- Each subsequent cylinder is 10mm taller (10, 20, 30, 40mm)
- Create using union of individual cylinders
"""

import cadquery as cq

# Create stepped cylinder array
# Start with first cylinder
result = cq.Workplane("XY").cylinder(10, 10)  # height=10, radius=10

# Add remaining cylinders at increasing heights
for i in range(1, 4):
    height = 10 + (i * 10)  # 20, 30, 40mm
    x_offset = i * 30  # 30, 60, 90mm
    cylinder = cq.Workplane("XY").center(x_offset, 0).cylinder(height, 10)
    result = result.union(cylinder)

# Expected properties:
# - Cylinder volumes: π*10²*10 + π*10²*20 + π*10²*30 + π*10²*40
# - Total volume: π*100*(10+20+30+40) = π*100*100 ≈ 31,415.93 mm³
# - Faces: 4 cylinders * 3 faces = 12 (but some may merge)
# - Edges: Multiple circles
