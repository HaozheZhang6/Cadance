"""
Flange nut (法兰螺母) — DIN 6923 / ISO 4161 manual parametric generator
========================================================================

Hex body fused with an integral circular flange at the base.  The flange
has a flat top ring and a chamfered/conical transition from hex to flange
outer diameter.  Thread bore simplified.

Reference: DIN 6923:2015 — Hexagon nuts with flange.
"""

import math
import cadquery as cq
from OCP.TopoDS import (
    TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
    TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid,
)
for _cls in [TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
             TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid]:
    if not hasattr(_cls, "HashCode"):
        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub

# (d_thread, s hex AF, m total height, dc flange OD, c flange thickness)
DIN6923 = {
    5:  dict(s=8.0,  m=5.0,  dc=11.8, c=1.0),
    6:  dict(s=10.0, m=6.0,  dc=14.2, c=1.1),
    8:  dict(s=13.0, m=8.0,  dc=17.9, c=1.2),
    10: dict(s=15.0, m=10.0, dc=21.8, c=1.5),
    12: dict(s=18.0, m=12.0, dc=26.0, c=1.8),
    16: dict(s=24.0, m=16.0, dc=34.5, c=2.5),
}


def build_flange_nut(d_thread, s, m, dc, c):
    # Flange disc (bottom)
    flange = cq.Workplane("XY").circle(dc / 2).extrude(c)

    # Conical transition from flange OD to hex across-corners
    e = s * 2 / math.sqrt(3)  # hex across corners
    trans_h = (dc - e) / 2 * 0.5
    trans = (
        cq.Workplane("XY")
        .circle(dc / 2)
        .workplane(offset=trans_h)
        .circle(e / 2)
        .loft(combine=True)
        .translate((0, 0, c))
    )

    # Hex body on top of transition
    r = s / math.sqrt(3)
    hex_pts = [
        (r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]
    hex_h = m - c - trans_h
    hex_body = (
        cq.Workplane("XY")
        .polyline(hex_pts).close()
        .extrude(hex_h)
        .translate((0, 0, c + trans_h))
    )

    body = flange.union(trans).union(hex_body)

    # Top chamfer on hex
    body = body.faces(">Z").edges().chamfer(s * 0.05)

    # Thread bore
    hole = (
        cq.Workplane("XY")
        .circle(d_thread / 2)
        .extrude(m + 1)
        .translate((0, 0, -0.5))
    )
    body = body.cut(hole)

    return body


# ------ Parameters ------
D_THREAD = 10
p = DIN6923[D_THREAD]
result = build_flange_nut(D_THREAD, **p)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_flange_nut_M{D_THREAD}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
