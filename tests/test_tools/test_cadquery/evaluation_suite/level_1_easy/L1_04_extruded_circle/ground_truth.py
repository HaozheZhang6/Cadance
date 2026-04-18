"""Ground truth CadQuery code for L1_04: Extruded Circle.

This creates a cylinder via sketch+extrude: circle radius 30mm, extruded 50mm.

Design decisions:
- Intent explicitly requests sketch+extrude approach (not cylinder())
- Using circle() for sketch, extrude() for 3D
- Produces same geometry as cylinder(50, 30) but different construction
"""

import cadquery as cq

# Sketch circle on XY plane, extrude upward
result = cq.Workplane("XY").circle(30).extrude(50)

# Expected properties:
# - Volume: π * 30² * 50 ≈ 141,371.67 mm³
# - Bounding box: 60 x 60 x 50 (diameter = 2 * radius)
# - Faces: 3 (top, bottom, curved surface)
# - Edges: 2 (top circle, bottom circle)
