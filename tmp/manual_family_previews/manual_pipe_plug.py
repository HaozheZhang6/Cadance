"""
Pipe plug (螺纹堵头) — DIN 906 manual parametric generator
===========================================================

Tapered-thread hex-socket pipe plug, no external head (flush-seating).
Taper = 1:16 per ISO 7-1 (R-thread).  Thread simplified as a bare tapered
cylinder; the hex socket is the diagnostic feature.

Reference: DIN 906:2016 — Hexagon socket pipe plugs with taper thread.
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

# (R thread designation, d_major mean, L length, s hex socket AF, t socket depth)
DIN906 = {
    "R1/8":  dict(d=10.3, L=10.0, s=5.0,  t=4.0),
    "R1/4":  dict(d=13.8, L=12.5, s=6.0,  t=5.0),
    "R3/8":  dict(d=17.3, L=14.0, s=8.0,  t=6.0),
    "R1/2":  dict(d=21.7, L=16.5, s=10.0, t=7.0),
    "R3/4":  dict(d=27.2, L=18.5, s=14.0, t=9.0),
    "R1":    dict(d=34.0, L=21.0, s=17.0, t=11.0),
}

TAPER = 1.0 / 16.0  # ISO 7-1 R-thread


def hex_socket_cut(body, s, depth, z_top):
    r = s / math.sqrt(3)
    pts = [(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i))) for i in range(6)]
    cutter = (
        cq.Workplane("XY").polyline(pts).close().extrude(depth).translate((0, 0, z_top - depth))
    )
    return body.cut(cutter)


def build_pipe_plug(d, L, s, t):
    """Tapered cylinder with hex socket.  d is mean thread OD; taper 1:16."""
    r_large = d / 2 + TAPER * L / 2
    r_small = d / 2 - TAPER * L / 2
    body = (
        cq.Workplane("XY")
        .circle(r_large)
        .workplane(offset=L)
        .circle(r_small)
        .loft(combine=True)
    )
    # Hex socket at the large (seating) end, z = L
    body = hex_socket_cut(body, s, t, z_top=L)
    # Chamfer the small (leading) end
    body = body.faces("<Z").edges("%CIRCLE").chamfer(r_small * 0.15)
    # Chamfer the large end rim
    body = body.faces(">Z").edges("%CIRCLE").chamfer(r_large * 0.05)
    return body


# ------ Parameters ------
CODE = "R1/2"
p = DIN906[CODE]
result = build_pipe_plug(**p)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os, re
    safe = re.sub(r"[^A-Za-z0-9]+", "_", CODE)
    out = os.path.join(os.path.dirname(__file__), f"manual_pipe_plug_{safe}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
