import cadquery as cq

result = (
    cq.Workplane("XY")
    .cylinder(29.5, 3.85)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -7.3), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .center(3.85, 0.0)
            .polyline([[0.0, -1.222], [2.2, -0.421], [2.2, 0.421], [0.0, 1.222]])
            .close()
            .sweep(cq.Wire.makeHelix(3.142, 14.6, 3.85), isFrenet=True)
    )
)

# Export
show_object(result)