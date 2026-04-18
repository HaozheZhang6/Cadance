import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -14.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(28.0, 14.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 9.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(18.0, 62.5)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -16.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(32.0, 4.5)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 7.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(22.0, 47.5)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[12.0, -12.0], [12.0, 12.0], [49.5, 25.0], [49.5, 11.0]])
            .close()
            .extrude(3.5, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 120.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[12.0, -12.0], [12.0, 12.0], [49.5, 25.0], [49.5, 11.0]])
            .close()
            .extrude(3.5, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 240.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[12.0, -12.0], [12.0, 12.0], [49.5, 25.0], [49.5, 11.0]])
            .close()
            .extrude(3.5, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(55.0, 0.0, 27.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(8.0, 6.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(55.0, 0.0, 35.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(57.0, 9.6)
    )
    .edges(">Z")
    .chamfer(3.2)
)

# Export
show_object(result)