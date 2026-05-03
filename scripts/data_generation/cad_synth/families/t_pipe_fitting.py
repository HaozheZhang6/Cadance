"""T-pipe fitting — main run + perpendicular branch with flanges and bores.

Rewritten from: tmp/manual_family_previews/manual_t_pipe.py
Pipe OD/wall from ASME B36.10M Sch40 NPS table (same as pipe_elbow).

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

Reference: ASME B16.9-2018 — Tee fittings; ASME B36.10M NPS/Sch40 OD and wall table
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ASME B36.10M Sch40 — (nps_label, OD_mm, wall_mm)
_NPS_SCH40 = [
    ("NPS 1/2", 21.3, 2.77),
    ("NPS 3/4", 26.7, 2.87),
    ("NPS 1", 33.4, 3.38),
    ("NPS 1-1/4", 42.2, 3.56),
    ("NPS 1-1/2", 48.3, 3.68),
    ("NPS 2", 60.3, 3.91),
    ("NPS 2-1/2", 73.0, 5.16),
    ("NPS 3", 88.9, 5.49),
    ("NPS 4", 114.3, 6.02),
]
_SMALL_NPS = _NPS_SCH40[:5]  # NPS 1/2 – 1-1/2
_MID_NPS = _NPS_SCH40[2:7]  # NPS 1 – 2-1/2
_ALL_NPS = _NPS_SCH40

VARIANTS = ["tee"]


class TPipeFittingFamily(BaseFamily):
    name = "t_pipe_fitting"
    standard = "ASME B16.9"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL_NPS
            if difficulty == "easy"
            else (_MID_NPS if difficulty == "medium" else _ALL_NPS)
        )
        nps, od, wall = pool[int(rng.integers(0, len(pool)))]
        # Branch: one NPS step smaller (or same if already smallest)
        branch_row = pool[max(0, int(rng.integers(0, len(pool))) - 1)]
        branch_od = branch_row[1]
        run_len = round(od * rng.uniform(2.5, 4.0), 1)
        branch_len = round(branch_od * rng.uniform(1.5, 3.0), 1)

        params = {
            "nps": nps,
            "variant": "tee",
            "outer_diameter": od,
            "wall_thickness": wall,
            "run_length": run_len,
            "branch_od": round(branch_od, 1),
            "branch_length": branch_len,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            flange_od = round(od * 1.8, 1)
            flange_t = round(max(3.0, wall * 1.5), 1)
            n_bolt = int(rng.choice([3, 4, 5, 6, 8]))  # was 4 or 6 by od
            bolt_d = round(max(3.0, min(8.0, flange_od * 0.09)), 1)
            pcd_lo = max(flange_od * 0.55, od + bolt_d + 4)
            pcd_hi = min(flange_od * 0.85, flange_od - bolt_d - 4)
            pcd_lo = min(pcd_lo, pcd_hi - 0.1)
            bolt_pcd = round((pcd_lo + pcd_hi) / 2, 1)
            params["flange_od"] = flange_od
            params["flange_thickness"] = flange_t
            params["n_bolts"] = n_bolt
            params["bolt_diameter"] = bolt_d
            params["bolt_pcd"] = bolt_pcd

            v_flange_od = round(branch_od * 1.6, 1)
            v_flange_t = round(max(3.0, wall * 1.8), 1)
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
