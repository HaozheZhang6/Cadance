"""Ground truth CadQuery code for L2_07: Tube (Hollow Cylinder).

This creates a hollow cylinder (tube/pipe) with specified outer and inner diameters.

Design decisions:
- Use circle() for outer diameter, then circle() for inner hole
- Outer diameter: 50mm, Inner diameter: 40mm (wall thickness: 5mm)
- Height: 60mm
- Extrude both circles together to create hollow shape
"""

import cadquery as cq

# Create tube: OD=50mm, ID=40mm, height=60mm
result = (
    cq.Workplane("XY")
    .circle(25)  # Outer radius 25mm (OD=50)
    .circle(20)  # Inner radius 20mm (ID=40) - creates hole
    .extrude(60)
)

# Expected properties:
# - Outer volume: π * 25² * 60 ≈ 117,809.72 mm³
# - Inner volume: π * 20² * 60 ≈ 75,398.22 mm³
# - Net volume: 117,809.72 - 75,398.22 ≈ 42,411.50 mm³
# - Faces: 4 (top annulus, bottom annulus, outer cylinder, inner cylinder)
# - Edges: 4 (2 outer circles, 2 inner circles)
