"""Ground truth CadQuery code for L2_06: Revolved Cup Shape.

This creates a cup by revolving a profile around a vertical axis.
- Outer diameter: 60mm (radius 30)
- Inner diameter: 52mm (radius 26)
- Height: 70mm
- Base thickness: 5mm
- Wall thickness: 4mm (30-26=4)

Design decisions:
- Draw cross-section profile in XY plane (standard convention)
- X = radial distance from center, Y = height
- Revolve 360° around Y axis (vertical)
- Y is the vertical axis, X is radial

Profile coordinates (in XY plane):
- Start at (0, 0) - center bottom
- To (30, 0) - outer radius at bottom
- Up (30, 70) - outer top
- In (26, 70) - inner top (rim)
- Down (26, 5) - where inner meets base
- In (0, 5) - center of base top
- Close to (0, 0)

Volume calculation:
- Outer cylinder: π * 30² * 70 = 197,920.34 mm³
- Inner cavity: π * 26² * (70-5) = π * 26² * 65 = 138,086.74 mm³
- Net volume: 197,920.34 - 138,086.74 ≈ 59,833.60 mm³
"""

import cadquery as cq

# Create cup by revolving profile around Z axis (vertical)
# Profile drawn in XY plane (X = radial, Y = height)
result = (
    cq.Workplane("XY")
    .moveTo(0, 0)  # Center bottom
    .lineTo(30, 0)  # To outer radius at bottom
    .lineTo(30, 70)  # Up outer wall
    .lineTo(26, 70)  # Across top rim (inner edge)
    .lineTo(26, 5)  # Down inner wall to base top
    .lineTo(0, 5)  # Across to center (base top)
    .close()  # Back to start
    .revolve(360, (0, 0, 0), (0, 1, 0))  # Revolve around Y axis (vertical)
)

# Expected properties:
# - Volume: π*30²*70 - π*26²*65 ≈ 59,833.61 mm³
# - Bounding box: 60 x 70 x 60 (X: diameter, Y: height, Z: diameter)
# - Faces: 4 (outer surface, inner surface, top rim, base bottom)
# - Edges: 4 (outer bottom circle, outer top, inner top, inner base junction)
