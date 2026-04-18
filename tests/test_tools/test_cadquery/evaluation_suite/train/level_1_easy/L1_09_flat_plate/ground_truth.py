"""Ground truth CadQuery code for L1_09: Flat Plate.

This creates a flat rectangular plate with large footprint and thin height.

Design decisions:
- Use box() with plate-like proportions (length >> height)
- Tests different aspect ratios than typical blocks
- 200mm x 150mm x 5mm
"""

import cadquery as cq

# Create flat plate: 200mm x 150mm x 5mm
result = cq.Workplane("XY").box(200, 150, 5)

# Expected properties:
# - Volume: 200 * 150 * 5 = 150,000 mm³
# - Faces: 6
# - Edges: 12
