"""
Star knob (星形/五角把手) — DIN 6336 manual parametric generator
================================================================

N-lobed smooth star knob (typically 3, 5, or 6 lobes) with a central threaded
through-bush. Profile is the UNION of a central disc (radius R_inner) plus N
large circles (radius lobe_r) placed at radius R_inner from center. This gives
a cloud-like smooth flower silhouette, NOT a pointy star — matches DIN 6336.

Reference: DIN 6336 — Stern- / Kreuzgriffe (star / cross grips). Typical
catalog families: KIPP K0155, HALDER 24600.

Approximate dimension table (DIN 6336, 5-lobe variant is standard; values
from KIPP K0155 catalog, not DIN-exact).
Keys: d_thread (mm).
Columns:
  d1     = overall tip-to-tip outer diameter, mm
  h1     = total knob height, mm
  N      = number of lobes (3/5/6); 5 is DIN 6336 default
  bush_h = threaded bush height protruding below the knob base, mm
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


DIN6336 = {
    5:  dict(d1=32,  h1=14, N=5, bush_h=6),
    6:  dict(d1=40,  h1=18, N=5, bush_h=8),
    8:  dict(d1=50,  h1=22, N=5, bush_h=10),
    10: dict(d1=63,  h1=28, N=5, bush_h=12),
    12: dict(d1=80,  h1=35, N=5, bush_h=15),
    16: dict(d1=100, h1=44, N=5, bush_h=18),
}


def build_star_knob(d_thread, d1, h1, N, bush_h):
    """Build star knob centered at origin, base at z=0."""
    R_outer = d1 / 2
    # Lobe radius chosen so lobes overlap smoothly (~55% of R_outer gives DIN look).
    lobe_r = R_outer * 0.55
    R_inner = R_outer - lobe_r  # center of each lobe circle from origin

    # Top-view profile: union of central disc + N lobe circles.
    # Each solid must be built+unioned separately; a single Workplane
    # with multiple circles extrudes them as independent solids, not a union.
    knob_body = cq.Workplane("XY").circle(R_inner + 0.5).extrude(h1)
    for i in range(N):
        ang = 2 * math.pi * i / N
        cx = R_inner * math.cos(ang)
        cy = R_inner * math.sin(ang)
        lobe = cq.Workplane("XY").moveTo(cx, cy).circle(lobe_r).extrude(h1)
        knob_body = knob_body.union(lobe)

    # Rounded ergonomic fillet on all top+bottom edges.
    fillet_r = min(h1 * 0.25, lobe_r * 0.35)
    knob_body = knob_body.edges("|Z or %CIRCLE").fillet(fillet_r) \
        if False else knob_body  # skip — edge selector too broad; do top/bottom separately

    # Apply fillets to top face edges, then bottom face edges.
    for selector in (">Z", "<Z"):
        try:
            knob_body = knob_body.faces(selector).edges().fillet(fillet_r)
        except Exception:
            pass

    # Threaded bush protruding below base (flange-like).
    bush_d = d_thread * 2.0  # bush OD ~ 2x thread diameter
    bush = cq.Workplane("XY").circle(bush_d / 2).extrude(-bush_h).translate((0, 0, 0))

    body = knob_body.union(bush)

    # Thread through-hole.
    hole_h = h1 + bush_h + 2
    hole = cq.Workplane("XY").circle(d_thread / 2).extrude(hole_h).translate((0, 0, -bush_h - 1))
    body = body.cut(hole)

    return body


if __name__ == "__main__":
    import os
    here = os.path.dirname(__file__)
    for d in (5, 10, 16):
        p = DIN6336[d]
        part = build_star_knob(d, **p)
        out = os.path.join(here, f"manual_star_knob_M{d}.step")
        cq.exporters.export(part, out)
        bb = part.val().BoundingBox()
        print(f"M{d} N={p['N']}: bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
        print(f"  wrote {out}")

    # Extra: test N=3 and N=6 variants at M10
    for N in (3, 6):
        p = dict(DIN6336[10])
        p["N"] = N
        part = build_star_knob(10, **p)
        out = os.path.join(here, f"manual_star_knob_M10_N{N}.step")
        cq.exporters.export(part, out)
        bb = part.val().BoundingBox()
        print(f"M10 N={N}: bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
