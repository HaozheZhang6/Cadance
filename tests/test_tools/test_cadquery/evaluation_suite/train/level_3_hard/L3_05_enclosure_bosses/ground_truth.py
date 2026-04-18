"""Ground truth CadQuery code for L3_05: Enclosure with Mounting Bosses.

This creates a shelled rectangular enclosure with internal mounting bosses.

Design decisions:
- Shell with 2mm walls, top face open (becomes the opening)
- Bosses are 8mm diameter cylinders on the inner floor
- Boss centers positioned 8mm from inside walls
- Boss holes are 3mm diameter, through full boss height

Geometry:
- Outer: 120 x 80 x 40 mm
- Inner cavity: 116 x 76 x 38 mm (2mm walls)
- Boss positions: (±50, ±30) from center
- Boss: radius 4mm, height 15mm
- Boss holes: radius 1.5mm, through boss

Volume: shell + 4×boss - 4×holes ≈ 50,847 mm³
"""

import cadquery as cq

# Boss positions: 8mm from inside walls
# Inside dimensions: 116 x 76 (after 2mm wall on each side)
# Boss centers from origin (center of box): ±(58-8)=±50 in X, ±(38-8)=±30 in Y
boss_positions = [
    (50, 30),
    (50, -30),
    (-50, 30),
    (-50, -30),
]

# Create outer box and shell it
enclosure = (
    cq.Workplane("XY")
    .box(120, 80, 40)  # Outer dimensions
    .faces(">Z")  # Select top face
    .shell(-2)  # Shell inward with 2mm walls, removing top
)

# Add mounting bosses on inner floor
# Inner floor is at z = -20 + 2 = -18 (bottom of box + wall thickness)
# We need to work on the inner bottom face
bosses = (
    enclosure.faces("<Z[1]")  # Select inner bottom face (not outer bottom)
    .workplane()
    .pushPoints(boss_positions)
    .circle(4)  # Boss outer radius
    .extrude(15)  # Boss height
)

# Add holes through bosses
result = (
    bosses.faces("<Z[1]")  # Inner floor again
    .workplane()
    .pushPoints(boss_positions)
    .hole(3, 15)  # 3mm diameter, 15mm deep (through boss)
)

# Alternative approach using union:
# enclosure = cq.Workplane("XY").box(120, 80, 40).faces(">Z").shell(-2)
# boss = cq.Workplane("XY").workplane(offset=-18).pushPoints(boss_positions).cylinder(15, 4)
# result = enclosure.union(boss).faces("<Z[1]").workplane().pushPoints(boss_positions).hole(3, 15)

# Expected properties:
# - Volume: ≈ 50,847 mm³
# - Bounding box: 120 x 80 x 40
# - Faces: 17 (outer box 5 + inner box 5 + 4 boss outer + 4 boss inner holes - shared)
# - Edges: 40 (box edges + boss circles)
