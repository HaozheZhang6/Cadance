"""Ground truth CadQuery code for L4_08: Motor Mount Plate.

This creates a motor mounting plate with multiple hole types.

Design decisions:
- Plate: 100mm x 80mm x 12mm
- Central pilot hole: 25mm diameter through
- 4x M6 mounting holes: 6.5mm dia on 65x55mm pattern
- 4x ventilation holes: 5mm dia at corners, 10mm from edges
"""

import cadquery as cq

# Bolt pattern positions (65x55mm rectangle, centered)
bolt_positions = [
    (32.5, 27.5),  # Top right
    (-32.5, 27.5),  # Top left
    (-32.5, -27.5),  # Bottom left
    (32.5, -27.5),  # Bottom right
]

# Ventilation hole positions (10mm from edges)
# Plate is 100x80, so corners at ±50, ±40
# Vent holes at ±(50-10), ±(40-10) = ±40, ±30
vent_positions = [
    (40, 30),
    (-40, 30),
    (-40, -30),
    (40, -30),
]

# Create motor mount plate
result = (
    cq.Workplane("XY")
    .box(100, 80, 12)
    # Central pilot hole
    .faces(">Z")
    .workplane()
    .hole(25)  # 25mm diameter central hole
    # M6 bolt holes
    .pushPoints(bolt_positions)
    .hole(6.5)  # 6.5mm diameter
    # Ventilation holes
    .pushPoints(vent_positions)
    .hole(5)  # 5mm diameter
)

# Expected properties:
# - Volume: plate - all holes
# - Plate: 100*80*12 = 96,000 mm³
# - Pilot: π*12.5²*12 ≈ 5,890 mm³
# - Bolts: 4*π*3.25²*12 ≈ 1,592 mm³
# - Vents: 4*π*2.5²*12 ≈ 942 mm³
# - Net: 96,000 - 8,424 ≈ 87,576 mm³
