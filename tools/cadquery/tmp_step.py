"""
CadQuery script to generate cantilever_mount_bracket_5kg_M6x2.
tools/cadquery/.venv/bin/python3 tools/cadquery/tmp_step.py
"""

import cadquery as cq

# --- Dimensions & Parameters ---
stock_x = 120.0
stock_y = 60.0
stock_z = 12.0

# Pocket details
pocket_global_center_x = 85.0
pocket_width_x = 70.0  # Length along X
pocket_depth = 6.0
pocket_corner_r = 4.0

# Rib details
rib_height = 18.0
rib_thickness = 6.0
rib_len = 70.0
rib_x_global = 85.0
rib_y_globals = [15.0, 45.0]

# Holes
m6_dia = 6.6
m6_coords = [(20.0, 30.0), (60.0, 30.0)]
tip_hole_dia = 8.5
tip_hole_coord = (110.0, 30.0)


def to_local(abs_x, abs_y):
    """Convert Global (0..120) to Local (-60..60)."""
    return (abs_x - stock_x / 2.0, abs_y - stock_y / 2.0)


# --- Build Process ---

# 1. Base Stock (Centered on X/Y, sitting on Z=0)
result = cq.Workplane("XY").box(stock_x, stock_y, stock_z, centered=(True, True, False))

# 2. Cut Pocket (Top Down)
px, py = to_local(pocket_global_center_x, 30.0)
result = (
    result.faces(">Z")
    .workplane()
    .center(px, py)
    .rect(pocket_width_x, 60.0)  # Width Y is 60 (full width)
    .cutBlind(-pocket_depth)
)

# 3. Fillet Pocket Corners
# Fix: Use e.Center().x instead of e.centerX()
# Logic: Select vertical edges (|Z) that are roughly at the pocket X-boundaries
p_min_x = px - pocket_width_x / 2 + 0.1
p_max_x = px + pocket_width_x / 2 - 0.1

try:
    result = (
        result.edges("|Z")
        .filter(lambda e: p_min_x < e.Center().x < p_max_x)
        .fillet(pocket_corner_r)
    )
except Exception as e:
    print(f"Fillet warning: {e}")

# 4. Add Ribs (Bottom Up)
# They start at Z=0 and grow +18mm UP.
for y_g in rib_y_globals:
    rx, ry = to_local(rib_x_global, y_g)
    # Create rib as a separate object then union to avoid workplane confusion
    rib = (
        cq.Workplane("XY")
        .center(rx, ry)
        .rect(rib_len, rib_thickness)
        .extrude(rib_height)
    )
    result = result.union(rib)

# 5. Drills Holes (Through All)
# We start drilling from Z=20 (above everything) to ensure we cut through ribs if needed.
# M6 Holes
for pt in m6_coords:
    hx, hy = to_local(*pt)
    result = result.workplane(offset=20.0).center(hx, hy).hole(m6_dia)

# Tip Hole
tx, ty = to_local(*tip_hole_coord)
result = result.workplane(offset=20.0).center(tx, ty).hole(tip_hole_dia)

# Export
cq.exporters.export(result, "tmp_bracket.step")
print("Successfully generated tmp_bracket.step")
