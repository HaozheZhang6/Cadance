"""Ground truth CadQuery code for L2_11: Filleted Cylinder.

This creates a cylinder with a filleted top edge.

Design decisions:
- Cylinder: diameter 50mm (radius 25mm), height 35mm
- Fillet: 5mm radius on top edge
- Use edges(">Z") to select top edge for filleting
"""

import cadquery as cq

# Create cylinder with filleted top edge
result = (
    cq.Workplane("XY")
    .cylinder(height=35, radius=25)
    .edges(">Z")  # Select top edge
    .fillet(5)  # 5mm fillet radius
)

# Expected properties:
# - Volume: approximately π * 25² * 35 minus fillet volume ≈ 68,000 mm³
# - Faces: 4 (top, bottom, curved surface, fillet surface)
# - Edges: 4 (bottom circle, 2 at fillet transitions, seam)
