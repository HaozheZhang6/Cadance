"""Ground truth CadQuery code for L2_08: Slotted Bracket.

This creates a rectangular bracket with a slot cut through it and filleted edges.

Design decisions:
- Base block: 80mm x 40mm x 15mm
- Center slot: 40mm long x 10mm wide, through the full thickness
- Fillet the top edges with 3mm radius
- Slot is oriented along the X axis
"""

import cadquery as cq

# Create bracket with slot and fillets
result = (
    cq.Workplane("XY")
    .box(80, 40, 15)
    .faces(">Z")
    .workplane()
    .slot2D(40, 10)  # 40mm long, 10mm wide slot
    .cutThruAll()
    .faces(">Z")
    .edges()
    .fillet(3)
)

# Expected properties:
# - Box volume: 80 * 40 * 15 = 48,000 mm³
# - Slot volume: (40-10)*10*15 + π*5²*15 ≈ 4,500 + 1,178.10 ≈ 5,678.10 mm³
# - Volume after slot: ~42,321.90 mm³
# - Fillets reduce volume slightly
# - Faces: 6 box + slot surfaces
# - Edges: Multiple due to slot and fillets
