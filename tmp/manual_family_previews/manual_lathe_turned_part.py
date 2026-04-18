import cadquery as cq


# Diameters / lengths
flange_radius = 26.0
flange_length = 8.0
body_radius = 18.0
body_length = 20.0
shoulder_radius = 13.0
shoulder_length = 14.0
thread_land_radius = 10.5
thread_land_length = 10.0
nose_radius = 8.0
nose_length = 12.0

# Features
relief_width = 2.0
relief_depth = 1.2
bore_radius = 4.5
counterbore_radius = 7.5
counterbore_depth = 12.0
front_chamfer = 1.5

z1 = flange_length
z2 = z1 + body_length
z3 = z2 + shoulder_length
z4 = z3 + thread_land_length
z5 = z4 + nose_length

profile = (
    cq.Workplane("XZ")
    .moveTo(0.0, 0.0)
    .lineTo(flange_radius, 0.0)
    .lineTo(flange_radius, z1)
    .lineTo(body_radius, z1 + 2.0)
    .lineTo(body_radius, z2)
    .lineTo(shoulder_radius, z2 + 2.0)
    .lineTo(shoulder_radius, z3 - relief_width)
    .lineTo(shoulder_radius - relief_depth, z3 - relief_width)
    .lineTo(shoulder_radius - relief_depth, z3)
    .lineTo(thread_land_radius, z3 + 2.0)
    .lineTo(thread_land_radius, z4)
    .lineTo(nose_radius, z4 + 2.0)
    .lineTo(nose_radius, z5)
    .lineTo(0.0, z5)
    .close()
)

result = cq.Workplane("XY", origin=(0, 0, 0))
result = profile.revolve(360, (0, 0), (0, 1))
result = result.faces(">Z").workplane().hole(bore_radius * 2)
result = result.faces("<Z").workplane().hole(counterbore_radius * 2, counterbore_depth)
result = result.faces(">Z").chamfer(front_chamfer)

show_object(result)
