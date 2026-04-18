"""T-pipe fitting — main run + perpendicular branch with flanges and bores.

Rewritten from: tmp/manual_family_previews/manual_t_pipe.py

Construction (matches manual exactly):
  Step 1: Main pipe outer wall — cylinder along Z
  Step 2: Main-end flanges — two cylinders at ±run_length/2
  Step 3: Bolt holes on main flanges — polarArray on >Z and <Z faces
  Step 4: Branch outer wall — cylinder along +Y, rotated -90°
  Step 5: Branch flange — cylinder at top of branch
  Step 6: Hollow branch — cut cylinder from Y=0 through branch+flange
  Step 7: Hollow main — cut cylinder through full assembly length (LAST)

Order matters: bore cuts come AFTER all solids are unioned (manual sequence).

Easy:   tee body + through bores (no flanges)
Medium: + flanges + bolt holes on main ends + branch flange
Hard:   + bolt holes on branch flange
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program

VARIANTS = ["tee"]


class TPipeFittingFamily(BaseFamily):
    name = "t_pipe_fitting"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        od = rng.uniform(12, 60)
        wall = rng.uniform(2, max(2.1, od * 0.15))
        run_len = rng.uniform(od * 1.5, od * 4)
        branch_od = rng.uniform(od * 0.5, od * 0.95)
        branch_len = rng.uniform(branch_od * 1.2, branch_od * 3)

        params = {
            "variant": variant,
            "outer_diameter": round(od, 1),
            "wall_thickness": round(wall, 1),
            "run_length": round(run_len, 1),
            "branch_od": round(branch_od, 1),
            "branch_length": round(branch_len, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            flange_od = round(od * rng.uniform(1.5, 2.2), 1)
            flange_t = round(rng.uniform(3, max(3.1, wall * 1.5)), 1)
            n_bolt = int(rng.choice([4, 6, 8]))
            bolt_d = round(
                rng.uniform(3, max(3.1, min(8, flange_od * 0.1))), 1
            )
            pcd_lo = max(flange_od * 0.55, od + bolt_d + 4)
            pcd_hi = min(flange_od * 0.85, flange_od - bolt_d - 4)
            pcd_lo = min(pcd_lo, pcd_hi - 0.1)
            bolt_pcd = round(rng.uniform(pcd_lo, pcd_hi), 1)
            params["flange_od"] = flange_od
            params["flange_thickness"] = flange_t
            params["n_bolts"] = n_bolt
            params["bolt_diameter"] = bolt_d
            params["bolt_pcd"] = bolt_pcd

            # Branch flange
            v_flange_od = round(branch_od * rng.uniform(1.2, 1.6), 1)
            v_flange_t = round(rng.uniform(3, max(3.1, wall * 1.8)), 1)
            params["branch_flange_od"] = v_flange_od
            params["branch_flange_thickness"] = v_flange_t

        return params

    def validate_params(self, params: dict) -> bool:
        od = params["outer_diameter"]
        wall = params["wall_thickness"]
        bod = params["branch_od"]

        if wall >= od * 0.4 or od < 8:
            return False
        if bod >= od:
            return False

        flange_od = params.get("flange_od")
        bolt_pcd = params.get("bolt_pcd")
        bolt_d = params.get("bolt_diameter")
        if flange_od and flange_od <= od * 1.2:
            return False
        if bolt_pcd and bolt_d and flange_od:
            bolt_r = bolt_pcd / 2
            if bolt_r - bolt_d / 2 < od / 2 + 2:
                return False
            if bolt_r + bolt_d / 2 > flange_od / 2 - 2:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "tee")
        od = params["outer_diameter"]
        wall = params["wall_thickness"]
        rl = params["run_length"]
        bod = params["branch_od"]
        bl = params["branch_length"]
        r = round(od / 2, 3)
        br = round(bod / 2, 3)
        bore_r = round(r - wall, 3)
        branch_bore_r = round(br - wall, 3)

        flange_od = params.get("flange_od")
        flange_t = params.get("flange_thickness")
        v_flange_od = params.get("branch_flange_od")
        v_flange_t = params.get("branch_flange_thickness")

        ops = []
        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # ── Step 1: Main pipe outer wall ──
        # Manual: cylinder(main_pipe_length, main_pipe_outer_radius) — centered
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "cylinder",
                            "args": {"height": round(rl, 3), "radius": r},
                        },
                    ]
                },
            )
        )

        # ── Step 2: Main-end flanges (medium+) ──
        # Manual: two cylinders at ±h_flange_offset via transformed
        if flange_od and flange_t:
            fr = round(flange_od / 2, 3)
            h_flange_offset = round(rl / 2, 3)
            for z_ctr in [round(-h_flange_offset, 3), h_flange_offset]:
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0.0, 0.0, z_ctr],
                                        "rotate": [0.0, 0.0, 0.0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(flange_t, 3),
                                        "radius": fr,
                                    },
                                },
                            ]
                        },
                    )
                )

        # ── Step 3: Bolt holes on main flanges (medium+) ──
        # Manual: .faces(">Z").workplane().polarArray(...).hole(...)
        if flange_od and flange_t:
            n_b = params["n_bolts"]
            b_pcd = params["bolt_pcd"]
            b_d = params["bolt_diameter"]
            for selector in [">Z", "<Z"]:
                ops.append(Op("workplane", {"selector": selector}))
                ops.append(
                    Op(
                        "polarArray",
                        {
                            "radius": round(b_pcd / 2, 3),
                            "startAngle": 0,
                            "angle": 360,
                            "count": n_b,
                        },
                    )
                )
                ops.append(Op("hole", {"diameter": round(b_d, 3)}))

        # ── Step 4: Branch outer wall ──
        # Manual: cylinder at (0, branch_length/2, 0) rotated -90° around X
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, round(bl / 2, 3), 0.0],
                                "rotate": [-90.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(bl, 3), "radius": br},
                        },
                    ]
                },
            )
        )

        # ── Step 5: Branch flange at top of branch (medium+) ──
        # Manual: cylinder at y = branch_length - v_flange_t/2, rotated -90°
        if v_flange_od and v_flange_t:
            v_fr = round(v_flange_od / 2, 3)
            v_flange_y = round(bl - v_flange_t / 2, 3)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, v_flange_y, 0.0],
                                    "rotate": [-90.0, 0.0, 0.0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(v_flange_t, 3),
                                    "radius": v_fr,
                                },
                            },
                        ]
                    },
                )
            )

        # ── Step 6: Hollow branch bore ──
        # Manual: cut from Y=0 through branch top + flange
        # Branch bore height: branch_length + 1 (ensures cut through flange)
        # Bore center: (branch_length+1)/2 (starts at Y=0, extends upward)
        branch_cut_len = round(bl + 1, 3)
        branch_cut_cy = round(branch_cut_len / 2, 3)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, branch_cut_cy, 0.0],
                                "rotate": [-90.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": branch_cut_len,
                                "radius": branch_bore_r,
                            },
                        },
                    ]
                },
            )
        )

        # ── Step 7: Hollow main bore (LAST — punches through everything) ──
        # Manual: main_cut_len = run_length + 2*flange_t + 1 to ensure full penetration
        if flange_t:
            main_bore_h = round(rl + 2 * flange_t + 1, 3)
        else:
            main_bore_h = round(rl + 2, 3)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "cylinder",
                            "args": {"height": main_bore_h, "radius": bore_r},
                        },
                    ]
                },
            )
        )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
