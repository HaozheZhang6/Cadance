"""
Spring pin / slotted tension pin (弹性圆柱销) — ISO 8752 / DIN 1481
==================================================================

Rolled sheet-metal tube with longitudinal slit.  Cross-section is an
annulus minus a narrow sector (the slit).  Ends are chamfered so the pin
self-guides into the bore.

Reference: ISO 8752:2009 — Spring-type straight pins, heavy duty.
"""

import math
import cadquery as cq

# (d nominal OD, s wall thickness)  ISO 8752 heavy-duty, common sizes
ISO8752 = {
    2.0:  dict(s=0.5),
    2.5:  dict(s=0.5),
    3.0:  dict(s=0.6),
    4.0:  dict(s=0.8),
    5.0:  dict(s=1.0),
    6.0:  dict(s=1.2),
    8.0:  dict(s=1.5),
    10.0: dict(s=2.0),
    12.0: dict(s=2.5),
}


def build_spring_pin(d_od, s, L, slit_w_frac=0.25, chamfer_frac=0.12):
    """d_od: nominal OD; s: wall thickness; L: length; slit_w_frac: slit width
    as fraction of wall thickness s."""
    r_out = d_od / 2.0
    r_in = r_out - s
    # slit half-angle so the arc gap is slit_w at mean radius r_mean = (r_out+r_in)/2
    slit_w = s * max(0.3, slit_w_frac)  # typical slit ~= wall thickness
    r_mean = (r_out + r_in) / 2
    half_theta = slit_w / (2 * r_mean)  # radians

    # C-shaped cross-section: outer arc (large CCW) + radial in + inner arc
    # (CW) + radial out.  Using polar angles from +half_theta .. 2π-half_theta.
    a0 = half_theta
    a1 = 2 * math.pi - half_theta

    p_out_start = (r_out * math.cos(a0), r_out * math.sin(a0))
    p_out_end   = (r_out * math.cos(a1), r_out * math.sin(a1))
    p_in_start  = (r_in  * math.cos(a0), r_in  * math.sin(a0))
    p_in_end    = (r_in  * math.cos(a1), r_in  * math.sin(a1))
    p_mid       = (-r_out, 0)   # on outer arc, angle = π
    p_in_mid    = (-r_in, 0)

    profile = (
        cq.Workplane("XY")
        .moveTo(*p_out_start)
        .threePointArc(p_mid, p_out_end)
        .lineTo(*p_in_end)
        .threePointArc(p_in_mid, p_in_start)
        .lineTo(*p_out_start)
        .close()
    )
    body = profile.extrude(L)

    # End chamfers (both top & bottom outer edges)
    cf = s * chamfer_frac + d_od * 0.05
    try:
        body = body.faces(">Z").edges().chamfer(cf)
        body = body.faces("<Z").edges().chamfer(cf)
    except Exception:
        pass  # chamfer may fail on thin C-section — non-fatal for preview
    return body


# ------ Parameters ------
D_OD, L = 6.0, 24.0
p = ISO8752[D_OD]
result = build_spring_pin(D_OD, s=p["s"], L=L)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_spring_pin_d{D_OD}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
