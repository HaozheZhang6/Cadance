import cadquery as cq
from cadquery.occ_impl.geom import Vector
from cadquery.occ_impl.shapes import Solid

block_x = 80.0
block_y = 50.0
block_z = 36.0

x_bore_r = 5.0
z_bore_r = 4.0

result = cq.Workplane("XY").box(block_x, block_y, block_z)

# X: full through-hole (cylinder length > block_x so booleans don’t leave slivers at faces)
result = result.cut(
    cq.Workplane("YZ").cylinder(block_x + 2.0, x_bore_r)
)

# Z: blind hole from +Z top face, depth = half block.
# Start slightly above the top face and cut downward along -Z for stable booleans.
z_blind_depth = block_z / 2.0
z_fudge = 0.5
top_z = block_z / 2.0
hole_z = Solid.makeCylinder(
    z_bore_r,
    z_blind_depth + z_fudge,
    Vector(0, 0, top_z + z_fudge),
    Vector(0, 0, -1),
)
result = result.cut(hole_z)

show_object(result)
