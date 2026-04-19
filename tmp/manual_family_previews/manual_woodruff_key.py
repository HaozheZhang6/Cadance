"""
Woodruff key (半圆键) — DIN 6888 manual parametric generator
=============================================================

Shape = circular segment × width b.
- D  = arc diameter (seat diameter cut in the shaft)
- b  = key width (thickness into hub)
- h  = key height from bottom of arc to flat top (h < D/2 → segment)

Reference: DIN 6888:1956 — Woodruff keys (Segmentkeile).
"""

import cadquery as cq
from OCP.TopoDS import (
    TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
    TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid,
)
for _cls in [TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
             TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid]:
    if not hasattr(_cls, "HashCode"):
        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub

# DIN 6888 Table 1 — (b, h, D) mm, practical subset
DIN6888 = [
    (1.5, 2.6, 7),
    (2.0, 2.6, 7),
    (2.0, 3.7, 10),
    (3.0, 5.0, 13),
    (4.0, 6.5, 16),
    (5.0, 6.5, 16),
    (5.0, 7.5, 19),
    (6.0, 9.0, 22),
    (6.0, 10.0, 25),
    (8.0, 11.0, 28),
    (10.0, 13.0, 32),
]


def build_woodruff(b, h, D, chamfer=None):
    """Circular segment of diameter D, chord gives height h; extruded length b."""
    r = D / 2.0
    if h >= D:
        raise ValueError("h must be < D")
    # Chord is at distance y_chord below center such that arc height above chord = h.
    # Segment height (sagitta) = h → y_chord = -(r - h) when h < r,
    # else y_chord = h - r above axis (segment bigger than half-circle).
    y_chord = h - r  # signed: negative if h < r, positive if h > r
    # Segment polyline: left edge of chord → arc around to right edge of chord
    half_chord = (r * r - y_chord * y_chord) ** 0.5
    profile = (
        cq.Workplane("XY")
        .moveTo(-half_chord, y_chord)
        .radiusArc((half_chord, y_chord), -r)  # lower arc (CCW)
        .lineTo(-half_chord, y_chord)
        .close()
    )
    body = profile.extrude(b)
    if chamfer:
        try:
            body = body.faces(">Z").edges().chamfer(chamfer)
            body = body.faces("<Z").edges().chamfer(chamfer)
        except Exception:
            pass
    return body


# ------ Parameters ------
B, H, D = 5.0, 7.5, 19.0   # DIN 6888 size 5×7.5×19
CHAMFER = 0.25

result = build_woodruff(B, H, D, chamfer=CHAMFER)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "manual_woodruff_key.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
