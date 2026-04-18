"""Ground truth CadQuery code for L4_04: Swept Channel.

This creates a U-shaped channel by sweeping a rectangular profile along an arc path.

Design decisions:
- Profile: 20mm wide x 10mm tall rectangle
- Sweep path: 90-degree arc with 50mm radius
- Creates a curved channel section
- Profile is perpendicular to the sweep path
"""

import cadquery as cq

# Create the sweep path (90-degree arc)
path = (
    cq.Workplane("XZ")
    .moveTo(0, 0)
    .radiusArc((50, 50), 50)  # Arc to (50, 50) with radius 50
)

# Create the profile and sweep
result = cq.Workplane("XY").rect(20, 10).sweep(path)  # 20mm wide, 10mm tall profile

# Expected properties:
# - Profile area: 20 * 10 = 200 mm²
# - Arc length: (π/2) * 50 ≈ 78.54 mm (quarter circle)
# - Volume ≈ 200 * 78.54 ≈ 15,707.96 mm³
# - Faces: 6 (top, bottom, 2 sides, 2 ends)
# - Edges: 12 (curved edges along sweep)
