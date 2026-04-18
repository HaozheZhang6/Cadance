"""Ground truth CadQuery code for L4_E01: Lofted Airfoil.

This creates a wing-like shape by lofting between airfoil-like profiles.

Design decisions:
- Root profile: larger teardrop shape (chord 60mm)
- Tip profile: smaller teardrop shape (chord 30mm)
- Span (loft distance): 100mm
- Creates a tapered wing section
"""

import cadquery as cq


# Define airfoil-like profile points (simplified teardrop)
def airfoil_points(chord, thickness_ratio=0.12):
    """Generate simplified airfoil points."""
    t = chord * thickness_ratio
    return [
        (0, 0),  # Leading edge
        (chord * 0.25, t),  # Upper surface
        (chord * 0.5, t * 0.8),
        (chord * 0.75, t * 0.4),
        (chord, 0),  # Trailing edge
        (chord * 0.75, -t * 0.4),
        (chord * 0.5, -t * 0.8),
        (chord * 0.25, -t),  # Lower surface
    ]


# Create root profile (larger)
root_points = airfoil_points(60, 0.15)
root = cq.Workplane("XZ").spline(root_points).close()

# Create tip profile (smaller, offset in Y)
tip_points = airfoil_points(30, 0.12)
tip = (
    cq.Workplane("XZ")
    .workplane(offset=100)
    .center(15, 0)  # Offset tip forward
    .spline(tip_points)
    .close()
)

# Loft between profiles
result = (
    cq.Workplane("XZ")
    .spline(root_points)
    .close()
    .workplane(offset=100)
    .center(15, 0)
    .spline(tip_points)
    .close()
    .loft()
)

# Expected properties:
# - Tapered wing shape
# - Complex curved surfaces
# - Volume depends on exact spline shapes
