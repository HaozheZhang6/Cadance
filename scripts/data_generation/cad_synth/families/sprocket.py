"""Sprocket — roller chain sprocket (ISO 606 / DIN 8187).

Continuous-polyline construction (one-shot extrude, no booleans for teeth):
  - Build full CCW outline via iso606_sprocket_profile() — z gaps share tip pts
  - Extrude → chamfer top + bottom edges → bore → optional hub → optional keyway

ISO 606 relations used by the helper:
  dp  = p / sin(π/z)                pitch circle diameter
  do  = dp + 0.6*dr                 outer (tip) diameter
  ri  = 0.505*dr                    root seating arc radius (ISO 606 §8.2)
  β/2 = (140° - 90°/z) / 2          half seating angle
  b1  = ISO 606 Table 1 tooth width per chain pitch

Easy:   plain toothed disc with bore
Medium: + hub (cylindrical boss on back face)
Hard:   + DIN 6885A keyway slot in bore

Reference: ISO 606:2015 — Short-pitch transmission precision roller chains,
  Table 1 (pitch, roller diameter, tooth width b1)
  DIN 8187:1996 — European precision roller chains
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily, din6885a_keyway, iso606_sprocket_profile

# ISO 606 table — (pitch_mm, roller_od_mm, b1_mm)
# b1 = minimum tooth width per ISO 606 Table 3 / DIN 8187
_ISO606 = [
    (6.350, 3.30, 3.0),  # #25
    (8.000, 5.00, 4.4),  # metric 8mm pitch
    (9.525, 6.35, 5.4),  # #41
    (12.700, 8.51, 7.2),  # 08B / #50
    (15.875, 10.16, 9.1),  # #60
    (19.050, 11.91, 11.4),  # #80
    (25.400, 15.88, 14.4),  # #100
]


class SprocketFamily(BaseFamily):
    name = "sprocket"
    standard = "ISO 606"

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

        params = {
            "pitch": pitch,
            "roller_diameter": dr,
            "n_teeth": n_teeth,
            "pitch_circle_diameter": round(pcd, 3),
            "tip_diameter": round(da, 3),
            "root_diameter": round(df, 3),
            "disc_thickness": round(b1, 2),
            "bore_diameter": round(bore_d, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            hub_d = round(bore_d * rng.uniform(1.8, 2.6), 1)
            hub_d = round(min(hub_d, df * 0.75), 1)
            hub_h = round(b1 * rng.uniform(0.8, 1.6), 1)
            params["hub_diameter"] = hub_d
            params["hub_height"] = hub_h

        if difficulty == "hard":
            kw, kd = din6885a_keyway(bore_d)
            params["keyway_width"] = kw
            params["keyway_depth"] = kd

        return params

    def validate_params(self, params: dict) -> bool:
        df = params["root_diameter"]
        da = params["tip_diameter"]
        t = params["disc_thickness"]
        bore = params["bore_diameter"]
        z = params["n_teeth"]

        if z < 9 or df <= bore or da <= df or t < 2.0:
            return False
        if bore < 3.0 or bore >= df * 0.5:
            return False

        hub_d = params.get("hub_diameter", 0)
        if hub_d and hub_d >= df:
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
        t = params["disc_thickness"]
        bore = params["bore_diameter"]

        profile_pts = iso606_sprocket_profile(z, pitch, dr)
        ch = round(t * 0.15, 4)

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": True,
        }

        # Toothed disc — single continuous polyline + extrude
        ops.append(Op("polyline", {"points": profile_pts}))
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": round(t, 4)}))

        # Chamfer outer top + bottom edges (before bore so only outer ring is hit)
        ops.append(Op("edges", {"selector": ">Z"}))
        ops.append(Op("chamfer", {"length": ch}))
        ops.append(Op("edges", {"selector": "<Z"}))
        ops.append(Op("chamfer", {"length": ch}))

        # Central bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bore, 4)}))

        # Hub (medium+)
        hub_d = params.get("hub_diameter", 0)
        hub_h = params.get("hub_height", 0)
        if hub_d and hub_h:
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("circle", {"radius": round(hub_d / 2, 4)}))
            ops.append(Op("extrude", {"distance": round(hub_h, 4)}))
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(
                Op("hole", {"diameter": round(bore, 4), "depth": round(hub_h + 1.0, 4)})
            )

        # Keyway (hard) — full-depth cut from top face
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
