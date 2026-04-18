"""Ground truth CadQuery code for L1_06: Sphere.

This creates a sphere with diameter 50mm centered at origin.

Design decisions:
- Intent says "diameter 50mm" but CadQuery sphere() takes radius
- Must convert: radius = diameter / 2 = 25mm
- Sphere is automatically centered on workplane origin
"""

import cadquery as cq

# Create sphere: radius=25mm (from diameter 50mm)
result = cq.Workplane("XY").sphere(25)

# Expected properties:
# - Volume: (4/3) * π * r³ = (4/3) * π * 25³ ≈ 65,449.85 mm³
# - Bounding box: 50 x 50 x 50 (diameter in all directions)
# - Faces: 1 (single continuous spherical surface)
# - Edges: 0 (sphere has no edges)
