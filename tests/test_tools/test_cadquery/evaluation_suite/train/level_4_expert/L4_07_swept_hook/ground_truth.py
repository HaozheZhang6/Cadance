"""Ground truth CadQuery code for L4_07: Swept Hook.

This creates a hook shape using sweep along a curved path.

Design decisions:
- Profile: 10mm diameter circle
- Path: vertical 50mm, then 180° arc with 25mm radius
- Sweep the circle along this path
- Results in J-hook or candy cane shape
"""

import cadquery as cq

# Create the path for the hook
# Start at origin, go up 50mm, then arc 180° with 25mm radius
# Path in XZ plane
path = (
    cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(0, 50)  # Vertical 50mm
    .tangentArcPoint((50, 50), relative=False)  # Arc to create hook
)

# Create circle profile and sweep
result = cq.Workplane("XY").circle(5).sweep(path)  # 10mm diameter (radius 5mm)

# Expected properties:
# - Volume: cross-section area * path length
# - Straight part: π*5² * 50 ≈ 3,927 mm³
# - Curved part: π*5² * π*25 ≈ 6,168 mm³
# - Total: ≈ 10,095 mm³
# - Complex curved surface
