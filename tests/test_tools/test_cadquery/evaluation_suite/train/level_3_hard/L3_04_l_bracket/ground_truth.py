"""Ground truth CadQuery code for L3_04: L-Bracket with Mounting Holes.

This creates an L-shaped mounting bracket with mounting holes on both legs.

Design decisions:
- L-profile drawn in XY plane (standard convention)
- X = horizontal leg direction, Y = vertical leg direction (height)
- Extrude along Z axis (width direction, 60mm)
- Inside corner fillet for stress relief
- Holes positioned per specification

L-profile area:
- Vertical leg: 80mm tall (Y), 5mm thick (X)
- Horizontal leg: 50mm long from corner (X), 5mm thick (Y)
- Total X extent: 5 + 50 = 55mm

Volume calculation:
- L-profile area: 80*5 + 50*5 = 650 mm²
- Extruded 60mm: 650 * 60 = 39,000 mm³
- Fillet adds: ~1,288 mm³
- 4 holes remove: 4 * π * 3² * 5 ≈ 566 mm³
- Net: ~38,306 mm³
"""

import cadquery as cq

# Create L-profile in XY plane and extrude along Z
# L-shape: vertical 80mm tall (Y), horizontal 50mm long (X), both 5mm thick
l_profile = (
    cq.Workplane("XY")
    .moveTo(0, 0)
    .lineTo(55, 0)  # Horizontal bottom (5mm vertical + 50mm horizontal leg)
    .lineTo(55, 5)  # Up to horizontal leg top
    .lineTo(5, 5)  # Back to inside corner
    .lineTo(5, 80)  # Up vertical leg
    .lineTo(0, 80)  # Top of vertical leg
    .close()
    .extrude(60)  # Extrude along Z (width)
)

# Add inside corner fillet
bracket = (
    l_profile.edges("|Z")  # Edges parallel to Z axis
    .edges("not(<X or >X or <Y or >Y)")  # Inside corner edge
    .fillet(10)
)

# Add holes on vertical leg (face at x=0, facing -X)
# Holes at z=20 and z=40 (20mm from edges), y=40 (centered at 80/2)
vertical_holes = (
    bracket.faces("<X")  # Select face at x=0 (vertical leg outer face)
    .workplane()
    .pushPoints([(20, 40), (40, 40)])  # (z, y) coordinates on this face
    .hole(6)  # 6mm diameter through holes
)

# Add holes on horizontal leg (face at y=0, facing -Y)
# Holes at x=40 (15mm from free end at x=55), z=15 and z=45 (15mm from edges)
result = (
    vertical_holes.faces("<Y")  # Select bottom face (horizontal leg)
    .workplane()
    .pushPoints([(40, 15), (40, 45)])  # (x, z) coordinates on this face
    .hole(6)  # 6mm diameter through holes
)

# Expected properties:
# - Volume: ≈ 38,306 mm³
# - Bounding box: 55 x 80 x 60 (X x Y x Z)
# - Faces: depends on fillet and hole implementation
# - Edges: depends on fillet and hole implementation
