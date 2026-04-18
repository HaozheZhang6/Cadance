import cadquery as cq


# Main dimensions
flange_thickness = 12.0
flange_radius = 34.0
raised_face_thickness = 2.0
raised_face_radius = 24.0
neck_height = 18.0
neck_radius = 14.0
bore_diameter = 12.0

# Bolt pattern
bolt_circle_radius = 26.0
bolt_count = 8
bolt_hole_diameter = 4.8

# Edge finish
bottom_chamfer = 1.2
top_chamfer = 0.8

flange = cq.Workplane("XY").cylinder(flange_thickness, flange_radius)
raised_face = cq.Workplane("XY").transformed(offset=(0, 0, flange_thickness)).cylinder(raised_face_thickness, raised_face_radius)
neck = cq.Workplane("XY").transformed(offset=(0, 0, flange_thickness + raised_face_thickness)).cylinder(neck_height, neck_radius)

result = flange.union(raised_face).union(neck)
result = (
    result.faces(">Z").workplane().hole(bore_diameter)
    .faces(">Z").workplane(offset=-(raised_face_thickness + neck_height - raised_face_thickness)).polarArray(bolt_circle_radius, 0, 360, bolt_count).hole(bolt_hole_diameter)
    .faces("<Z").chamfer(bottom_chamfer)
    .faces(">Z").chamfer(top_chamfer)
)

show_object(result)
