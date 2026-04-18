import cadquery as cq

# Parameters (mm)
length = 120.0
width = 80.0
thickness = 4.0

hole_d = 6.6
hole_depth = 4.0

slot_len = 12.0
slot_w = 6.0

rib_len = 70.0
rib_thk = 4.0
rib_h = 20.0


# Coordinate conversion:
# Ops positions are given in a 0..length / 0..width system.
# CadQuery box is centered at origin, so shift by (-length/2, -width/2).
def to_centered_xy(x, y):
    return (x - length / 2.0, y - width / 2.0)


# Feature locations (mm) in absolute (0..length / 0..width) coordinates
hole_positions_abs = [(30.0, 20.0), (90.0, 20.0), (30.0, 60.0), (90.0, 60.0)]
slot_main_abs = [(6.0, 20.0), (114.0, 20.0)]
slot_lip_abs = [(6.0, 60.0), (114.0, 60.0)]
rib1_center_abs = (60.0, 25.0)
rib2_center_abs = (60.0, 55.0)

# Convert to centered coordinates for standard face-centered workplanes
hole_positions = [to_centered_xy(x, y) for x, y in hole_positions_abs]
slot_main_positions = [to_centered_xy(x, y) for x, y in slot_main_abs]
slot_lip_positions = [to_centered_xy(x, y) for x, y in slot_lip_abs]
rib1_center = to_centered_xy(*rib1_center_abs)
rib2_center = to_centered_xy(*rib2_center_abs)

# 1) Stock geometry
result = cq.Workplane("XY").box(length, width, thickness)

# 2-3) Top face: mounting holes
result = (
    result.faces(">Z")
    .workplane()
    .pushPoints(hole_positions)
    .hole(hole_d, depth=hole_depth)
)

# 4-5) Main bend relief slots (along Y => angle=90 deg), cut through
result = (
    result.faces(">Z")
    .workplane()
    .pushPoints(slot_main_positions)
    .slot2D(slot_len, slot_w, angle=90.0)
    .cutThruAll()
)

# 6-7) Lip bend relief slots (along Y), cut through
result = (
    result.faces(">Z")
    .workplane()
    .pushPoints(slot_lip_positions)
    .slot2D(slot_len, slot_w, angle=90.0)
    .cutThruAll()
)

# 8-12) Ribs on top face (two rectangles), extrude upward
# Root cause: rib coordinates were in absolute space but applied on a centered workplane
# (or mixed with origin shifting), placing rib sketches off the plate -> disconnected solids.
# Fix: use centered coordinates on the default face-centered workplane.
result = (
    result.faces(">Z")
    .workplane()
    .center(rib1_center[0], rib1_center[1])
    .rect(rib_len, rib_thk, centered=True)
    .extrude(rib_h)
)

result = (
    result.faces(">Z")
    .workplane()
    .center(rib2_center[0], rib2_center[1])
    .rect(rib_len, rib_thk, centered=True)
    .extrude(rib_h)
)
