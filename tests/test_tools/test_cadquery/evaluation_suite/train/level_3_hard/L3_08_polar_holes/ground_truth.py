"""Ground truth CadQuery code for L3_08: Disk with Polar Hole Pattern.

This creates a circular disk with evenly-spaced holes in a circular pattern.

Design decisions:
- Disk: diameter 80mm (radius 40mm), thickness 12mm
- Holes: 6 x 8mm diameter on 60mm bolt circle (radius 30mm)
- Use polarArray for circular pattern
"""

import cadquery as cq

# Bolt circle radius
bolt_radius = 30  # 60mm diameter / 2

# Create disk with polar hole pattern
result = (
    cq.Workplane("XY")
    .cylinder(height=12, radius=40)  # Disk: diameter 80mm, thickness 12mm
    .faces(">Z")
    .workplane()
    .polarArray(bolt_radius, 0, 360, 6)  # 6 holes on 30mm radius
    .hole(8)  # 8mm diameter holes
)

# Expected properties:
# - Volume: π*40²*12 - 6*π*4²*12 ≈ 60,319 - 3,619 ≈ 56,700 mm³
# - Faces: 3 + 6 = 9 (disk faces + 6 hole surfaces)
# - Edges: 3 + 12 = 15 (disk edges + 12 hole circles)
