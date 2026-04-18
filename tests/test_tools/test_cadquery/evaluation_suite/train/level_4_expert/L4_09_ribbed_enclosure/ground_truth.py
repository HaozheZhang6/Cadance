"""Ground truth CadQuery code for L4_09: Ribbed Enclosure.

This creates a shelled box with internal reinforcement ribs.

Design decisions:
- Outer box: 90mm x 70mm x 45mm
- Wall thickness: 3mm (inner cavity: 84mm x 64mm x 42mm)
- Shell open on top
- 4 internal ribs: 2 lengthwise, 2 widthwise
- Ribs: 2mm thick, 15mm tall from inner bottom
"""

import cadquery as cq

# Create outer box and shell it
enclosure = (
    cq.Workplane("XY")
    .box(90, 70, 45)
    .faces(">Z")  # Select top face to keep open
    .shell(-3)  # Shell inward 3mm
)

# Add lengthwise ribs (parallel to X axis, 90mm long)
# Inner width is 64mm, ribs at Y = ±16mm from center
# Rib dimensions: 84mm long x 2mm thick x 15mm tall
lengthwise_rib1 = (
    cq.Workplane("XY")
    .workplane(offset=3)  # Start at inner bottom
    .center(0, 16)  # Offset in Y
    .box(84, 2, 15)
)

lengthwise_rib2 = cq.Workplane("XY").workplane(offset=3).center(0, -16).box(84, 2, 15)

# Add widthwise ribs (parallel to Y axis, 70mm span but only inner cavity)
# Inner length is 84mm, ribs at X = ±21mm from center
widthwise_rib1 = cq.Workplane("XY").workplane(offset=3).center(21, 0).box(2, 64, 15)

widthwise_rib2 = cq.Workplane("XY").workplane(offset=3).center(-21, 0).box(2, 64, 15)

# Union all parts
result = (
    enclosure.union(lengthwise_rib1)
    .union(lengthwise_rib2)
    .union(widthwise_rib1)
    .union(widthwise_rib2)
)

# Expected properties:
# - Volume: shell + 4 ribs (with intersections)
# - Complex internal geometry
