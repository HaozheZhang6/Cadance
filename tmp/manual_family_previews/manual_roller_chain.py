"""
ISO 606 Roller Chain (simplex) — manual parametric generator
============================================================

Produces N_links of a short-pitch roller chain pairing directly with
`sprocket` / `double_simplex_sprocket` (同一 ISO 606 chain code).

Each link = 2 side plates (stadium outline, same level) + 2 pins across both
plates + 2 bushings + 2 rollers. Inner vs outer links alternate along X:
- outer link: 2 outer plates at ±(b1/2 + plate_t); pins press-fit into them
- inner link: 2 inner plates at ±b1/2; bushings press-fit into them, rollers
  rotate freely on bushings

Reference: ISO 606:2004 — Short-pitch transmission precision roller chains.
Table 2: chain numbers 06B-1 .. 20B-1.
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

# ISO 606 Table 2 — (p, d1 roller, b1 inner width, d2 pin, h2 plate depth)
ISO606 = {
    "06B-1": dict(p=9.525,  d1=6.35,  b1=5.72,  d2=3.28,  h2=8.2),
    "08B-1": dict(p=12.70,  d1=8.51,  b1=7.75,  d2=4.45,  h2=11.8),
    "10B-1": dict(p=15.875, d1=10.16, b1=9.65,  d2=5.08,  h2=14.7),
    "12B-1": dict(p=19.05,  d1=12.07, b1=11.68, d2=5.72,  h2=16.0),
    "16B-1": dict(p=25.40,  d1=15.88, b1=17.02, d2=8.28,  h2=21.0),
    "20B-1": dict(p=31.75,  d1=19.05, b1=19.56, d2=10.19, h2=26.4),
}


def plate(pitch, h2, thickness):
    """Stadium-shaped chain plate (two rounded ends of radius h2/2 joined by
    straight top/bottom). Center of the two pin-holes at (0,0) and (pitch,0).
    For 'waisted' plate style, swap to a two-arc concave mid-section later."""
    r = h2 / 2.0
    wp = (
        cq.Workplane("XY")
        .moveTo(0, r)
        .lineTo(pitch, r)
        .radiusArc((pitch, -r), r)
        .lineTo(0, -r)
        .radiusArc((0, r), r)
        .close()
        .extrude(thickness)
    )
    return wp


def build_link(params, x_off, outer=True):
    """One link (outer or inner) centred in Z at 0."""
    p = params["p"]; d1 = params["d1"]; b1 = params["b1"]
    d2 = params["d2"]; h2 = params["h2"]
    plate_t = max(1.0, round(d2 * 0.45, 2))  # plate thickness ≈ 0.45 · pin d

    # Plate Z offsets
    if outer:
        z_top = b1 / 2 + plate_t              # outer plate top face
        z_bot = -b1 / 2 - plate_t
    else:
        z_top = b1 / 2                         # inner plate top face
        z_bot = -b1 / 2

    # Two plates (top & bottom)
    plate_top = plate(p, h2, plate_t).translate((x_off, 0, z_top - plate_t))
    plate_bot = plate(p, h2, plate_t).translate((x_off, 0, z_bot))

    body = plate_top.union(plate_bot)

    # --- Cut pin holes through both plates ---
    # Hole dia slightly larger than pin (clearance)
    hole_d = d2 * 1.02
    for hx in (0, p):
        hole = (
            cq.Workplane("XY")
            .center(x_off + hx, 0)
            .circle(hole_d / 2)
            .extrude(z_top + 1)
            .translate((0, 0, z_bot - 0.5))
        )
        body = body.cut(hole)

    # --- Pins (only on outer links; press-fit into outer plates) ---
    # --- Bushings + rollers (only on inner links) ---
    parts = [body]
    for hx in (0, p):
        if outer:
            pin_len = (z_top) * 2  # from -z_top to +z_top (full through)
            pin = (
                cq.Workplane("XY")
                .center(x_off + hx, 0)
                .circle(d2 / 2)
                .extrude(pin_len)
                .translate((0, 0, -pin_len / 2))
            )
            parts.append(pin)
        else:
            # Bushing: OD = d1 * 0.82 (sleeve under roller), ID = d2*1.02
            bush_od = d1 * 0.82
            bushing = (
                cq.Workplane("XY")
                .center(x_off + hx, 0)
                .circle(bush_od / 2)
                .circle(d2 * 1.02 / 2)
                .extrude(b1)
                .translate((0, 0, -b1 / 2))
            )
            # Roller: OD = d1, ID = bush_od*1.02, length = b1 * 0.95
            roller = (
                cq.Workplane("XY")
                .center(x_off + hx, 0)
                .circle(d1 / 2)
                .circle(bush_od * 1.02 / 2)
                .extrude(b1 * 0.95)
                .translate((0, 0, -b1 * 0.95 / 2))
            )
            parts.append(bushing)
            parts.append(roller)

    result = parts[0]
    for extra in parts[1:]:
        result = result.union(extra)
    return result


def build_chain(chain_code="08B-1", n_links=8):
    params = ISO606[chain_code]
    p = params["p"]
    links = []
    for i in range(n_links):
        outer = (i % 2 == 0)
        x_off = i * p
        links.append(build_link(params, x_off=x_off, outer=outer))
    chain = links[0]
    for lk in links[1:]:
        chain = chain.union(lk)
    return chain


# ------ Parameters ------
CHAIN_CODE = "08B-1"
N_LINKS = 3

result = build_chain(CHAIN_CODE, N_LINKS)

# CQ-Editor preview
try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

# Export STEP for visual check
if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_roller_chain_{CHAIN_CODE}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
