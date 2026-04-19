"""
Slotted / Castle nut (开槽螺母) — DIN 935 manual parametric generator
====================================================================

Hex base + cylindrical crown with 6 radial castellation slots (at 60°).
In this script the 6 openings are produced by 3 diametrical through-cuts
rotated 60° apart.  Thread bore simplified as plain hole.

Reference: DIN 935-1:2008 — Hexagon castle nuts.
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

# (d_thread, s_across_flats, m_total_height, n_crown_height, e_slot_width)
DIN935 = {
    6:  dict(s=10.0, m=10.0, n=3.0, e=2.8),
    8:  dict(s=13.0, m=13.0, n=4.0, e=3.5),
    10: dict(s=17.0, m=15.0, n=4.5, e=3.5),
    12: dict(s=19.0, m=18.0, n=5.5, e=4.5),
    16: dict(s=24.0, m=22.0, n=6.0, e=5.5),
    20: dict(s=30.0, m=26.0, n=7.0, e=7.0),
    24: dict(s=36.0, m=31.0, n=8.0, e=7.0),
}


def build_slotted_nut(d_thread, s, m, n, e):
    """d_thread = bore, s = across-flats, m = total height (hex + crown = m + n),
    n = crown height above hex, e = slot width."""
    # Hex base
    r = s / math.sqrt(3)  # circumradius
    hex_pts = [
        (r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]
    body = cq.Workplane("XY").polyline(hex_pts).close().extrude(m - n)

    # Crown: cylinder of diameter ≈ s (circumscribed to hex minus some chamfer)
    crown_r = s / 2 * 0.98
    crown = (
        cq.Workplane("XY")
        .circle(crown_r)
        .extrude(n)
        .translate((0, 0, m - n))
    )
    body = body.union(crown)

    # 3 diametrical slots (through-cut) rotated at 60° → 6 openings
    slot_depth = n * 0.75
    slot_len = s * 1.2  # through the full crown width
    for k in range(3):
        ang = k * 60
        slot = (
            cq.Workplane("XY")
            .center(0, 0)
            .rect(slot_len, e)
            .extrude(slot_depth)
            .rotate((0, 0, 0), (0, 0, 1), ang)
            .translate((0, 0, m - slot_depth))
        )
        body = body.cut(slot)

    # Thread bore (simplified)
    hole = (
        cq.Workplane("XY")
        .circle(d_thread / 2)
        .extrude(m + 1)
        .translate((0, 0, -0.5))
    )
    body = body.cut(hole)

    # Top chamfer on crown rim
    body = body.faces(">Z").edges("%CIRCLE").chamfer(0.4)
    # Bottom chamfer on hex
    body = body.faces("<Z").edges().chamfer(0.3)

    return body


# ------ Parameters ------
D_THREAD = 12
p = DIN935[D_THREAD]
result = build_slotted_nut(D_THREAD, **p)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_slotted_nut_M{D_THREAD}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
