"""Ground truth CadQuery code for L1_07: Extruded Hexagon.

This creates a regular hexagon extruded to form a hexagonal prism.

Design decisions:
- Use regularPolygon() to create a 6-sided polygon (hexagon)
- Circumscribed radius of 25mm (distance from center to vertex)
- Extrude 40mm in height
- Hexagon centered on XY plane origin
"""

import cadquery as cq

# Create hexagonal prism: 25mm circumradius, 40mm height
result = (
    cq.Workplane("XY")
    .polygon(6, 50)  # 6 sides, 50mm diameter (circumscribed)
    .extrude(40)
)

# Expected properties:
# - Hexagon area = (3 * sqrt(3) / 2) * s² where s = side length
# - For circumradius R=25, side s = R = 25mm
# - Area = (3 * sqrt(3) / 2) * 25² ≈ 1623.80 mm²
# - Volume = 1623.80 * 40 ≈ 64,951.91 mm³
# - Faces: 8 (top, bottom, 6 sides)
# - Edges: 18 (6 top, 6 bottom, 6 vertical)
