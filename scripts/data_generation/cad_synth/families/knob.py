"""Conical control knob — KIPP/HALDER-style ergonomic control knob.

Generic conical/hourglass control knob with side flutes for finger grip and a
threaded center bore. NOT DIN 319 (which is a ball knob — sphere + handle);
the closest catalog reference is KIPP K0153 / HALDER 24380 conical knobs,
which are not covered by a single DIN/ISO standard. Standard tag: N/A.

Easy:   single tapered frustum (small, D 8–20 mm)
Medium: hourglass (3 frustum sections) + side flutes + top crown fillet
Hard:   + threaded center bore (full range, D 8–80 mm)

Side flutes are axial cylindrical cuts placed at radius ≈ top_radius × 1.05
(just outside the crown), so they appear as scallops on the crown taper —
real grip surface, not bottom-face decorative holes.

Reference: no single standard; D / thread / H sizing borrowed from common
KIPP / HALDER catalog ranges (M3–M20 thread, D 8–80 mm).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# Catalog-style table — (D_knob_mm, thread_M_mm, H_nominal_mm)
_TABLE = [
    (8, 3, 12),
    (10, 4, 14),
    (12, 5, 16),
    (14, 6, 20),
    (16, 6, 22),
    (20, 8, 28),
    (25, 10, 36),
    (32, 10, 45),
    (40, 12, 56),
    (50, 12, 71),
    (63, 16, 90),
    (80, 20, 112),
]
_SMALL = _TABLE[:5]  # D 8–16
_MID = _TABLE[2:9]  # D 12–40
_ALL = _TABLE


class KnobFamily(BaseFamily):
    name = "knob"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        D, M, H = pool[int(rng.integers(0, len(pool)))]
        r_base = round(D / 2, 1)
        r_top = round(r_base * 0.55, 1)
        h_total = float(H)

        params = {
            "knob_diameter": float(D),
            "thread_m": float(M),
            "base_radius": r_base,
            "top_radius": r_top,
            "total_height": h_total,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            r_waist = round(r_top * 0.75, 1)
            h1 = round(h_total * 0.45, 1)
            h2 = round(h_total * 0.25, 1)
            params["waist_radius"] = r_waist
            params["h_base_to_waist"] = h1
            params["h_waist_to_top"] = h2
            # Side flutes — clustered near crown for finger grip
            n_flutes = int(rng.choice([8, 10, 12]))
            params["n_flutes"] = n_flutes
            params["flute_radius"] = round(max(0.8, r_base * 0.10), 1)
            params["fillet_top"] = round(max(0.4, min(1.0, r_top * 0.18)), 2)
            params["chamfer_bot"] = round(max(0.3, min(0.8, r_base * 0.08)), 2)

        if difficulty == "hard":
            params["bore_diameter"] = float(M)
            params["n_flutes"] = int(rng.choice([12, 16, 20]))

        return params

    def validate_params(self, params: dict) -> bool:
        rb = params["base_radius"]
        rt = params["top_radius"]
        h = params["total_height"]

        if rt >= rb or h < 8:
            return False

        rw = params.get("waist_radius")
        h1 = params.get("h_base_to_waist")
        h2 = params.get("h_waist_to_top")
        if rw and h1 and h2:
            if h1 + h2 >= h:
                return False
            if rw >= rb:
                return False

        bd = params.get("bore_diameter")
        if bd and bd >= rt * 1.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rb = params["base_radius"]
        rt = params["top_radius"]
        h = params["total_height"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        rw = params.get("waist_radius")
        h1 = params.get("h_base_to_waist")
        h2 = params.get("h_waist_to_top")

        if rw and h1 and h2:
            t1 = round(math.degrees(math.atan((rb - rw) / h1)), 3)
            ops.append(Op("circle", {"radius": rb}))
            ops.append(Op("extrude", {"distance": round(h1, 3), "taper": t1}))
            h3 = round(h - h1 - h2, 3)
            t2 = round(math.degrees(math.atan((rw - rt) / h2)), 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": round(rw, 3)}))
            ops.append(Op("extrude", {"distance": round(h2, 3), "taper": t2}))
            if h3 > 0.5:
                ops.append(Op("workplane", {"selector": ">Z"}))
                ops.append(Op("circle", {"radius": round(rt, 3)}))
                ops.append(Op("extrude", {"distance": h3}))
        else:
            taper_deg = round(math.degrees(math.atan((rb - rt) / h)), 3)
            ops.append(Op("circle", {"radius": rb}))
            ops.append(Op("extrude", {"distance": round(h, 3), "taper": taper_deg}))

        # Top crown fillet — apply BEFORE flutes/bore so the >Z face has only
        # the outer rim circle (single edge), guaranteeing the fillet succeeds.
        ft = params.get("fillet_top")
        if ft:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("fillet", {"radius": ft}))

        # Bottom chamfer — same reasoning, before the bore is cut.
        cb = params.get("chamfer_bot")
        if cb:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cb}))

        # Side flutes — N axial cylinders cut at radius rt*1.05 near the crown.
        # Because the body is hourglass and the flutes sit just outside the
        # narrow crown, the cuts only nibble the upper portion → scallops on
        # the crown taper, not holes in the side.
        n_f = params.get("n_flutes")
        fr = params.get("flute_radius")
        if n_f and fr:
            tags["has_slot"] = True
            position_r = round(rt * 1.05, 3)
            flute_h = round(h * 0.55, 3)
            flute_zc = round(h - flute_h / 2 - 0.3, 3)
            for i in range(n_f):
                ang = math.radians(360.0 * i / n_f)
                fx = round(position_r * math.cos(ang), 3)
                fy = round(position_r * math.sin(ang), 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {"offset": [fx, fy, flute_zc]},
                                },
                                {
                                    "name": "cylinder",
                                    "args": {"height": flute_h, "radius": fr},
                                },
                            ]
                        },
                    )
                )

        # Threaded center bore (hard) — cut last so it goes through cleanly.
        bd = params.get("bore_diameter")
        if bd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
