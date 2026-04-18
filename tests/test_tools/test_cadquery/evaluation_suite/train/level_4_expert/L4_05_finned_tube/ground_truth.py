"""Ground truth CadQuery code for L4_05: Finned Tube.

This creates a tube with radial fins for heat exchange.

Design decisions:
- Main tube: OD 30mm (r=15mm), ID 20mm (r=10mm), length 100mm
- 8 fins at 45° intervals, 2mm thick, 15mm radial extent
- Fins run full length (100mm)
- Build tube first, then add fins
"""

import math

import cadquery as cq

# Create main tube
tube = (
    cq.Workplane("XY")
    .circle(15)  # Outer radius 15mm
    .circle(10)  # Inner radius 10mm
    .extrude(100)  # Length 100mm
)

# Create fin positions (8 fins at 45° intervals)
# Fins are rectangles positioned radially
fin_angles = [i * 45 for i in range(8)]

# Add fins using union
result = tube
for angle in fin_angles:
    # Position fin at this angle
    # Fin extends from radius 15mm to 30mm (15mm outward)
    # Fin is 2mm thick, 100mm long
    rad = math.radians(angle)

    # Calculate fin center position (at radius 22.5mm = 15 + 15/2)
    fin_center_r = 15 + 15 / 2  # 22.5mm from center

    fin = (
        cq.Workplane("XY")
        .transformed(rotate=(0, 0, angle))
        .center(fin_center_r, 0)
        .rect(15, 2)  # 15mm radial x 2mm thick
        .extrude(100)
    )
    result = result.union(fin)

# Expected properties:
# - Volume: tube + 8*fins
# - Tube: π*(15²-10²)*100 ≈ 39,270 mm³
# - 8 fins: 8*(15*2*100) = 24,000 mm³
# - Total: ≈ 63,270 mm³
