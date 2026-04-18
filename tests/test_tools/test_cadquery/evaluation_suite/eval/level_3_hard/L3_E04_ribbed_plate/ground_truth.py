"""Ground truth CadQuery code for L3_E04: Ribbed Plate.

This creates a plate with reinforcing ribs on the bottom.

Design decisions:
- Base plate: 100mm x 60mm x 5mm
- Three parallel ribs underneath, 5mm thick, 15mm tall
- Ribs run along the length (X direction)
- Ribs spaced evenly (at Y = -20, 0, +20)
"""

import cadquery as cq

# Create base plate
plate = cq.Workplane("XY").box(100, 60, 5)

# Create ribs on the bottom face
# Each rib is 100mm long, 5mm wide, 15mm tall
ribs = (
    cq.Workplane("XY")
    .workplane(offset=-2.5)  # Move to bottom of plate
    .pushPoints([(0, -20), (0, 0), (0, 20)])
    .box(100, 5, 15, centered=(True, True, False))
)

# Move ribs down so they hang from the plate
ribs = ribs.translate((0, 0, -15))

# Union plate and ribs
result = plate.union(ribs)

# Expected properties:
# - Plate volume: 100 * 60 * 5 = 30,000 mm³
# - Rib volume: 3 * 100 * 5 * 15 = 22,500 mm³
# - Total volume: 52,500 mm³
# - Multiple faces and edges
