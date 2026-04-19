"""
Set screw (紧定螺钉) — ISO 4026/4027/4028/4029 manual parametric generator
==========================================================================

Hex-socket set screw with real ISO metric thread profile (borrowed from
`manual_worm_screw.py`: 60° V trapezoid swept along a `makeHelix` helix,
union'd to a root-diameter shaft).  No head.  Tip varies by variant:

  - ISO 4026 flat point : plain flat end (chamfered)
  - ISO 4027 cone point : 90°-included conical tip
  - ISO 4028 dog point  : reduced-diameter cylindrical extension
  - ISO 4029 cup point  : concave conical cavity at tip

Reference: ISO 4026/4027/4028/4029:2003 — Hexagon socket set screws.
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

# (d, s hex socket AF, t socket depth, p ISO metric coarse pitch)
SETSCREW = {
    2.0:  dict(s=0.9, t=1.5, p=0.40),
    2.5:  dict(s=1.3, t=2.0, p=0.45),
    3.0:  dict(s=1.5, t=2.0, p=0.50),
    4.0:  dict(s=2.0, t=2.5, p=0.70),
    5.0:  dict(s=2.5, t=3.0, p=0.80),
    6.0:  dict(s=3.0, t=3.5, p=1.00),
    8.0:  dict(s=4.0, t=5.0, p=1.25),
    10.0: dict(s=5.0, t=6.0, p=1.50),
    12.0: dict(s=6.0, t=8.0, p=1.75),
}


def hex_socket_cut(body, s, depth, z_top):
    r = s / math.sqrt(3)
    pts = [(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i))) for i in range(6)]
    cutter = (
        cq.Workplane("XY").polyline(pts).close().extrude(depth)
        .translate((0, 0, z_top - depth))
    )
    return body.cut(cutter)


def build_threaded_shaft_parts(d_major, pitch, length, z_offset=0.0):
    """Return (shaft_solid, thread_solid) as a 2-tuple.

    OCCT BRepAlgoAPI_Fuse silently produces a zero-volume compound when
    fusing the swept-helix thread with its root cylinder at non-zero
    z_offset.  Keep them as separate solids and assemble downstream via
    cq.Compound.makeCompound — STEP export and the VTK renderer both
    handle compounds fine.
    """
    h3 = 0.614 * pitch            # ISO external thread height
    d_minor = d_major - 2 * h3
    r_minor = d_minor / 2.0

    shaft = (
        cq.Workplane("XY")
        .workplane(offset=z_offset)
        .circle(r_minor)
        .extrude(length)
        .val()
    )

    top_w = pitch * 0.125    # narrow crest (1/8 p)
    bot_w = pitch * 0.875    # wide root  (7/8 p)
    profile = (
        cq.Workplane("XZ")
        .center(r_minor, z_offset)
        .polyline([
            (0, -bot_w / 2),
            (h3, -top_w / 2),
            (h3,  top_w / 2),
            (0,  bot_w / 2),
        ])
        .close()
    )
    helix = cq.Wire.makeHelix(
        pitch=pitch, height=length, radius=r_minor,
        center=cq.Vector(0, 0, z_offset),
    )
    thread = profile.sweep(helix, isFrenet=True).val()
    return shaft, thread


def build_set_screw(d, L, variant="flat"):
    """Body z-extent: [0, L]; z=0 = TIP end, z=L = DRIVE end."""
    p = SETSCREW[d]
    s_af, t_depth, pitch = p["s"], p["t"], p["p"]
    r_major = d / 2.0
    h3 = 0.614 * pitch
    r_minor = r_major - h3

    if variant == "cone":
        tip_h = r_major                    # 45° half-angle (90° included)
    else:
        tip_h = 0.0
    shaft_len = L - tip_h

    shaft, thread = build_threaded_shaft_parts(d, pitch, shaft_len, z_offset=tip_h)

    if variant == "cup":
        # ISO 4029 cup point: conical cavity carved into the tip face of the
        # shaft cylinder (thread doesn't reach z=0 so only shaft is affected).
        # Cut on the single shaft solid before compounding — cuts on compounds
        # don't propagate cleanly through our keep-separate fuse workaround.
        cup_od = d * 0.85
        cup_depth = d * 0.3
        cutter = (
            cq.Workplane("XY")
            .circle(cup_od / 2)
            .workplane(offset=cup_depth)
            .circle(0.05)
            .loft(combine=True)
            .val()
        )
        shaft = shaft.cut(cutter)

    parts = [shaft, thread]

    if variant == "cone":
        # Truncated cone from r_minor (apex) to r_major (base) over [0, tip_h].
        parts.append(cq.Solid.makeCone(r_minor, r_major, tip_h))
    elif variant == "dog":
        # ISO 4028 full-dog: unthreaded reduced-dia cylinder BELOW the thread
        dp = d * 0.55
        lp = d * 0.5
        dog_solid = cq.Workplane("XY").circle(dp / 2).extrude(-lp).val()
        parts.append(dog_solid)

    body = cq.Workplane("XY").newObject([cq.Compound.makeCompound(parts)])

    # Hex drive socket on top (z=L)
    body = hex_socket_cut(body, s_af, t_depth, z_top=L)

    return body


# ------ Parameters ------
D, L = 6.0, 16.0
VARIANTS = ["flat", "cone", "dog", "cup"]

results = {v: build_set_screw(D, L, v) for v in VARIANTS}

try:
    for v, r in results.items():
        show_object(r, name=f"set_screw_{v}")  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    for v, r in results.items():
        out = os.path.join(os.path.dirname(__file__), f"manual_set_screw_{v}.step")
        cq.exporters.export(r, out)
        print(f"wrote {out}")
