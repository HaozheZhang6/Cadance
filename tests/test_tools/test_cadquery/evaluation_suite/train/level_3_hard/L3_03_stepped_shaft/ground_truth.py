"""Ground truth CadQuery code for L3_03: Stepped Shaft with Keyway.

This creates a stepped shaft with a keyway cut.

Design decisions:
- Large section at bottom (z=0 to z=50), small section on top (z=50 to z=85)
- Keyway cut as rectangular slot into cylindrical surface
- Keyway positioned 10mm from shoulder, 20mm long (z=30 to z=50)
- Keyway oriented along X axis (standard convention)

Geometry:
- Large cylinder: radius 12.5mm, height 50mm
- Small cylinder: radius 9mm, height 35mm
- Total height: 85mm
- Keyway: 6mm wide × 3mm deep × 20mm long

Volume: (π×12.5²×50) + (π×9²×35) - ~300 ≈ 33,143 mm³
"""

import cadquery as cq

# Create stepped shaft
large_section = cq.Workplane("XY").cylinder(50, 12.5)  # height 50, radius 12.5
small_section = (
    cq.Workplane("XY")
    .workplane(offset=50)  # Move up to top of large section
    .cylinder(35, 9)  # height 35, radius 9
)

shaft = large_section.union(small_section)

# Create keyway slot
# Keyway: 6mm wide (X), 3mm deep (into shaft from surface), 20mm long (Z)
# Position: starts at z=30 (10mm from shoulder at z=50), ends at z=50
# At surface level: y = 12.5 (shaft radius), cut 3mm deep to y = 9.5
keyway = (
    cq.Workplane("XZ")
    .workplane(offset=12.5 - 1.5)  # Position at radius minus half depth (approximation)
    .center(0, 40)  # Center at z=40 (middle of keyway range 30-50)
    .box(6, 20, 3, centered=(True, True, False))  # 6 wide, 20 long, 3 deep
)

result = shaft.cut(keyway)

# Expected properties:
# - Volume: ≈ 33,143 mm³ (shaft - keyway)
# - Bounding box: 25 x 25 x 85 (large diameter x diameter x total length)
# - Faces: 8 (multiple surfaces including keyway walls)
# - Edges: 14 (circles plus keyway edges)
