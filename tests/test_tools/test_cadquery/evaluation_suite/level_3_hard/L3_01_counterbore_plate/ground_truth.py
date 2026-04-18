"""Ground truth CadQuery code for L3_01: Mounting Plate with Counterbored Holes.

This creates a 120x90x12mm plate with four M8 counterbored holes, 15mm from edges.

Design decisions:
- Use cboreHole() for counterbored holes (common for socket head cap screws)
- cboreHole(diameter, cboreDiameter, cboreDepth) - through hole with counterbore
- Hole positions: plate centered, so corners at (±60, ±45)
- 15mm inset means holes at (±45, ±30)

Position calculation:
- Plate 120mm wide, centered: x = ±60
- 15mm from edge: x = ±(60-15) = ±45
- Plate 90mm deep, centered: y = ±45
- 15mm from edge: y = ±(45-15) = ±30

Volume calculation:
- Plate: 120 * 90 * 12 = 129,600 mm³
- Each counterbore hole removes:
  - Through hole: π * 4.5² * 12 = 763.41 mm³
  - Counterbore adds: π * 7² * 8 - π * 4.5² * 8 = 722.57 mm³
  - Total per hole: π * 4.5² * 4 + π * 7² * 8 = 254.47 + 1231.50 = 1485.97
  - Actually: through part (below cbore): π * 4.5² * 4 = 254.47
  - Counterbore part: π * 7² * 8 = 1231.50
  - Total per hole ≈ 977.38 mm³ (if we consider overlap correctly)
- 4 holes: ≈ 3,908 mm³
- Net: ≈ 125,692 mm³

Let me recalculate more carefully:
- Through hole diameter 9mm (radius 4.5), goes through entire 12mm
- Counterbore diameter 14mm (radius 7), depth 8mm from top
- Volume removed per hole:
  - Cylindrical hole 4.5² * π * 12 = 763.41 mm³ (full through)
  - Extra material for counterbore (radius 7 vs 4.5, depth 8):
    π * (7² - 4.5²) * 8 = π * (49 - 20.25) * 8 = π * 28.75 * 8 = 722.57 mm³
  - Total per hole: 763.41 + 722.57 = 1485.98 mm³ (wrong approach)

Actually cboreHole makes:
- A through hole of diameter 9
- Plus a counterbore (larger cylinder) of diameter 14, depth 8

Volume removed = π * (d_cbore/2)² * depth_cbore + π * (d_hole/2)² * (thickness - depth_cbore)
= π * 7² * 8 + π * 4.5² * (12 - 8)
= π * 49 * 8 + π * 20.25 * 4
= 1231.50 + 254.47
= 1485.97 mm³ per hole

4 holes = 5943.88 mm³
Net volume = 129,600 - 5,943.88 = 123,656.12 mm³

Hmm, I had 125691.37 in spec. Let me double-check...

Wait, cboreHole in CadQuery might work differently. The depth parameter is the counterbore depth,
and the through hole goes all the way through. So:
- Counterbore cylinder: π * 7² * 8 = 1231.50 mm³
- Through hole below counterbore: π * 4.5² * (12-8) = π * 4.5² * 4 = 254.47 mm³
- Total per hole: 1485.97 mm³
- 4 holes: 5943.88 mm³
- Net: 129,600 - 5,943.88 = 123,656.12 mm³

I'll update spec to 123656.12.
"""

import cadquery as cq

# Create plate with four counterbored holes
result = (
    cq.Workplane("XY")
    .box(120, 90, 12)
    .faces(">Z")
    .workplane()
    .pushPoints([(-45, -30), (-45, 30), (45, -30), (45, 30)])
    .cboreHole(9, 14, 8)  # hole diameter, cbore diameter, cbore depth
)

# Expected properties:
# - Volume: ≈ 123,656.12 mm³
# - Bounding box: 120 x 90 x 12
# - Faces: 14 (6 plate + 4 counterbore floors + 4 hole cylinders)
# - Edges: 36 (complex due to counterbores)
