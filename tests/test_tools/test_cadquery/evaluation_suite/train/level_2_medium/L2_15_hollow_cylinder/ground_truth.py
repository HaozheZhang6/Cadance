"""Ground truth CadQuery code for L2_15: Hollow Cylinder via Shell.

This creates a hollow cylinder using the shell operation.

Design decisions:
- Start with solid cylinder: diameter 70mm, height 50mm
- Shell with 5mm wall thickness
- Remove top and bottom faces to create open-ended tube
- Shell inward (negative thickness)
"""

import cadquery as cq

# Create hollow cylinder via shell
# NOTE: .solids() extracts the Solid from the Compound returned by shell
result = (
    cq.Workplane("XY")
    .cylinder(height=50, radius=35)  # Outer diameter 70mm
    .faces(">Z or <Z")  # Select both end faces
    .shell(-5)  # Shell inward 5mm, removing selected faces
    .solids()  # Extract solid from compound for .val() to work correctly
)

# Expected properties:
# - Outer radius: 35mm, Inner radius: 30mm
# - Volume: π * (35² - 30²) * 50 = π * 325 * 50 ≈ 51,051.03 mm³
# - Faces: 2 (outer curved, inner curved)
# - Edges: 4 (top outer, top inner, bottom outer, bottom inner) + seams
