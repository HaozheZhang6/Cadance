import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -19.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(38.0, 19.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 12.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(24.0, 100.0)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -21.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(42.0, 7.0)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 10.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(28.0, 78.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[17.0, -17.0], [17.0, 17.0], [80.0, 34.0], [80.0, 14.0]])
            .close()
            .extrude(4.75, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 120.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[17.0, -17.0], [17.0, 17.0], [80.0, 34.0], [80.0, 14.0]])
            .close()
            .extrude(4.75, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 240.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[17.0, -17.0], [17.0, 17.0], [80.0, 34.0], [80.0, 14.0]])
            .close()
            .extrude(4.75, both=True)
    )
    .edges(">Z")
    .chamfer(2.3)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(89.0, 0.0, 36.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(8.0, 7.5)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(89.0, 0.0, 44.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(72.0, 12.0)
    )
    .edges(">Z")
    .chamfer(4.0)
)

# Export
show_object(result)