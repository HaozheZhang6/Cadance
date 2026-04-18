"""Ground truth CadQuery code for L2_E05: Drafted Box.

This creates a box with draft angles on the sides (tapered walls).

Design decisions:
- Base box concept: 50mm x 50mm base, 40mm height
- Draft angle: 5 degrees on all vertical faces
- Draft makes the part narrower at the top (for mold release)
- Use extrude with taper parameter
"""

import cadquery as cq

# Create box with draft angle using tapered extrude
result = cq.Workplane("XY").rect(50, 50).extrude(40, taper=5)  # 5-degree draft angle

# Expected properties:
# - Base: 50mm x 50mm
# - Top is smaller due to 5° taper
# - Top size: 50 - 2*40*tan(5°) ≈ 50 - 7.0 ≈ 43mm per side
# - Volume: frustum volume (smaller than 50*50*40)
# - Faces: 6 (top, bottom, 4 tapered sides)
# - Edges: 12
