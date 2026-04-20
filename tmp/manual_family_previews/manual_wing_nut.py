"""
Wing nut (蝶形螺母) — DIN 315 manual parametric generator
==========================================================

Central round boss with a threaded through-hole, plus two symmetric vertical
"butterfly" wings extending in ±X. Wings are thin plates with outward-tapered
trapezoidal profile in the XZ plane, extruded along Y, with large fillets at
their outer corners for the characteristic rounded wing tips.

Reference: DIN 315:2018 — Wing nuts, American / German form (German form here).

Approximate dimension table (German form). Values are catalog-grade, not
DIN-exact — we want physically plausible parameterization, not spec compliance.
Keys: d_thread (mm).
Columns:
  s   = wing span (outer tip to outer tip across ±X), mm
  D   = round boss outer diameter, mm
  h1  = boss height (= total height at boss axis), mm
  h2  = wing height (on wing plane, slightly less than h1), mm
  t   = wing plate thickness along Y, mm
  f   = wing outer-corner fillet radius, mm
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


DIN315 = {
    3:  dict(s=16, D=7,  h1=12, h2=10, t=1.6, f=2.5),
    4:  dict(s=20, D=9,  h1=15, h2=13, t=2.0, f=3.0),
    5:  dict(s=25, D=11, h1=18, h2=16, t=2.5, f=4.0),
    6:  dict(s=32, D=13, h1=21, h2=19, t=3.0, f=5.0),
    8:  dict(s=40, D=17, h1=26, h2=23, t=3.5, f=6.0),
    10: dict(s=50, D=21, h1=32, h2=28, t=4.0, f=8.0),
    12: dict(s=60, D=25, h1=38, h2=34, t=5.0, f=10.0),
    16: dict(s=80, D=33, h1=50, h2=45, t=6.0, f=13.0),
}


def build_wing_nut(d_thread, s, D, h1, h2, t, f):
    # Central boss (cylinder) centered on Z axis, base at z=0
    boss = cq.Workplane("XY").circle(D / 2).extrude(h1)
    # light top chamfer on boss
    boss = boss.faces(">Z").edges().chamfer(min(0.8, D * 0.05))

    # One wing on +X side. Profile in XZ plane (normal = Y), extrude along Y.
    # Profile: trapezoid slightly narrower at base, full-height at outer tip,
    # attaches to boss at x = D/2 * 0.9 (slight overlap for clean union).
    x_root = D / 2 * 0.9
    x_tip = s / 2
    # Taper bottom up a bit so wing looks angled upward; top goes to tip
    z_root_bot = h1 * 0.18
    z_root_top = h1 * 0.95
    z_tip_bot = h1 * 0.02
    z_tip_top = h2

    pts = [
        (x_root, z_root_bot),
        (x_tip, z_tip_bot),
        (x_tip, z_tip_top),
        (x_root, z_root_top),
    ]
    wing_plus = (
        cq.Workplane("XZ")
        .polyline(pts).close()
        .extrude(t / 2, both=True)  # total thickness t, centered on y=0
    )
    # Fillet all 4 edges of the outer tip face (rounded butterfly wing tip).
    # Radius capped by t/2 (fillet can't exceed wing half-thickness).
    f_eff = min(f * 0.6, t * 0.45)
    wing_plus = wing_plus.faces(">X").edges().fillet(f_eff)

    # Mirror to get -X wing
    wing_minus = wing_plus.mirror("YZ")

    body = boss.union(wing_plus).union(wing_minus)

    # Fillet wing-root blend into boss (edges near boss outer cylinder)
    try:
        body = body.edges("|Z").edges(cq.selectors.NearestToPointSelector((x_root, 0, h1 / 2))).fillet(min(1.5, D * 0.08))
    except Exception:
        pass  # skip if selector fails

    # Thread through-hole
    hole = cq.Workplane("XY").circle(d_thread / 2).extrude(h1 + 2).translate((0, 0, -1))
    body = body.cut(hole)

    return body


if __name__ == "__main__":
    import os
    here = os.path.dirname(__file__)
    for d in (5, 8, 12):
        p = DIN315[d]
        part = build_wing_nut(d, **p)
        out = os.path.join(here, f"manual_wing_nut_M{d}.step")
        cq.exporters.export(part, out)
        bb = part.val().BoundingBox()
        print(f"M{d}: bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
        print(f"  wrote {out}")
