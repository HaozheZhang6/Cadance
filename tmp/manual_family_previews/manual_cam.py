import cadquery as cq
import math


# Disc and hub
thickness = 12.0
hub_diameter = 24.0
hub_height = 6.0
shaft_bore_diameter = 8.0

# Cam profile
base_radius = 15.0
nose_radius = 31.0
nose_angle_deg = 18.0
flank_angle_deg = 150.0
sample_count = 120

# Drive details
keyway_width = 2.0
keyway_depth = 1.5
timing_hole_diameter = 3.0
timing_hole_radius = 11.0

pts = []
for i in range(sample_count):
    ang = 2 * math.pi * i / sample_count
    deg = math.degrees(ang)
    d_nose = math.atan2(math.sin(math.radians(deg - nose_angle_deg)), math.cos(math.radians(deg - nose_angle_deg)))
    d_flank = math.atan2(math.sin(math.radians(deg - flank_angle_deg)), math.cos(math.radians(deg - flank_angle_deg)))
    lift = (nose_radius - base_radius) * math.exp(-0.5 * (d_nose / 0.34) ** 2)
    trailing = 2.8 * math.exp(-0.5 * (d_flank / 0.65) ** 2)
    flat_back = -1.4 * math.exp(-0.5 * ((math.atan2(math.sin(math.radians(deg - 280.0)), math.cos(math.radians(deg - 280.0)))) / 0.8) ** 2)
    radius = base_radius + lift + trailing + flat_back
    pts.append((round(radius * math.cos(ang), 3), round(radius * math.sin(ang), 3)))

result = cq.Workplane("XY").polyline(pts).close().extrude(thickness)
result = result.union(
    cq.Workplane("XY")
    .transformed(offset=(0, 0, thickness))
    .cylinder(hub_height, hub_diameter / 2)
)
result = result.faces(">Z").workplane().hole(shaft_bore_diameter)
result = result.cut(
    cq.Workplane("XY")
    .transformed(offset=(0, shaft_bore_diameter / 2 + keyway_depth / 2, thickness / 2))
    .box(keyway_width, keyway_depth, thickness + hub_height + 2.0)
)
result = (
    result.faces(">Z").workplane()
    .pushPoints([(timing_hole_radius, 0.0)])
    .hole(timing_hole_diameter)
)

show_object(result)
