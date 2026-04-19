"""
Spline shaft (单体花键轴) — DIN 5480 involute spline, manual generator
========================================================================

External involute spline, 30° pressure angle.  One tooth profile built from
the involute curve (base circle → tip circle), then polar-arrayed z times
into a closed CCW outline, then extruded.

Geometry per DIN 5480 external teeth (nominal):
  dp = m · z                       (reference/pitch diameter)
  da = dp + 2·m  · (1 − x · ...)   — simplified: da = dp + m
  df = dp − 2·m  · (1 − x · ...)   — simplified: df = dp − 1.1·m
  db = dp · cos(α)  with α = 30°   (base circle)

Reference: DIN 5480-1:2015 — Involute splines based on reference diameters.
"""

import math
import cadquery as cq

# DIN 5480 common (m, z) combos and plausible shaft length
DIN5480 = [
    dict(m=0.8, z=20, L=30),
    dict(m=1.0, z=18, L=35),
    dict(m=1.25, z=22, L=40),
    dict(m=1.5, z=18, L=45),
    dict(m=2.0, z=16, L=50),
    dict(m=2.5, z=18, L=60),
    dict(m=3.0, z=14, L=70),
]

ALPHA = math.radians(30)  # DIN 5480 pressure angle


def involute(rb, t):
    """Point on involute of circle of base radius rb at parameter t (angle)."""
    x = rb * (math.cos(t) + t * math.sin(t))
    y = rb * (math.sin(t) - t * math.cos(t))
    return x, y


def one_tooth_half(rb, rf, ra, samples=20):
    """Return polyline points for one half-tooth side: from root circle to tip
    circle along involute.  If rb > rf, prepend a radial segment from root
    circle to base circle."""
    pts = []
    # Start on root circle at angle 0 (x-axis)
    pts.append((rf, 0.0))
    # Radial seg from root to base
    if rb > rf:
        pts.append((rb, 0.0))
    # Involute from base (t=0) to tip
    # find t_tip s.t. |inv(rb,t)| = ra
    # |inv| = rb*sqrt(1+t²)  → t_tip = sqrt((ra/rb)² − 1)
    t_tip = math.sqrt(max(0.0, (ra / rb) ** 2 - 1))
    for i in range(1, samples + 1):
        t = t_tip * i / samples
        pts.append(involute(rb, t))
    return pts


def build_spline_outline(m, z, L):
    dp = m * z
    rp = dp / 2
    ra = (dp + m) / 2            # tip
    rf = (dp - 1.1 * m) / 2      # root
    rb = rp * math.cos(ALPHA)    # base
    tooth_angle = 2 * math.pi / z

    # Build one tooth: right-flank involute (from root at θ=0 up to tip),
    # then short arc across tip, then mirror of involute (CCW back down to next
    # root), then arc along root circle to the next tooth's right flank.
    half = one_tooth_half(rb, rf, ra)
    # tip angle at end of involute on right flank (x-axis)
    x_tip_r, y_tip_r = half[-1]
    theta_tip_r = math.atan2(y_tip_r, x_tip_r)
    # We want tooth-space angle split s.t. tooth + space = tooth_angle.
    # Place right flank so tooth centre lies at tooth_angle/2 from x-axis.
    # Rotate right-flank points by −(tooth_angle/4 − theta_tip_r) so tip-end
    # lies at angle tooth_angle/4 (tooth half-angle).
    phi_centre = tooth_angle / 4
    rot_right = phi_centre - theta_tip_r
    right = [(x * math.cos(rot_right) - y * math.sin(rot_right),
              x * math.sin(rot_right) + y * math.cos(rot_right)) for (x, y) in half]
    # Left flank: mirror across x-axis then rotate by tooth_angle/2
    left = [(x, -y) for (x, y) in reversed(half)]
    rot_left = 2 * phi_centre  # mirror line at tooth centre
    left = [(x * math.cos(rot_left) - y * math.sin(rot_left),
             x * math.sin(rot_left) + y * math.cos(rot_left)) for (x, y) in left]

    # Arc across tip between right-end and left-start
    tip_arc = []
    a0 = math.atan2(right[-1][1], right[-1][0])
    a1 = math.atan2(left[0][1], left[0][0])
    N_arc = 6
    for i in range(1, N_arc):
        a = a0 + (a1 - a0) * i / N_arc
        tip_arc.append((ra * math.cos(a), ra * math.sin(a)))

    # Root arc from left-end of tooth k to right-start of tooth k+1
    root_arc = []
    a0r = math.atan2(left[-1][1], left[-1][0])
    a1r = tooth_angle + math.atan2(right[0][1], right[0][0])
    N_root = 4
    for i in range(1, N_root):
        a = a0r + (a1r - a0r) * i / N_root
        root_arc.append((rf * math.cos(a), rf * math.sin(a)))

    # One full tooth + following root arc
    unit = right + tip_arc + left + root_arc

    # Rotate unit z times around centre
    outline = []
    for k in range(z):
        base = k * tooth_angle
        for (x, y) in unit:
            rx = x * math.cos(base) - y * math.sin(base)
            ry = x * math.sin(base) + y * math.cos(base)
            outline.append((rx, ry))
    return outline, L


def build_spline_shaft(m=1.5, z=18, L=45):
    outline, L = build_spline_outline(m, z, L)
    shaft = (
        cq.Workplane("XY")
        .polyline(outline).close()
        .extrude(L)
    )
    # Small chamfer on both ends
    try:
        shaft = shaft.faces(">Z").edges().chamfer(m * 0.15)
        shaft = shaft.faces("<Z").edges().chamfer(m * 0.15)
    except Exception:
        pass
    return shaft


# ------ Parameters ------
M, Z, L = 1.5, 18, 45
result = build_spline_shaft(M, Z, L)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_spline_shaft_m{M}_z{Z}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
