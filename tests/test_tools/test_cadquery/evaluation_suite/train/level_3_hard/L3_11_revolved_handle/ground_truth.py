"""Ground truth CadQuery code for L3_11: Revolved Handle.

This creates a handle shape by revolving an L-shaped profile.

Design decisions:
- L-profile: vertical segment 25mm tall x 8mm wide
- Horizontal segment: 15mm outward x 8mm tall at base
- Revolve around Z axis to create ring/handle shape
- Creates a shape like a pot lid handle
"""

import cadquery as cq

# Create L-shaped profile and revolve
# Profile is in XZ plane (X = radial, Z = height)
# Start at inner radius, build L shape outward and up
inner_radius = 10  # Distance from rotation axis to start of profile

# L-shape profile points (in XZ plane)
profile_points = [
    (inner_radius + 15, 0),  # Base extends outward 15mm
    (inner_radius + 15, 8),  # Up 8mm
    (inner_radius + 8, 8),  # Inward to vertical segment
    (inner_radius + 8, 25),  # Up to top (total height 25mm)
    (inner_radius, 25),  # Inward 8mm to close
]

result = (
    cq.Workplane("XZ")
    .moveTo(inner_radius, 0)  # Start at inner radius, Z=0
    .polyline(profile_points)  # Draw L-shape
    .close()  # Close back to start
    .revolve()  # Default revolve around Y axis (global Z)
)

# Expected properties:
# - Complex volume from L-profile revolution
# - Multiple faces from the revolved profile corners
# - Creates ring-shaped handle
