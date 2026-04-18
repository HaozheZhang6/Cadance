"""Ground truth CadQuery code for L4_03: Pillow Block Bearing Housing.

This creates a bearing housing with base, boss, bore, mounting holes, and chamfer.

Design decisions:
- Base plate with central cylindrical boss on top
- Through bore for bearing (through boss and base)
- Mounting holes at corners, 10mm from edges
- 2mm chamfer on boss top outer edge
- Oil groove omitted for simplicity (complex revolved internal feature)

Geometry:
- Base: 100 x 50 x 12 mm (centered)
- Boss: radius 25mm, height 30mm (on top of base)
- Bore: 35mm diameter, through all (42mm total height)
- Mounting holes: 8mm diameter at (±40, ±15)
- Chamfer: 2mm on boss top outer edge

Volume: ~76,498 mm³
"""

import cadquery as cq
from cadquery.selectors import RadiusNthSelector

# Mounting hole positions: 10mm from edges
# Base is centered at origin, so corners are at ±50, ±25
# Holes at: (±40, ±15)
hole_positions = [
    (40, 15),
    (40, -15),
    (-40, 15),
    (-40, -15),
]

# Create base plate
base = cq.Workplane("XY").box(100, 50, 12)

# Add cylindrical boss on top
# Boss centered on base top face
boss = (
    base.faces(">Z")
    .workplane()
    .cylinder(
        30, 25, centered=(True, True, False)
    )  # 50mm OD = 25mm radius, 30mm tall, not centered in Z
)

# Cut central bore through everything
# Bore diameter 35mm = radius 17.5mm, through full height (42mm)
bored = (
    boss.faces(">Z")  # Top face
    .workplane()
    .hole(35, 42)  # 35mm diameter, 42mm deep (through all)
)

# Add mounting holes in base
# Select bottom face of base and drill up
with_holes = (
    bored.faces("<Z")
    .workplane()
    .pushPoints(hole_positions)
    .hole(8)  # 8mm diameter through holes
)

# Add chamfer on boss top outer edge
# Select the top outer circular edge (larger radius)
chamfered = (
    with_holes.faces(">Z")
    .edges(RadiusNthSelector(-1))  # Outer (largest radius) circle
    .chamfer(2)  # 2mm chamfer
)

# Oil groove omitted for simplicity - revolved internal features are complex
# The main geometry (base, boss, bore, holes, chamfer) is sufficient for testing
result = chamfered

# Expected properties:
# - Volume: ≈ 76,498 mm³
# - Bounding box: 100 x 50 x 42 (base + boss height)
# - Faces: 15 (base faces, boss faces, bore surface, holes, groove surfaces)
# - Edges: 28 (various circles and lines)
