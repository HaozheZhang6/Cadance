"""Ground truth CadQuery code for L1_11: Thick-Walled Pipe.

This creates a pipe/tube using concentric circles and extrusion.

Design decisions:
- Outer diameter 50mm (radius 25mm)
- Inner diameter 30mm (radius 15mm)
- Wall thickness: (50-30)/2 = 10mm
- Use circle() for outer, then circle() for inner to create annulus
"""

import cadquery as cq

# Create pipe: outer diameter 50mm, inner diameter 30mm, length 80mm
result = (
    cq.Workplane("XY")
    .circle(25)  # Outer circle, radius 25mm
    .circle(15)  # Inner circle, radius 15mm (creates annulus)
    .extrude(80)  # Extrude to 80mm length
)

# Expected properties:
# - Volume: π * (R² - r²) * h = π * (25² - 15²) * 80 = π * 400 * 80 ≈ 100,530.96 mm³
# - Faces: 4 (outer curved, inner curved, top annulus, bottom annulus)
# - Edges: 6 (2 outer circles, 2 inner circles, 2 seams)
