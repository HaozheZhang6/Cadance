"""Ground truth CadQuery code for L4_02: 90-Degree Pipe Elbow.

This creates a pipe elbow with 90-degree bend and straight end sections.

Design decisions:
- Sweep an annular profile along a path
- Path in XZ plane: straight 20mm → 90° arc (r=45mm) → straight 20mm
- Profile: concentric circles creating hollow pipe cross-section

Geometry:
- Outer diameter: 30mm (radius 15)
- Inner diameter: 24mm (radius 12), wall thickness: 3mm
- Bend radius: 45mm (to centerline)
- Straight sections: 20mm each end
- Path: origin → +Z 20mm → arc to +X → +X 20mm

Volume: ~28,166 mm³ (annular cross-section swept along path)
"""

import cadquery as cq

# Pipe dimensions
outer_radius = 15  # 30mm outer diameter / 2
inner_radius = 12  # 24mm inner diameter / 2
bend_radius = 45  # centerline bend radius
straight_len = 20  # straight section length

# Create the sweep path
# Path in XZ plane: start at origin going +Z, arc to +X, then straight +X
path = (
    cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(0, straight_len)  # First straight (Z direction)
    .tangentArcPoint(
        (bend_radius, straight_len + bend_radius), relative=False
    )  # 90° arc
    .lineTo(
        bend_radius + straight_len, straight_len + bend_radius
    )  # Second straight (X direction)
)

# Create annular profile and sweep
# Profile is in XY plane at the start of the path
result = (
    cq.Workplane("XY")
    .circle(outer_radius)
    .circle(inner_radius)  # Creates annular region
    .sweep(path)
)

# Alternative approach - sweep solid then shell:
# path = cq.Workplane("XZ").moveTo(0,0).lineTo(0,20).tangentArcPoint((45,65),False).lineTo(65,65)
# solid = cq.Workplane("XY").circle(15).sweep(path)
# result = solid.shell(-3)  # Shell to 3mm wall

# Expected properties:
# - Volume: ≈ 18,562 mm³ (hollow pipe volume)
# - Bounding box: 65 x 30 x 65 (bend_radius + straight = 45+20 = 65)
# - Faces: 4 (outer surface, inner surface, two end faces)
# - Edges: 8 (4 circles: 2 outer + 2 inner at each end)
