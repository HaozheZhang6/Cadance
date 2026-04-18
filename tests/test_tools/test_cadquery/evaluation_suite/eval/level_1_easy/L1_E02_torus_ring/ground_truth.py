"""Ground truth CadQuery code for L1_E02: Torus Ring.

This creates a torus (donut shape) with specified major and minor radii.

Design decisions:
- Use Solid.makeTorus() for direct torus creation
- Major radius (center to tube center): 40mm
- Minor radius (tube radius): 10mm
- Torus centered at origin, lying in XY plane
"""

import cadquery as cq
from cadquery import Solid

# Create a torus: major radius 40mm, minor radius 10mm
torus = Solid.makeTorus(40, 10)
result = cq.Workplane("XY").newObject([torus])

# Expected properties:
# - Volume: 2 * π² * R * r² = 2 * π² * 40 * 10² ≈ 78,956.84 mm³
# - Faces: 1 (single toroidal surface)
# - Edges: 0 (no edges on a torus)
