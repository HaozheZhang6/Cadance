import cadquery as cq


def tapered_threaded_end(
    start_z: float,
    length: float,
    shoulder_radius: float,
    major_radius: float,
    minor_radius: float,
    pitch: float,
    groove_depth: float,
):
    taper = (
        cq.Workplane("XY")
        .workplane(offset=start_z)
        .circle(major_radius)
        .workplane(offset=length)
        .circle(minor_radius)
        .loft(combine=True)
    )

    helix_r = major_radius - groove_depth / 2
    turns = max(5, int(length / pitch) + 1)
    result = taper
    for i in range(turns):
        z = start_z + i * pitch * 0.78 + pitch * 0.18
        ring_major = major_radius - (major_radius - minor_radius) * min((i * pitch * 0.78) / length, 1.0)
        groove = (
            cq.Workplane("XY")
            .transformed(offset=(0, 0, z))
            .cylinder(pitch * 0.34, max(ring_major - groove_depth, shoulder_radius * 0.68))
        )
        result = result.cut(groove)
    return result


# Overall fitting
hex_diameter = 30.0
hex_height = 16.0
center_bore_diameter = 7.0

# Upper male thread
upper_shoulder_radius = 9.5
upper_shoulder_length = 4.0
upper_thread_start = hex_height
upper_thread_length = 14.0
upper_major_radius = 8.5
upper_minor_radius = 7.7
upper_pitch = 1.8
upper_groove_depth = 0.7

# Lower male thread
lower_shoulder_radius = 8.5
lower_shoulder_length = 4.0
lower_thread_start = -16.0
lower_thread_length = 12.0
lower_major_radius = 7.6
lower_minor_radius = 6.9
lower_pitch = 1.7
lower_groove_depth = 0.65

body = cq.Workplane("XY").polygon(6, hex_diameter).extrude(hex_height)

upper_shoulder = (
    cq.Workplane("XY")
    .transformed(offset=(0, 0, hex_height - 0.8))
    .cylinder(upper_shoulder_length, upper_shoulder_radius)
)
upper_thread = tapered_threaded_end(
    start_z=upper_thread_start,
    length=upper_thread_length,
    shoulder_radius=upper_shoulder_radius,
    major_radius=upper_major_radius,
    minor_radius=upper_minor_radius,
    pitch=upper_pitch,
    groove_depth=upper_groove_depth,
)

lower_shoulder = (
    cq.Workplane("XY")
    .transformed(offset=(0, 0, lower_thread_start + lower_thread_length - lower_shoulder_length + 0.8))
    .cylinder(lower_shoulder_length, lower_shoulder_radius)
)
lower_thread = tapered_threaded_end(
    start_z=lower_thread_start,
    length=lower_thread_length,
    shoulder_radius=lower_shoulder_radius,
    major_radius=lower_major_radius,
    minor_radius=lower_minor_radius,
    pitch=lower_pitch,
    groove_depth=lower_groove_depth,
)

result = body.union(upper_shoulder).union(upper_thread).union(lower_shoulder).union(lower_thread)
result = (
    result.faces(">Z").workplane().hole(center_bore_diameter)
    .faces("<Z").workplane().hole(center_bore_diameter)
)

show_object(result)
