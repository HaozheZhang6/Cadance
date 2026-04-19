"""Double simplex sprocket — two parallel simplex tooth rows on one continuous hub.

DIN 8187 / ISO 606 double simplex (e.g., 08B-1 double simplex): each row engages
one independent single-strand chain. Construction (mirroring real-world part):
  - One full-length central hub cylinder (spacer_diameter × total_width)
  - Toothed disc 1 unioned at z = 0..b1
  - Toothed disc 2 unioned at z = b1+spacer_w..2*b1+spacer_w
  - Each disc built via continuous polyline + extrude + top/bottom chamfer
  - Bore + optional DIN 6885A keyway cut through all

Tooth geometry (per row, identical to simplex):
  do  = dp + 0.6*dr             tip diameter
  ri  = 0.505*dr                roller seating radius (ISO 606 §8.2)
  dp  = pitch / sin(π/z)        pitch circle diameter
  b1  = ISO 606 Table 1 tooth width per chain pitch

Axial layout: [disc1: b1] [hub gap: spacer_w] [disc2: b1]

Easy:   2 toothed discs + thin central hub + bore
Medium: + thicker central hub
Hard:   + DIN 6885A keyway

Reference: DIN 8187:1996 — European precision roller chains;
  ISO 606:2015 §8.2 (tooth form), Table 1 (b1 per pitch)
  https://australia-drive.com/product/08b-1-double-simplex-sprocket-for-roller-chains-din-8187-iso-r-606/
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily, din6885a_keyway, iso606_sprocket_profile

# ISO 606 table — (pitch_mm, roller_od_mm, b1_mm)
_ISO606 = [
    (6.350, 3.30, 3.0),
    (8.000, 5.00, 4.4),
    (9.525, 6.35, 5.4),
    (12.700, 8.51, 7.2),
    (15.875, 10.16, 9.1),
    (19.050, 11.91, 11.4),
    (25.400, 15.88, 14.4),
]


class DoubleSimplexSprocketFamily(BaseFamily):
    name = "double_simplex_sprocket"
    standard = "DIN 8187"

    def sample_params(self, difficulty: str, rng) -> dict:
        pitch, dr, b1 = _ISO606[int(rng.integers(0, len(_ISO606)))]

        z_ranges = {"easy": (9, 18), "medium": (18, 36), "hard": (32, 60)}
        z_min, z_max = z_ranges.get(difficulty, (12, 40))
        n_teeth = int(rng.integers(z_min, z_max + 1))

        pcd = pitch / math.sin(math.pi / n_teeth)
        ri = 0.505 * dr
        da = pcd + 0.6 * dr
        df = pcd - 2 * ri

        bore_d = round(rng.uniform(df * 0.2, df * 0.45), 1)
        bore_d = max(bore_d, 5.0)

        # Central hub OD (spans full length, between bore and root circle)
        spacer_d_min = max(bore_d * 1.6, df * 0.4)
        spacer_d_max = df * 0.75
        if spacer_d_min >= spacer_d_max:
            spacer_d = round((spacer_d_min + spacer_d_max) / 2, 1)
        elif difficulty == "easy":
            spacer_d = round(
                rng.uniform(spacer_d_min, (spacer_d_min + spacer_d_max) / 2), 1
            )
        else:
            spacer_d = round(
                rng.uniform((spacer_d_min + spacer_d_max) / 2, spacer_d_max), 1
            )

        # Axial gap between the two toothed rows (chain-plate clearance)
        spacer_w = round(b1 * float(rng.choice([1.5, 1.8, 2.0, 2.2, 2.5])), 1)

        total_w = round(2 * b1 + spacer_w, 2)

        params = {
            "pitch": pitch,
            "roller_diameter": dr,
            "n_teeth": n_teeth,
            "pitch_circle_diameter": round(pcd, 3),
            "tip_diameter": round(da, 3),
            "root_diameter": round(df, 3),
            "tooth_width": round(b1, 2),
            "spacer_diameter": spacer_d,
            "spacer_width": spacer_w,
            "total_width": total_w,
            "bore_diameter": round(bore_d, 1),
            "difficulty": difficulty,
        }

        if difficulty == "hard":
            kw, kd = din6885a_keyway(bore_d)
            params["keyway_width"] = kw
            params["keyway_depth"] = kd

        return params

    def validate_params(self, params: dict) -> bool:
        df = params["root_diameter"]
        da = params["tip_diameter"]
        b1 = params["tooth_width"]
        bore = params["bore_diameter"]
        z = params["n_teeth"]
        spacer_w = params["spacer_width"]
        spacer_d = params["spacer_diameter"]

        if z < 9 or df <= bore or da <= df or b1 < 2.0:
            return False
        if bore < 3.0 or bore >= df * 0.5:
            return False
        if spacer_w < b1 * 1.2:
            return False
        if spacer_d <= bore or spacer_d >= df:
            return False

        kw = params.get("keyway_width", 0)
        kd = params.get("keyway_depth", 0)
        if kw and kd:
            if kw >= bore * 0.5 or kd >= bore * 0.3:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        z = params["n_teeth"]
        pitch = params["pitch"]
        dr = params["roller_diameter"]
        b1 = params["tooth_width"]
        spacer_w = params["spacer_width"]
        spacer_d = params["spacer_diameter"]
        bore = params["bore_diameter"]
        total_w = params["total_width"]

        profile_pts = iso606_sprocket_profile(z, pitch, dr)
        ch = round(b1 * 0.15, 4)

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": True,
        }

        # 1. Central hub — full-length cylinder spanning both toothed rows
        ops.append(Op("circle", {"radius": round(spacer_d / 2, 4)}))
        ops.append(Op("extrude", {"distance": round(total_w, 4)}))

        # 2. Disc 1 (z=0..b1): sub-built with chamfer, then unioned in
        ops.append(Op("union", {"ops": _toothed_disc_subops(profile_pts, b1, ch, 0.0)}))

        # 3. Disc 2 (z=b1+spacer_w..total_w): same, offset workplane
        ops.append(
            Op(
                "union",
                {"ops": _toothed_disc_subops(profile_pts, b1, ch, b1 + spacer_w)},
            )
        )

        # 4. Bore through all
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bore, 4)}))

        # 5. Keyway (hard) — full-depth cut from top face
        kw = params.get("keyway_width", 0)
        kd = params.get("keyway_depth", 0)
        if kw and kd:
            tags["has_slot"] = True
            bore_r = bore / 2
            rect_w = round(kw, 4)
            rect_h = round(kd + bore_r, 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": 0.0, "y": round(rect_h / 2, 4)}))
            ops.append(Op("rect", {"length": rect_w, "width": rect_h}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )


def _toothed_disc_subops(profile_pts, b1, ch, z_offset):
    """Sub-ops to build one chamfered toothed disc inside a union."""
    sub = []
    if z_offset:
        sub.append({"name": "workplane_offset", "args": {"offset": round(z_offset, 4)}})
    sub.append({"name": "polyline", "args": {"points": profile_pts}})
    sub.append({"name": "close", "args": {}})
    sub.append({"name": "extrude", "args": {"distance": round(b1, 4)}})
    if ch > 0:
        sub.append({"name": "edges", "args": {"selector": ">Z"}})
        sub.append({"name": "chamfer", "args": {"length": ch}})
        sub.append({"name": "edges", "args": {"selector": "<Z"}})
        sub.append({"name": "chamfer", "args": {"length": ch}})
    return sub
