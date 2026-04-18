import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -22.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(44.0, 22.5)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 17.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(26.0, 125.0)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -24.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(48.0, 8.4)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 15.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(30.0, 99.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[20.5, -20.0], [20.5, 20.0], [101.0, 41.0], [101.0, 19.0]])
            .close()
            .extrude(5.625, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 72.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[20.5, -20.0], [20.5, 20.0], [101.0, 41.0], [101.0, 19.0]])
            .close()
            .extrude(5.625, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 144.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[20.5, -20.0], [20.5, 20.0], [101.0, 41.0], [101.0, 19.0]])
            .close()
            .extrude(5.625, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 216.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[20.5, -20.0], [20.5, 20.0], [101.0, 41.0], [101.0, 19.0]])
            .close()
            .extrude(5.625, both=True)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(0.0, 0.0, 288.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(90.0, 0.0, 0.0))
            .polyline([[20.5, -20.0], [20.5, 20.0], [101.0, 41.0], [101.0, 19.0]])
            .close()
            .extrude(5.625, both=True)
    )
    .edges(">Z")
    .chamfer(2.2)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(112.0, 0.0, 43.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(8.0, 9.0)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(112.0, 0.0, 51.0), rotate=cq.Vector(0.0, 0.0, 0.0))
            .cylinder(82.0, 14.4)
    )
    .edges(">Z")
    .chamfer(4.8)
)

# Export
show_object(result)