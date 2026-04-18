import cadquery as cq

result = (
    cq.Workplane("XY")
    .union(
        cq.Workplane("XY")
            .cylinder(179.2, 24.55)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 27.4, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(54.8, 20.0)
    )
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 27.9, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .cylinder(55.8, 15.6)
    )
    .cut(
        cq.Workplane("XY")
            .cylinder(181.2, 20.15)
    )
)

# Export
show_object(result)