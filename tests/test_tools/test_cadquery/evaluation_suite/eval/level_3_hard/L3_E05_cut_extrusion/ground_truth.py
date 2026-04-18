"""Ground truth CadQuery code for L3_E05: Cut Extrusion.

This creates a block with a T-slot cut into one face.

Design decisions:
- Base block: 80mm x 50mm x 30mm
- T-slot cut into the top face, running full length
- T-slot dimensions: 10mm wide slot, 15mm wide base, 20mm total depth
"""

import cadquery as cq

# Create base block
block = cq.Workplane("XY").box(80, 50, 30)

# Create T-slot profile (inverted T shape)
# Start from top face and cut down
t_slot = (
    cq.Workplane("XZ")
    .workplane(offset=25)  # Move to front face
    .center(0, 15)  # Center at top of block
    # Draw T-slot profile
    .moveTo(-5, 0)  # Start left side of narrow slot
    .lineTo(-5, -10)  # Go down narrow portion
    .lineTo(-7.5, -10)  # Widen for T base
    .lineTo(-7.5, -20)  # Go to bottom of T
    .lineTo(7.5, -20)  # Across bottom
    .lineTo(7.5, -10)  # Up right side of T base
    .lineTo(5, -10)  # Narrow for slot
    .lineTo(5, 0)  # Up to top
    .close()
    .extrude(50)  # Extrude through full width
)

# Cut the T-slot from the block
result = block.cut(t_slot)

# Expected properties:
# - Base volume: 80 * 50 * 30 = 120,000 mm³
# - Minus T-slot volume
# - Faces: 6 block faces + T-slot internal surfaces
# - Edges: Multiple due to T-slot
