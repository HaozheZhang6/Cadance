"""Ground truth CadQuery code for L2_06: Revolved Cup Shape.

This creates a cup by revolving a profile around the Y axis.
- Outer diameter: 60mm (radius 30)
- Inner diameter: 52mm (radius 26)
- Height: 70mm
- Base thickness: 5mm
- Wall thickness: 4mm (30-26=4)

Design decisions:
- Draw cross-section profile in XZ plane
- Profile is the cup wall cross-section (closed polygon)
- Revolve 360° around the Y axis (which is vertical in XZ plane)

Profile coordinates (in XZ plane, Z is up):
- Start at inner radius at base top: (26, 5)
- Go to outer radius at base: (30, 5)
- Up outer wall: (30, 70)
- Across top rim: (26, 70)
- Down inner wall: (26, 5) - close

Wait, that's just a wall. We need to include the base:
- Start at (0, 0) - center bottom
- To (30, 0) - outer bottom edge
- Up (30, 70) - outer top
- In (26, 70) - inner top
- Down (26, 5) - where inner meets base
- In (0, 5) - center of base top
- Close to (0, 0)

This creates a solid cup with base.

Volume calculation:
- Outer cylinder: π * 30² * 70 = 197,920.34 mm³
- Inner cavity: π * 26² * (70-5) = π * 26² * 65 = 138,086.74 mm³
- Net: 197,920.34 - 138,086.74 ≈ 59,833.60 mm³

Hmm, let me recalculate more carefully:
- Outer cylinder: π * 30² * 70 = π * 900 * 70 = 197,920.34
- Inner void (hollow part): π * 26² * 65 = π * 676 * 65 = 138,086.74
- Solid volume: 197,920.34 - 138,086.74 = 59,833.60 mm³

Actually I had 57955.09 in spec. Let me recheck:
π * 30² * 70 = 3.14159 * 900 * 70 = 197920.35
π * 26² * 65 = 3.14159 * 676 * 65 = 138086.74
Difference = 59833.61

I'll update the spec to 59833.61.
"""

import cadquery as cq

# Create cup by revolving profile around Y axis
# Profile drawn in XZ plane (X = radial, Z = height)
result = (
    cq.Workplane("XZ")
    .moveTo(0, 0)  # Center bottom
    .lineTo(30, 0)  # To outer radius at bottom
    .lineTo(30, 70)  # Up outer wall
    .lineTo(26, 70)  # Across top rim (inner edge)
    .lineTo(26, 5)  # Down inner wall to base top
    .lineTo(0, 5)  # Across to center (base top)
    .close()  # Back to start
    .revolve(360, (0, 0, 0), (0, 1, 0))  # Revolve around Y axis
)

# Expected properties:
# - Volume: π*30²*70 - π*26²*65 ≈ 59,833.61 mm³
# - Bounding box: 60 x 60 x 70 (diameter x diameter x height)
# - Faces: 4 (outer surface, inner surface, top rim, base bottom)
# - Edges: 4 (outer bottom circle, outer top, inner top, inner base junction)
