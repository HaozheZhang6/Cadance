"""Ground truth CadQuery code for L1_E04: Extruded Ellipse.

This creates an elliptical prism by extruding an ellipse.

Design decisions:
- Use ellipse() to create elliptical sketch
- Major axis: 50mm (X direction)
- Minor axis: 30mm (Y direction)
- Extrude height: 25mm
"""

import cadquery as cq

# Create elliptical prism: 50mm x 30mm ellipse, 25mm height
result = (
    cq.Workplane("XY").ellipse(25, 15).extrude(25)  # Semi-major 25mm, semi-minor 15mm
)

# Expected properties:
# - Ellipse area: π * a * b = π * 25 * 15 ≈ 1,178.10 mm²
# - Volume: 1,178.10 * 25 ≈ 29,452.43 mm³
# - Faces: 3 (top ellipse, bottom ellipse, cylindrical surface)
# - Edges: 2 (top and bottom ellipse curves)
