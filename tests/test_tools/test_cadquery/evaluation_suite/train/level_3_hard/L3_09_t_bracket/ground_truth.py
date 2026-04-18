"""Ground truth CadQuery code for L3_09: T-Bracket.

This creates a T-shaped bracket from two rectangular blocks.

Design decisions:
- Horizontal base: 100mm wide x 30mm deep x 10mm thick (at bottom)
- Vertical part: 30mm wide x 10mm thick x 80mm tall (above base)
- Union of two boxes
- Vertical part centered on base
"""

import cadquery as cq

# Create T-bracket by union of two boxes
# Base: 100mm (X) x 30mm (Y) x 10mm (Z)
base = cq.Workplane("XY").box(100, 30, 10)

# Vertical part: 30mm (X) x 10mm (Y) x 80mm (Z), positioned on top of base
vertical = (
    cq.Workplane("XY").workplane(offset=10).box(30, 10, 80)  # Start at top of base
)

# Union the parts
result = base.union(vertical)

# Expected properties:
# - Volume: 100*30*10 + 30*10*80 = 30,000 + 24,000 = 54,000 mm³
# - Faces: 10 (complex due to T-junction)
# - Edges: 20 (complex topology)
