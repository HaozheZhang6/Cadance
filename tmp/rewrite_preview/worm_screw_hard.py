import cadquery as cq

result = (
    cq.Workplane("XY")
    .cylinder(92.7, 15.5)
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, -24.4), rotate=cq.Vector(0.0, 0.0, 0.0))
            .transformed(offset=cq.Vector(0.0, 0.0, 0.0), rotate=cq.Vector(-90.0, 0.0, 0.0))
            .center(15.5, 0.0)
            .polyline([[0.0, -4.889], [8.8, -1.686], [8.8, 1.686], [0.0, 4.889]])
            .close()
            .sweep(cq.Wire.makeHelix(25.133, 48.8, 15.5), isFrenet=True)
    )
    .edges("<Z")
    .chamfer(2.3)
    .edges(">Z")
    .chamfer(2.3)
    .faces(">Z").workplane()
    .hole(11.7)
    .faces(">Z").workplane()
    .pushPoints([(0.0, 5.85)])
    .rect(5.4, 3.24)
    .cutThruAll()
)

# Export
show_object(result)