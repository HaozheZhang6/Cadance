"""Ground truth CadQuery code for L1_10: Extruded Triangle.

This creates a triangular prism from an equilateral triangle.

Design decisions:
- Use regularPolygon(3) for equilateral triangle
- The radius parameter is the circumradius (center to vertex)
- For side length s, circumradius r = s / sqrt(3) ≈ s * 0.577
- Side 40mm → circumradius ≈ 23.09mm
"""

import math

import cadquery as cq

# Calculate circumradius for equilateral triangle with side 40mm
# r = s / sqrt(3) for inscribed circle, but regularPolygon uses circumradius
# circumradius = s / (2 * sin(π/n)) = 40 / (2 * sin(60°)) = 40 / sqrt(3) ≈ 23.09
side_length = 40
circumradius = side_length / math.sqrt(3)

# Create triangular prism: equilateral triangle with 40mm sides, extruded 30mm
result = cq.Workplane("XY").polygon(3, circumradius * 2).extrude(30)

# Expected properties:
# - Volume: (sqrt(3)/4) * s² * h = (sqrt(3)/4) * 40² * 30 ≈ 20,784.61 mm³
# - Faces: 5 (2 triangular ends + 3 rectangular sides)
# - Edges: 9 (3 on each triangular face + 3 vertical edges)
