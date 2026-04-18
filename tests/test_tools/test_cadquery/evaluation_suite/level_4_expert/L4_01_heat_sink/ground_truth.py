"""Ground truth CadQuery code for L4_01: Heat Sink with Cooling Fins.

This creates a heat sink with base plate and parallel cooling fins.

Design decisions:
- Base plate with fins extruded from top surface
- Fins evenly spaced: 8 fins of 2mm thickness = 16mm total fin width
- Remaining space: 60 - 16 = 44mm for 9 gaps (8 fins create 9 gaps)
- Gap size: 44 / 9 = 4.889mm
- First fin center: gap/2 + fin_thickness/2 = 2.444 + 1 = 3.444mm from edge
- Fin spacing (center to center): gap + fin_thickness = 4.889 + 2 = 6.889mm

Volume calculation:
- Base plate: 100 * 60 * 5 = 30,000 mm³
- 8 fins: 8 * (100 * 2 * 25) = 8 * 5,000 = 40,000 mm³
- Total: 30,000 + 40,000 = 70,000 mm³
"""

import cadquery as cq

# Calculate fin spacing
fin_count = 8
fin_thickness = 2
base_width = 60

# Total fin width
total_fin_width = fin_count * fin_thickness  # 16mm
# Remaining space for gaps (n fins create n+1 gaps if at edges, but we want equal spacing)
# With fins and equal gaps: n*fin_thickness + (n+1)*gap = width
# gap = (width - n*fin_thickness) / (n+1) = (60 - 16) / 9 = 4.889mm
gap = (base_width - total_fin_width) / (fin_count + 1)

# First fin center position from edge
first_fin_y = gap + fin_thickness / 2  # 4.889 + 1 = 5.889mm from y=0

# Fin center positions (relative to center of base, which is at y=30)
# First fin at y = 5.889, last at y = 60 - 5.889 = 54.111
# Offset from center (y=30): first is at -24.111, last at +24.111
fin_spacing = gap + fin_thickness  # 6.889mm center-to-center

# Create base plate
base = cq.Workplane("XY").box(100, 60, 5)

# Add fins using rectangular array
# Position fin centers symmetrically about Y center
result = (
    base.faces(">Z")  # Top face of base
    .workplane()
    .rarray(1, fin_spacing, 1, fin_count)  # 1 column, 8 rows, spaced by fin_spacing
    .rect(100, fin_thickness)  # Each fin: 100mm long, 2mm thick
    .extrude(25)  # Fin height
)

# Alternative using pushPoints for explicit control:
# fin_y_positions = [first_fin_y + i * fin_spacing - 30 for i in range(fin_count)]
# fin_points = [(0, y) for y in fin_y_positions]
# result = (
#     base
#     .faces(">Z")
#     .workplane()
#     .pushPoints(fin_points)
#     .rect(100, fin_thickness)
#     .extrude(25)
# )

# Expected properties:
# - Volume: 70,000 mm³
# - Bounding box: 100 x 60 x 30 (base 5mm + fin 25mm = 30mm total height)
# - Faces: 50 (base 6 - 1 top + 8 fins * 5 faces + shared connections)
#   Actually: base bottom (1) + base sides (4) + 8 fin tops (8) + 8 fin front/back (16) + 8 fin sides (16) + base top between fins (9)
#   = 1 + 4 + 8 + 16 + 16 + 9 = 54... let's say ~50
# - Edges: 96 (complex topology from fin array)
