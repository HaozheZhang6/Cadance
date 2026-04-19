"""
Compression coil spring — DIN 2095, closed and ground ends (两端并紧且磨平)
============================================================================

Variable-pitch helix: 1 tight end-coil (pitch = wire_d, "closed") → n active
coils at nominal pitch → 1 tight end-coil → flat grind planes top & bottom.
Sweep circular wire cross-section along the 3-segment helix.

Reference: DIN 2095:1973 — Cylindrical helical compression springs.
"""

import math
import cadquery as cq

DIN2095_WIRE_D = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]


def helix_points(radius, pitch_bot, n_end_bot, pitch_active, n_active, pitch_top, n_end_top, samples_per_turn=32):
    """Return list of 3D points describing a variable-pitch helix."""
    pts = []
    z = 0.0
    theta0 = 0.0
    def segment(theta0, z0, pitch, n_turns):
        N = max(4, int(samples_per_turn * n_turns))
        out = []
        for i in range(N + 1):
            frac = i / N
            theta = theta0 + frac * 2 * math.pi * n_turns
            zz = z0 + frac * pitch * n_turns
            out.append((radius * math.cos(theta), radius * math.sin(theta), zz))
        return out, theta0 + 2 * math.pi * n_turns, z0 + pitch * n_turns

    seg1, theta0, z = segment(theta0, z, pitch_bot, n_end_bot)
    seg2, theta0, z = segment(theta0, z, pitch_active, n_active)
    seg3, theta0, z = segment(theta0, z, pitch_top, n_end_top)
    # Concatenate but drop duplicated join-points
    pts = seg1 + seg2[1:] + seg3[1:]
    return pts


def build_coil_spring(wire_d=4.0, coil_D=24.0, n_active=6, pitch_active=None,
                      n_end=1.0, grind_t=None):
    """wire_d: wire diameter; coil_D: mean coil diameter; n_active: active
    coils; pitch_active: axial pitch in active zone (default 3·wire_d);
    n_end: coils closed at each end (touching); grind_t: axial thickness
    ground flat from each end."""
    coil_r = coil_D / 2
    if pitch_active is None:
        pitch_active = wire_d * 3
    if grind_t is None:
        grind_t = wire_d * 0.4  # grind about 40 % of wire thickness off each end

    pts = helix_points(
        radius=coil_r,
        pitch_bot=wire_d, n_end_bot=n_end,
        pitch_active=pitch_active, n_active=n_active,
        pitch_top=wire_d, n_end_top=n_end,
    )
    # Build spline path
    path = cq.Workplane("XY").spline(pts).val()
    path_wp = cq.Workplane(obj=path)

    # Wire-profile circle in a plane normal to path start tangent
    # Start tangent direction ≈ (−sin(0), cos(0), pitch/(2π)) = (0, 1, h)
    p0 = pts[0]; p1 = pts[1]
    tx, ty, tz = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    tn = math.sqrt(tx * tx + ty * ty + tz * tz)
    normal = (tx / tn, ty / tn, tz / tn)

    # Create circle centred at p0 perpendicular to tangent
    profile_plane = cq.Plane(origin=cq.Vector(*p0), normal=cq.Vector(*normal))
    profile = cq.Workplane(profile_plane).circle(wire_d / 2)
    spring = profile.sweep(path_wp)

    # Grind flat top + bottom
    total_z = pts[-1][2]
    grind_box_bot = (
        cq.Workplane("XY")
        .box(coil_D * 2, coil_D * 2, grind_t * 2)
        .translate((0, 0, -grind_t))
    )
    grind_box_top = (
        cq.Workplane("XY")
        .box(coil_D * 2, coil_D * 2, grind_t * 2)
        .translate((0, 0, total_z + grind_t))
    )
    spring = spring.cut(grind_box_bot).cut(grind_box_top)
    return spring


# ------ Parameters ------
WIRE_D = 4.0
COIL_D = 24.0
N_ACTIVE = 6.0
result = build_coil_spring(wire_d=WIRE_D, coil_D=COIL_D, n_active=N_ACTIVE)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "manual_coil_spring_closed_ground.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
