"""Ground truth CadQuery code for L2_14: Box with Slot.

This creates a rectangular block with a slot cut through it.

Design decisions:
- Block: 90mm x 60mm x 25mm
- Slot: 40mm long x 10mm wide, through entire thickness
- Use slot() or rect() + cutThruAll()
- Slot centered on top face
"""

import cadquery as cq

# Create block with slot
result = (
    cq.Workplane("XY")
    .box(90, 60, 25)
    .faces(">Z")
    .workplane()
    .slot2D(40, 10)  # Slot: 40mm total length, 10mm width (with rounded ends)
    .cutThruAll()
)

# Expected properties:
# - Volume: 90*60*25 - slot_volume
# - Slot has rounded ends (semicircles of radius 5mm)
# - Slot volume: rect part + 2 semicircles = (30*10*25) + (π*5²*25) ≈ 9,463 mm³
# - Net volume: 135,000 - 9,463 ≈ 125,537 mm³
# - Faces: 6 + 2 (slot sides) + 2 (slot ends) - 1 (top) = 9
# - Edges: complex due to slot geometry
