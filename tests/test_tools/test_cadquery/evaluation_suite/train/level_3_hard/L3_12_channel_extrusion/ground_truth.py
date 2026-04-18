"""Ground truth CadQuery code for L3_12: U-Channel Extrusion.

This creates a U-shaped channel profile extruded along its length.

Design decisions:
- Outer dimensions: 50mm wide x 40mm tall
- Wall thickness: 5mm on all sides
- Inner cavity: 40mm wide x 35mm tall
- Extrude 150mm
- Build U-profile with polyline
"""

import cadquery as cq

# Create U-channel profile and extrude
# Profile in XY plane, extrude in Z
# Outer: 50mm wide, 40mm tall
# Walls: 5mm thick

result = (
    cq.Workplane("XY")
    .moveTo(-25, 0)  # Start at bottom left
    .lineTo(-25, 40)  # Up left wall outer
    .lineTo(-20, 40)  # Inward at top
    .lineTo(-20, 5)  # Down inside left wall
    .lineTo(20, 5)  # Across bottom inner
    .lineTo(20, 40)  # Up inside right wall
    .lineTo(25, 40)  # Outward at top right
    .lineTo(25, 0)  # Down right wall outer
    .close()  # Close at bottom
    .extrude(150)  # Extrude 150mm
)

# Expected properties:
# - Volume: (outer_area - inner_area) * length
# - Outer area: 50*40 = 2000mm², Inner area: 40*35 = 1400mm²
# - Cross section: 600mm², Volume: 600 * 150 = 90,000 mm³
# - Faces: 10 (outer top, sides, inner surfaces)
# - Edges: 24 (12 on each end)
