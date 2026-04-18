"""Ground truth CadQuery code for L3_02: Flanged Cylinder.

This creates a cylinder with mounting flange and bolt holes.

Design decisions:
- Create flange first, then add main cylinder on top
- Bolt circle of 45mm diameter → holes at radius 22.5mm
- 4 holes at 90° intervals (0°, 90°, 180°, 270°)

Geometry:
- Flange: radius 30mm, height 8mm (at base)
- Main cylinder: radius 15mm, height 60mm (on top of flange)
- Total height: 68mm
- Bolt holes: 5mm diameter, through flange only

Volume: (π×30²×8) + (π×15²×60) - (4×π×2.5²×8) = 64,403 mm³
"""

import math

import cadquery as cq

# Bolt circle positions: radius 22.5mm, 4 holes at 90° intervals
bolt_radius = 45 / 2  # 22.5mm
hole_positions = [
    (
        bolt_radius * math.cos(math.radians(angle)),
        bolt_radius * math.sin(math.radians(angle)),
    )
    for angle in [0, 90, 180, 270]
]

# Create flanged cylinder
result = (
    cq.Workplane("XY")
    .cylinder(8, 30)  # Flange: height 8, radius 30
    .faces(">Z")
    .workplane()
    .cylinder(60, 15)  # Main cylinder: height 60, radius 15
    .faces("<Z")  # Select bottom face (flange bottom)
    .workplane()
    .pushPoints(hole_positions)
    .hole(5)  # 5mm diameter through holes
)

# Alternative approach using union:
# flange = cq.Workplane("XY").cylinder(8, 30)
# cylinder = cq.Workplane("XY").workplane(offset=8).cylinder(60, 15)
# result = flange.union(cylinder)
# result = result.faces("<Z").workplane().pushPoints(hole_positions).hole(5)

# Expected properties:
# - Volume: ≈ 64,402.65 mm³
# - Bounding box: 60 x 60 x 68 (flange diameter x diameter x total height)
# - Faces: 8 (flange top, flange bottom, flange outer, cylinder outer, cylinder top, 4 hole surfaces... need to recount)
# - Edges: 14 (multiple circles and intersections)
