"""
Disc spring (Belleville washer 碟形弹簧) — DIN 2093 manual parametric generator
=================================================================================

Conical washer revolved about Z.  Cross-section is a parallelogram (uniform
thickness t, cone rise h0 between inner and outer rim).

  l0 = h0 + t   (free height)
  Cross-section vertices:
    outer-bottom (De/2, 0) → outer-top (De/2, t)
    inner-top    (Di/2, h0 + t) → inner-bottom (Di/2, h0)

Reference: DIN 2093:2013 — Disc springs; Tables for Group 1/2/3 geometries.
"""

import cadquery as cq

# DIN 2093 Table — Group-2 subset (De, Di, t, l0) mm
DIN2093 = [
    (8.0,   4.2, 0.4, 0.45),
    (10.0,  5.2, 0.5, 0.55),
    (12.5,  6.2, 0.7, 0.80),
    (16.0,  8.2, 0.9, 1.00),
    (20.0, 10.2, 1.1, 1.25),
    (25.0, 12.2, 1.5, 1.55),
    (31.5, 16.3, 1.75, 2.00),
    (40.0, 20.4, 2.25, 2.55),
    (50.0, 25.4, 3.0,  3.30),
    (70.0, 35.5, 4.0,  4.50),
]


def build_disc_spring(De, Di, t, l0):
    """Revolve trapezoid cross-section around Z-axis.  Cone rises from outer
    rim (z=0) to inner rim (z=h0)."""
    h0 = l0 - t
    Ro, Ri = De / 2, Di / 2
    # Profile vertices (R, Z):
    # (Ro, 0) → (Ro, t) → (Ri, h0 + t) → (Ri, h0) → close
    profile = (
        cq.Workplane("XZ")
        .moveTo(Ro, 0)
        .lineTo(Ro, t)
        .lineTo(Ri, h0 + t)
        .lineTo(Ri, h0)
        .close()
    )
    disc = profile.revolve(360, (0, 0, 0), (0, 0, 1))
    # Small edge breaks on the four rim edges
    try:
        disc = disc.edges("%CIRCLE").chamfer(t * 0.08)
    except Exception:
        pass
    return disc


# ------ Parameters ------
# Pick a tall Group-1 size so cone rise is visually obvious (h0/t ≈ 0.75).
De, Di, t, l0 = 50.0, 25.4, 3.0, 5.25
result = build_disc_spring(De, Di, t, l0)
# Rotate 90° so cone axis is horizontal → iso renders show the cone profile.
result_side = result.rotate((0, 0, 0), (1, 0, 0), 90)

try:
    show_object(result)  # type: ignore  # noqa: F821
except NameError:
    pass

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), f"manual_disc_spring_De{int(De)}.step")
    cq.exporters.export(result, out)
    print(f"wrote {out}")
    out_side = os.path.join(os.path.dirname(__file__), f"manual_disc_spring_De{int(De)}_side.step")
    cq.exporters.export(result_side, out_side)
    print(f"wrote {out_side}")
