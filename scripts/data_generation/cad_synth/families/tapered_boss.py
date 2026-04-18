"""Tapered boss / frustum plug — lofted shape from large base to smaller top.

Structural type: loft-based variable cross-section. Can't be made by simple extrude.
Covers: taper plugs, locating cones, draft-angle blocks, funnel flanges.

Easy:   round frustum (circle loft, large→small)
Medium: + flat base flange + center bore
Hard:   + key slot + fillet
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class TaperedBossFamily(BaseFamily):
    name = "tapered_boss"

    def sample_params(self, difficulty: str, rng) -> dict:
        base_d = rng.uniform(20, 100)
        top_d = rng.uniform(base_d * 0.3, base_d * 0.8)
        height = rng.uniform(15, 80)
        taper_offset = round(height * rng.uniform(0.5, 0.9), 1)  # where loft profile sits

        params = {
            "base_diameter": round(base_d, 1),
            "top_diameter": round(top_d, 1),
            "height": round(height, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            flange_od = rng.uniform(base_d * 1.3, base_d * 1.9)
            flange_h = rng.uniform(3, min(12, height * 0.25))
            bore_d = rng.uniform(top_d * 0.25, top_d * 0.6)
            params["flange_diameter"] = round(flange_od, 1)
            params["flange_height"] = round(flange_h, 1)
            params["bore_diameter"] = round(bore_d, 1)
            params["chamfer_length"] = round(rng.uniform(0.5, min(2.0, flange_h * 0.25)), 1)

        if difficulty == "hard":
            bore_val = params.get("bore_diameter", 0)
            kw_lo = max(top_d * 0.15, bore_val + 3)
            kw_hi = top_d * 0.35
            if kw_lo < kw_hi:
                kw = rng.uniform(kw_lo, kw_hi)
                kd = rng.uniform(kw * 0.4, kw * 0.8)
                params["key_width"] = round(kw, 1)
                params["key_depth"] = round(kd, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        bd = params["base_diameter"]
        td = params["top_diameter"]
        h = params["height"]

        if td >= bd or td < 5 or bd < 10 or h < 10:
            return False

        fd = params.get("flange_diameter")
        fh = params.get("flange_height")
        if fd and fh:
            if fd <= bd or fh >= h * 0.4:
                return False

        bore = params.get("bore_diameter")
        if bore and bore >= td * 0.75:
            return False

        cl = params.get("chamfer_length")
        if cl and bore and cl >= (td - bore) / 4:
            return False

        kw = params.get("key_width")
        kd = params.get("key_depth")
        if kw and kd:
            if kw >= td * 0.4 or kd >= td * 0.3:
                return False
            if bore and kd + bore / 2 >= td / 2:
                return False
            # key slot left edge (kw/2) must clear bore radius by 1mm
            if bore and kw < bore + 2:
                return False
            # chamfer must not exceed key depth
            if cl and cl >= kd:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bd = params["base_diameter"]
        td = params["top_diameter"]
        h = params["height"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True, "multi_stage": True,
        }

        # Loft: circle at z=0 → smaller circle at z=height
        # Step 1: draw base circle on XY plane
        ops.append(Op("circle", {"radius": bd / 2}))
        # Step 2: workplane at offset=height, draw top circle
        ops.append(Op("workplane", {"selector": ">Z"}))
        # Can't use >Z before extruding — use transformed workplane approach
        # Actually: draw both circles in sequence then loft
        # Reset and use proper loft: profile on WP1, then WP2 at offset
        # Rebuild: start fresh with faces approach not possible on empty wp
        # Use cylinder approximation via two-step:
        # Better: use XY for base, transformed offset for top
        ops.clear()

        ops.append(Op("circle", {"radius": bd / 2}))
        ops.append(Op("transformed", {"offset": [0, 0, h], "rotate": [0, 0, 0]}))
        ops.append(Op("circle", {"radius": td / 2}))
        ops.append(Op("loft", {"combine": True}))

        # Flange base (medium+)
        flange_d = params.get("flange_diameter")
        flange_h = params.get("flange_height")
        if flange_d and flange_h:
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("circle", {"radius": flange_d / 2}))
            ops.append(Op("extrude", {"distance": flange_h}))

        # Center bore (medium+)
        bore = params.get("bore_diameter")
        if bore:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bore}))

        # Chamfer top rim (medium+) — BEFORE keyway, use edges not faces (loft edge)
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Key slot on top face (hard)
        kw = params.get("key_width")
        kd = params.get("key_depth")
        if kw and kd:
            tags["has_slot"] = True
            key_len = round(td / 2 - kw, 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": round(td / 4, 3), "y": 0.0}))
            ops.append(Op("rect", {"length": key_len, "width": kw}))
            ops.append(Op("cutBlind", {"depth": kd}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
