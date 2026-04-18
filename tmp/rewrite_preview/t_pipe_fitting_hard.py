import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .cylinder(46.4, 7.55)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -23.2), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(3.3, 16.4)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 23.2), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(3.3, 16.4)
    )
    .faces(">Z").workplane()
    .polarArray(11.45, 0, 360, 6)
    .hole(3.2)
    .faces("<Z").workplane()
    .polarArray(11.45, 0, 360, 6)
    .hole(3.2)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 11.65, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(23.3, 6.35)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 21.8, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(3.0, 8.8)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 12.15, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(24.3, 4.15)
    )
    .cut(
        cq.Workplane("XY")
            .cylinder(54.0, 5.35)
    )
)

# Export
show_object(result)