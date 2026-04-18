"""Ground truth CadQuery code for L2_E03: Polygon Extrusion (Octagon).

This creates a regular octagon extruded into a prism.

Design decisions:
- Use regularPolygon() to create an 8-sided polygon
- Circumscribed diameter: 40mm
- Extrude height: 30mm
"""

import cadquery as cq

# Create octagonal prism: 40mm diameter, 30mm height
result = (
    cq.Workplane("XY")
    .polygon(8, 40)  # 8 sides, 40mm circumscribed diameter
    .extrude(30)
)

# Expected properties:
# - Octagon area: 2 * (1 + sqrt(2)) * s² where s is side length
# - For circumradius R=20, s = 2*R*sin(π/8) ≈ 15.31mm
# - Area ≈ 1131.37 mm²
# - Volume: 1131.37 * 30 ≈ 33,941.13 mm³
# - Faces: 10 (top, bottom, 8 sides)
# - Edges: 24 (8 top, 8 bottom, 8 vertical)
