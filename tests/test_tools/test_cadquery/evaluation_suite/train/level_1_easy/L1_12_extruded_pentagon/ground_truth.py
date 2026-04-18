"""Ground truth CadQuery code for L1_12: Extruded Pentagon.

This creates a pentagonal prism from a regular pentagon.

Design decisions:
- Use regularPolygon(5) for regular pentagon
- The polygon() function takes nSides and diameter (circumscribed circle diameter)
- For side length s, circumradius r = s / (2 * sin(π/5)) = s / (2 * 0.588) ≈ s * 0.851
- Side 35mm → circumradius ≈ 29.78mm, diameter ≈ 59.56mm
"""

import math

import cadquery as cq

# Calculate circumscribed circle diameter for pentagon with side 35mm
# circumradius = s / (2 * sin(π/5))
side_length = 35
circumradius = side_length / (2 * math.sin(math.pi / 5))
diameter = circumradius * 2

# Create pentagonal prism: regular pentagon with 35mm sides, extruded 45mm
result = cq.Workplane("XY").polygon(5, diameter).extrude(45)

# Expected properties:
# - Volume: (1/4) * sqrt(5*(5+2*sqrt(5))) * s² * h ≈ 1.720 * 35² * 45 ≈ 94,815 mm³
# - Faces: 7 (2 pentagonal ends + 5 rectangular sides)
# - Edges: 15 (5 on each pentagonal face + 5 vertical edges)
