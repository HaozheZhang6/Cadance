import cadquery as cq

result = (
    cq.Workplane("XY")
    .cylinder(27.5, 2.65)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -6.7), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .center(2.65, 0.0)
            .polyline([[0.0, -1.222], [2.2, -0.421], [2.2, 0.421], [0.0, 1.222]])
            .close()
            .sweep(cq.Wire.makeHelix(12.566, 13.4, 2.65), isFrenet=True)
    )
    .edges("<Z")
    .chamfer(0.6)
    .edges(">Z")
    .chamfer(0.6)
)

# Export
show_object(result)