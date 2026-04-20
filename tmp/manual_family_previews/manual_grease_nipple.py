"""
Grease nipple (黄油嘴/油嘴) — DIN 71412 H1 (straight) manual parametric generator
================================================================================

Straight grease nipple: threaded shank at the bottom, hex collar in the middle,
a short cylindrical neck, and a standardized 6.5 mm ball head at the top. The
ball head is the universal grease-gun coupler interface (same across thread
sizes per DIN 71412).

Reference: DIN 71412:1987-05 — Lubricating (grease) nipples, form H1 (straight).

Approximate dimension table (form H1). Keys: thread code.
Columns:
  d_thread = nominal thread major diameter, mm
  s        = hex across-flats, mm
  L        = total length (shank bottom to ball top), mm
  b        = thread shank length, mm
  hex_h    = hex collar height, mm
  d_ball   = ball head diameter, mm (standardized: 6.5)
  d_neck   = neck cylinder diameter, mm
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


DIN71412_H1 = {
    "M6x1":   dict(d_thread=6,   s=7,  b=6, hex_h=3, neck_h=1.0, d_ball=6.5, d_neck=3.5),
    "M8x1":   dict(d_thread=8,   s=9,  b=7, hex_h=4, neck_h=1.0, d_ball=6.5, d_neck=4.0),
    "M10x1":  dict(d_thread=10,  s=11, b=8, hex_h=5, neck_h=1.5, d_ball=6.5, d_neck=4.5),
    "R1/8":   dict(d_thread=9.7, s=9,  b=7, hex_h=4, neck_h=1.0, d_ball=6.5, d_neck=4.0),
    "R1/4":   dict(d_thread=13,  s=11, b=9, hex_h=5, neck_h=1.5, d_ball=6.5, d_neck=4.5),
}


def build_grease_nipple(d_thread, s, b, hex_h, neck_h, d_ball, d_neck):
    """Build grease nipple centered on Z axis, shank base at z=0.

    Total length = b (thread) + hex_h + neck_h + d_ball.
    """
    # 1. Thread shank (bottom cylinder)
    shank = cq.Workplane("XY").circle(d_thread / 2).extrude(b)
    # Bottom chamfer (thread start)
    shank = shank.faces("<Z").chamfer(d_thread * 0.08)

    # 2. Hex collar — regular hexagon, across-flats = s
    # Hex "across-corners" = s * 2 / sqrt(3)
    hex_r = s / math.sqrt(3)  # circumscribed radius
    hex_pts = [(hex_r * math.cos(math.radians(60 * i)),
                hex_r * math.sin(math.radians(60 * i))) for i in range(6)]
    hex_body = (
        cq.Workplane("XY")
        .polyline(hex_pts).close()
        .extrude(hex_h)
        .translate((0, 0, b))
    )
    # Top chamfer on hex for tool-friendly look
    hex_body = hex_body.faces(">Z").chamfer(s * 0.04)

    # 3. Neck — thin cylinder between hex and ball
    neck = (
        cq.Workplane("XY")
        .circle(d_neck / 2)
        .extrude(neck_h)
        .translate((0, 0, b + hex_h))
    )

    # 4. Ball head — sphere centered above neck, ball equator at z=neck_top+d_ball/2
    ball_z = b + hex_h + neck_h + d_ball / 2
    ball = cq.Workplane("XY").sphere(d_ball / 2).translate((0, 0, ball_z))

    body = shank.union(hex_body).union(neck).union(ball)

    # 5. Grease passage — small axial hole from bottom almost to ball center
    bore_d = d_thread * 0.35  # typical internal passage ~1/3 of thread
    bore_h = ball_z - d_ball / 4  # stops before ball valve seat
    bore = (
        cq.Workplane("XY")
        .circle(bore_d / 2)
        .extrude(bore_h)
        .translate((0, 0, -0.5))
    )
    body = body.cut(bore)

    return body


if __name__ == "__main__":
    import os
    here = os.path.dirname(__file__)
    for thread_code in ("M6x1", "M8x1", "M10x1"):
        p = DIN71412_H1[thread_code]
        part = build_grease_nipple(**p)
        safe = thread_code.replace("/", "_").replace("x", "x")
        out = os.path.join(here, f"manual_grease_nipple_{safe}.step")
        cq.exporters.export(part, out)
        bb = part.val().BoundingBox()
        print(f"{thread_code}: bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
        print(f"  wrote {out}")
