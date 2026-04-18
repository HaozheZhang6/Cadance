import cadquery as cq
import math


# Pipe section
outer_radius = 12.0
wall_thickness = 2.5
inner_radius = outer_radius - wall_thickness

# Elbow path
lead_length = 18.0
bend_radius = 34.0
trail_length = 18.0

# Flanges
flange_radius = 22.0
flange_thickness = 4.0
flange_overlap = 1.5
neck_radius = 15.0
neck_length = 6.0
bolt_circle_radius = 16.0
bolt_hole_radius = 2.0
bolt_count = 4

path = (
    cq.Workplane("XZ")
    .moveTo(0.0, 0.0)
    .lineTo(0.0, lead_length)
    .radiusArc((bend_radius, lead_length + bend_radius), bend_radius)
    .lineTo(bend_radius + trail_length, lead_length + bend_radius)
)

outer_profile = cq.Workplane("XY").circle(outer_radius)
inner_profile = cq.Workplane("XY").circle(inner_radius)

outer = outer_profile.sweep(path, isFrenet=True)
inner = inner_profile.sweep(path, isFrenet=True)
result = outer.cut(inner)

inlet_neck = (
    cq.Workplane("XY")
    .transformed(offset=(0.0, 0.0, -neck_length + flange_overlap))
    .cylinder(neck_length + flange_overlap, neck_radius)
)
inlet_plate = (
    cq.Workplane("XY")
    .transformed(offset=(0.0, 0.0, -neck_length - flange_thickness + flange_overlap))
    .cylinder(flange_thickness + flange_overlap, flange_radius)
)
outlet_x = bend_radius + trail_length
outlet_z = lead_length + bend_radius
outlet_neck = (
    cq.Workplane("XY")
    .transformed(
        offset=(outlet_x - flange_overlap, 0.0, outlet_z),
        rotate=(0, 90, 0),
    )
    .cylinder(neck_length + flange_overlap, neck_radius)
)
outlet_plate = (
    cq.Workplane("XY")
    .transformed(
        offset=(outlet_x + neck_length - flange_overlap, 0.0, outlet_z),
        rotate=(0, 90, 0),
    )
    .cylinder(flange_thickness + flange_overlap, flange_radius)
)
result = result.union(inlet_neck).union(inlet_plate).union(outlet_neck).union(outlet_plate)

# Extend the bore through both necks/flanges so the fitting is truly hollow end-to-end.
result = result.cut(
    cq.Workplane("XY")
    .transformed(offset=(0.0, 0.0, -neck_length - flange_thickness - 1.0))
    .cylinder(lead_length + neck_length + flange_thickness + 2.0, inner_radius)
)
result = result.cut(
    cq.Workplane("XY")
    .transformed(
        offset=(outlet_x - 1.0, 0.0, outlet_z),
        rotate=(0, 90, 0),
    )
    .cylinder(trail_length + neck_length + flange_thickness + 2.0, inner_radius)
)

for i in range(bolt_count):
    ang = math.radians(360.0 * i / bolt_count)
    x = bolt_circle_radius * math.cos(ang)
    y = bolt_circle_radius * math.sin(ang)
    result = result.cut(
        cq.Workplane("XY")
        .transformed(offset=(x, y, -neck_length - flange_thickness - 0.5))
        .cylinder(flange_thickness + 1.0, bolt_hole_radius)
    )
    y2 = bolt_circle_radius * math.cos(ang)
    z2 = lead_length + bend_radius + bolt_circle_radius * math.sin(ang)
    result = result.cut(
        cq.Workplane("YZ")
        .transformed(
            offset=(outlet_x + neck_length - 0.5, y2, z2),
            rotate=(0, 90, 0),
        )
        .cylinder(flange_thickness + 1.0, bolt_hole_radius)
    )

show_object(result)
