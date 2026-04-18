import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .cylinder(203.9, 29.4)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -101.95), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(10.2, 51.75)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 101.95), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(10.2, 51.75)
    )
    .faces(">Z").workplane()
    .polarArray(38.95, 0, 360, 8)
    .hole(7.1)
    .faces("<Z").workplane()
    .polarArray(38.95, 0, 360, 8)
    .hole(7.1)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 33.0, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(66.0, 16.4)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 61.75, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(8.5, 21.15)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 33.5, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(67.0, 9.2)
    )
    .cut(
        cq.Workplane("XY")
            .cylinder(225.3, 22.2)
    )
)

# Export
show_object(result)