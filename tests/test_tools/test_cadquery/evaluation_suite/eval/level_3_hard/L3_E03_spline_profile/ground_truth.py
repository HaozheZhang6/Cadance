"""Ground truth CadQuery code for L3_E03: Spline Profile.

This creates an extruded shape with a spline-based profile.

Design decisions:
- Profile defined by spline through control points
- Creates a smooth, organic shape
- Extrude height: 20mm
- Spline forms a closed, teardrop-like shape
"""

import cadquery as cq

# Define spline control points for a teardrop shape
points = [
    (0, 30),  # Top point
    (15, 20),  # Right upper
    (20, 0),  # Right middle
    (15, -15),  # Right lower
    (0, -20),  # Bottom point
    (-15, -15),  # Left lower
    (-20, 0),  # Left middle
    (-15, 20),  # Left upper
]

# Create closed spline profile and extrude
result = cq.Workplane("XY").spline(points, includeCurrent=False).close().extrude(20)

# Expected properties:
# - Smooth curved profile
# - Volume depends on spline shape
# - Faces: 3 (top, bottom, curved side)
# - Edges: 2 spline curves (top and bottom)
