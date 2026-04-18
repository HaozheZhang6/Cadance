"""Ground truth CadQuery code for L2_01: Box with Center Through-Hole.

This creates an 80x60x20mm block with a 15mm diameter through-hole in center.

Design decisions:
- First create the box, then add the hole
- Use faces(">Z") to select the top face for hole placement
- hole() without depth parameter creates through-all hole
- Hole is automatically centered on selected face workplane

Volume calculation:
- Box: 80 * 60 * 20 = 96,000 mm³
- Hole: π * 7.5² * 20 ≈ 3,534.29 mm³
- Net: 96,000 - 3,534.29 ≈ 92,465.71 mm³
"""

import cadquery as cq

# Create box then add through-hole
result = (
    cq.Workplane("XY")
    .box(80, 60, 20)
    .faces(">Z")  # Select top face
    .workplane()
    .hole(15)  # 15mm diameter through-hole (no depth = through-all)
)

# Expected properties:
# - Volume: 96,000 - π*(7.5)²*20 ≈ 92,464.73 mm³
# - Bounding box: 80 x 60 x 20 (unchanged by hole)
# - Faces: 7 (6 box faces + 1 cylindrical hole surface)
# - Edges: 16 (12 box edges + 2 hole circles + 2 where hole meets box faces)
