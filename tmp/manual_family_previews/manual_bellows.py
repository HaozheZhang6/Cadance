import cadquery as cq
import math


# Through path
bore_radius = 10.0
wall_thickness = 2.2
root_radius = 19.0
crest_radius = 26.0

# Axial layout
overall_length = 54.0
flange_thickness = 6.0
neck_length = 4.0
convolution_pitch = 6.0
convolution_count = 5

# Flanges
flange_radius = 38.0
raised_face_radius = 26.0
bolt_circle_radius = 29.0
bolt_hole_radius = 2.2
bolt_count = 6

z0 = flange_thickness
z1 = z0 + neck_length

outer_points = [
    (flange_radius, 0.0),
    (flange_radius, flange_thickness),
    (raised_face_radius, flange_thickness),
    (raised_face_radius, z1),
]

for i in range(convolution_count):
    base = z1 + i * convolution_pitch
    outer_points.extend([
        (root_radius + wall_thickness, base + 1.0),
        (crest_radius + wall_thickness, base + 3.0),
        (root_radius + wall_thickness, base + 5.0),
    ])

z2 = z1 + convolution_count * convolution_pitch
outer_points.extend([
    (raised_face_radius, z2 + 1.0),
    (raised_face_radius, overall_length - flange_thickness),
    (flange_radius, overall_length - flange_thickness),
    (flange_radius, overall_length),
    (bore_radius, overall_length),
    (bore_radius, 0.0),
])

inner_points = [
    (bore_radius, 0.0),
    (bore_radius, overall_length),
    (0.0, overall_length),
    (0.0, 0.0),
]

outer = cq.Workplane("XZ").polyline(outer_points).close().revolve(360, (0, 0), (0, 1))
inner = cq.Workplane("XZ").polyline(inner_points).close().revolve(360, (0, 0), (0, 1))
result = outer.cut(inner)

for z in (flange_thickness / 2, overall_length - flange_thickness / 2):
    for i in range(bolt_count):
        ang = math.radians(360.0 * i / bolt_count)
        x = bolt_circle_radius * math.cos(ang)
        y = bolt_circle_radius * math.sin(ang)
        result = result.cut(
            cq.Workplane("XY")
            .transformed(offset=(x, y, z - flange_thickness / 2))
            .cylinder(flange_thickness + 1.0, bolt_hole_radius)
        )

show_object(result)
