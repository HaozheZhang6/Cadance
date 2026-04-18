"""Ground truth CadQuery code for L2_10: Cylinder with Center Hole.

This creates a cylindrical tube (cylinder with axial hole).

Design decisions:
- Outer diameter 60mm (radius 30mm)
- Inner diameter 20mm (radius 10mm)
- Height 40mm
- Creates a tube/bushing shape
"""

import cadquery as cq

# Create cylinder with center hole
result = (
    cq.Workplane("XY")
    .cylinder(height=40, radius=30)
    .faces(">Z")
    .workplane()
    .hole(20)  # 20mm diameter through hole
)

# Expected properties:
# - Volume: π * (30² - 10²) * 40 = π * 800 * 40 ≈ 100,530.96 mm³
# - Faces: 4 (outer curved, inner curved, top annulus, bottom annulus)
# - Edges: 6 (2 outer circles + 2 inner circles + 2 seams)
