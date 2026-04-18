import cadquery as cq


# Core dimensions
hub_radius = 11.0
hub_height = 13.0
bore_diameter = 6.0

# Nose / spinner
spinner_base_radius = hub_radius * 0.92
spinner_tip_radius = 1.5
spinner_height = 7.0

# Blade planform
blade_count = 3
blade_root_thickness = 3.6
blade_root_chord = 24.0
blade_tip_chord = 10.0
blade_length = 42.0
blade_root_offset = hub_radius * 0.35
blade_z_offset = hub_height * 0.42
blade_pitch_y = 16.0
blade_pitch_x = 18.0

hub = (
    cq.Workplane("XY")
    .cylinder(hub_height, hub_radius)
    .faces(">Z").workplane()
    .hole(bore_diameter)
)

spinner = (
    cq.Workplane("XY")
    .transformed(offset=(0, 0, hub_height))
    .circle(spinner_base_radius)
    .workplane(offset=spinner_height)
    .circle(spinner_tip_radius)
    .loft(combine=True)
)

result = hub.union(spinner)

single_blade = (
    cq.Workplane("XY")
    .polyline([
        (0.0, -blade_root_chord / 2),
        (0.0, blade_root_chord / 2),
        (blade_length * 0.72, blade_tip_chord * 0.55),
        (blade_length, 0.0),
        (blade_length * 0.72, -blade_tip_chord * 0.55),
    ])
    .close()
    .extrude(blade_root_thickness)
    .translate((blade_root_offset, 0, blade_z_offset))
    .rotate((0, 0, 0), (0, 1, 0), blade_pitch_y)
    .rotate((0, 0, 0), (1, 0, 0), blade_pitch_x)
)

for i in range(blade_count):
    result = result.union(single_blade.rotate((0, 0, 0), (0, 0, 1), i * 360 / blade_count))

show_object(result)
