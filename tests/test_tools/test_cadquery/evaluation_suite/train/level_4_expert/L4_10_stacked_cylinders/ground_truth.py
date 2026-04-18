"""Ground truth CadQuery code for L4_10: Stacked Cylinders.

This creates a stepped shaft with three diameter sections.

Design decisions:
- Bottom: diameter 60mm (r=30mm), height 20mm
- Middle: diameter 40mm (r=20mm), height 35mm
- Top: diameter 25mm (r=12.5mm), height 25mm
- All centered on Z axis
- Total height: 20 + 35 + 25 = 80mm
"""

import cadquery as cq

# Create bottom cylinder
bottom = cq.Workplane("XY").cylinder(height=20, radius=30)

# Create middle cylinder, positioned on top of bottom
middle = (
    cq.Workplane("XY")
    .workplane(offset=20)  # At top of bottom
    .cylinder(height=35, radius=20)
)

# Create top cylinder, positioned on top of middle
top = (
    cq.Workplane("XY")
    .workplane(offset=55)  # At top of middle (20+35)
    .cylinder(height=25, radius=12.5)
)

# Union all sections
result = bottom.union(middle).union(top)

# Expected properties:
# - Volume: π*30²*20 + π*20²*35 + π*12.5²*25
# - Bottom: π*900*20 ≈ 56,549 mm³
# - Middle: π*400*35 ≈ 43,982 mm³
# - Top: π*156.25*25 ≈ 12,272 mm³
# - Total: ≈ 112,803 mm³
# - Faces: multiple circular faces and curved surfaces
