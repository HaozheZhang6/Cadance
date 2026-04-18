"""Connecting rod — two cylindrical bosses connected by rectangular shank.

Structural type: multi-boss union (two cylinders + shank box).
All bodies centered at z=0 for consistent overlap.

variant=straight:  both bosses same z, straight shank
variant=offset:    small end offset in z (stepped rod)

Easy:   big end + small end + shank + bores
Medium: + side ribs on shank + optional weight pocket
Hard:   + oil hole through shank center
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program

VARIANTS = ["straight", "offset"]


class ConnectingRodFamily(BaseFamily):
    name = "connecting_rod"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        big_r = rng.uniform(8, 25)
        small_r = rng.uniform(big_r * 0.4, max(big_r * 0.41, big_r * 0.75))
        ctr_dist = rng.uniform(big_r * 3, big_r * 7)
        thickness = rng.uniform(big_r * 0.5, max(big_r * 0.51, big_r * 1.0))
        shank_w = rng.uniform(big_r * 0.4, max(big_r * 0.41, big_r * 0.75))
        bore_big = rng.uniform(big_r * 0.45, max(big_r * 0.46, big_r * 0.72))
        bore_small = rng.uniform(small_r * 0.4, max(small_r * 0.41, small_r * 0.72))

        params = {
            "variant": variant,
            "big_end_radius": round(big_r, 1),
            "small_end_radius": round(small_r, 1),
            "center_distance": round(ctr_dist, 1),
            "thickness": round(thickness, 1),
            "shank_width": round(shank_w, 1),
            "bore_big": round(bore_big, 1),
            "bore_small": round(bore_small, 1),
            "difficulty": difficulty,
        }

        if variant == "offset":
            z_off = round(rng.uniform(thickness * 0.2, max(thickness * 0.21, thickness * 0.6)), 1)
            params["z_offset"] = z_off

        if difficulty in ("medium", "hard"):
            rib_h = round(rng.uniform(3, max(3.1, big_r * 0.4)), 1)
            rib_t = round(rng.uniform(2, max(2.1, shank_w * 0.2)), 1)
            params["rib_height"] = rib_h
            params["rib_thickness"] = rib_t

        if difficulty == "hard":
            oil_d = round(rng.uniform(2, max(2.1, min(5, shank_w * 0.28))), 1)
            params["oil_hole_diameter"] = oil_d

        return params

    def validate_params(self, params: dict) -> bool:
        br = params["big_end_radius"]
        sr = params["small_end_radius"]
        cd = params["center_distance"]
        sw = params["shank_width"]
        bore_big = params["bore_big"]
        bore_small = params["bore_small"]

        if bore_big >= br * 0.85 or bore_small >= sr * 0.85:
            return False
        if cd < br + sr + 5 or sr < 4:
            return False
        if sw >= br * 1.5:
            return False

        rib_h = params.get("rib_height")
        rib_t = params.get("rib_thickness")
        if rib_h and rib_t and rib_t >= sw * 0.5:
            return False

        oil_d = params.get("oil_hole_diameter")
        if oil_d and oil_d >= sw * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "straight")
        br = params["big_end_radius"]
        sr = params["small_end_radius"]
        cd = params["center_distance"]
        t = params["thickness"]
        sw = params["shank_width"]
        bore_big = params["bore_big"]
        bore_small = params["bore_small"]
        z_off = params.get("z_offset", 0.0)

        ops, tags = [], {
            "has_hole": True, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
        }

        # Big end boss at origin — cylinder centered at z=0
        ops.append(Op("cylinder", {"height": t, "radius": br}))

        # Shank — 0.5 mm overlap into each boss to ensure watertight union
        shank_len = round(cd - br - sr, 3)
        shank_cx = round(br + shank_len / 2, 3)
        shank_ext = round(shank_len + 1.0, 3)   # extra 0.5mm each side
        ops.append(Op("union", {"ops": [
            {"name": "transformed", "args": {
                "offset": [shank_cx, 0, 0],
                "rotate": [0, 0, 0],
            }},
            {"name": "box", "args": {
                "length": shank_ext,
                "width": sw,
                "height": t,
                "centered": True,
            }},
        ]}))

        # Small end boss — centered at z=z_off
        ops.append(Op("union", {"ops": [
            {"name": "transformed", "args": {
                "offset": [round(cd, 3), 0, round(z_off, 3)],
                "rotate": [0, 0, 0],
            }},
            {"name": "cylinder", "args": {"height": t, "radius": sr}},
        ]}))

        # Big end bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bore_big * 2, 3)}))

        # Small end bore — use cut so z_offset is handled correctly
        ops.append(Op("cut", {"ops": [
            {"name": "transformed", "args": {
                "offset": [round(cd, 3), 0, round(z_off, 3)],
                "rotate": [0, 0, 0],
            }},
            {"name": "cylinder", "args": {"height": round(t * 1.5, 3), "radius": bore_small}},
        ]}))

        # Side ribs (medium+) — flat plates on ±X sides of shank
        rib_h = params.get("rib_height")
        rib_t = params.get("rib_thickness")
        if rib_h and rib_t:
            rib_z = round(t / 2 + rib_h / 2 - 0.5, 3)
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {
                    "offset": [shank_cx, 0, rib_z],
                    "rotate": [0, 0, 0],
                }},
                {"name": "box", "args": {
                    "length": round(shank_len * 0.8, 3),
                    "width": sw,
                    "height": rib_h,
                    "centered": True,
                }},
            ]}))
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {
                    "offset": [shank_cx, 0, round(-rib_z, 3)],
                    "rotate": [0, 0, 0],
                }},
                {"name": "box", "args": {
                    "length": round(shank_len * 0.8, 3),
                    "width": sw,
                    "height": rib_h,
                    "centered": True,
                }},
            ]}))

        # Oil hole (hard)
        oil_d = params.get("oil_hole_diameter")
        if oil_d:
            ops.append(Op("faces", {"selector": ">Y"}))
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": [(round(shank_cx - cd / 2, 3), 0.0)]}))
            ops.append(Op("hole", {"diameter": oil_d}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
