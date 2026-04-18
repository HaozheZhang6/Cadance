"""Ground truth CadQuery code for L2_13: Revolved Disk.

This creates a disk shape using revolve operation.

Design decisions:
- Create a simple rectangle profile and revolve it
- Rectangle: 5mm (thickness) x 30mm (radius extent)
- Revolve around axis to create disk
- Results in cylinder-like shape but created via revolve
"""

import cadquery as cq

# Create disk by revolving rectangle profile
# Profile: rectangle from origin out to radius 30mm, thickness 5mm
# Using rect with centered=False to create profile from origin
result = (
    cq.Workplane("XZ")  # Profile in XZ plane (X = radial, Z = thickness)
    .rect(30, 5, centered=False)  # 30mm radial extent, 5mm thickness, from origin
    .revolve()  # Default revolve around Y axis (global Z in XZ plane)
)

# Expected properties:
# - Volume: π * R² * h = π * 30² * 5 ≈ 14,137.17 mm³
# - Faces: 3 (top, bottom, outer curved surface)
# - Edges: 3 (top circle, bottom circle, seam)
