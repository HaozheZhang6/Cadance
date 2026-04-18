"""Gusseted bracket — L-bracket with triangular gusset rib for rigidity.

Typical use: high-stiffness mounting arm, structural corner bracket.
Easy:   L-profile via polyline+mirrorY + extrude
Medium: + mounting holes both flanges + chamfer
Hard:   + gusset pocket (lightening) + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class GussetedBracketFamily(BaseFamily):
    name = "gusseted_bracket"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        flange_w = rng.uniform(30, 100)  # width of each flange
        flange_t = rng.uniform(5, 15)  # flange thickness
        depth = rng.uniform(20, 80)  # extrude depth (Z)
        # gusset must fit below the inner corner (fw/2 - ft); keep 3mm margin
        gh_min = max(10.0, flange_w * 0.2)
        gh_max = max(gh_min + 2.0, flange_w / 2 - flange_t - 3)
        gusset_h = rng.uniform(gh_min, gh_max)
        inset = rng.uniform(6, min(18, flange_w / 4))
        hole_d = rng.uniform(3.0, min(8.0, inset * 0.6))

        params = {
            "flange_width": round(flange_w, 1),
            "flange_thickness": round(flange_t, 1),
            "depth": round(depth, 1),
            "gusset_height": round(gusset_h, 1),
            "mount_inset": round(inset, 1),
            "mount_hole_diameter": round(hole_d, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_holes = int(rng.choice([1, 2]))
            params["holes_per_flange"] = n_holes
            params["chamfer_length"] = round(
                rng.uniform(0.5, min(2.0, flange_t / 4)), 1
            )

        if difficulty == "hard":
            pocket_w = rng.uniform(gusset_h * 0.2, gusset_h * 0.45)
            pocket_d = rng.uniform(flange_t * 0.3, flange_t * 0.6)
            params["gusset_pocket_width"] = round(pocket_w, 1)
            params["gusset_pocket_depth"] = round(pocket_d, 1)
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, flange_t / 4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        fw = params["flange_width"]
        ft = params["flange_thickness"]
        d = params["depth"]
        gh = params["gusset_height"]
        ins = params["mount_inset"]
        hd = params["mount_hole_diameter"]

        if ft < 3 or fw < 15 or d < 10 or gh < 10:
            return False
        # gusset must not exceed inner wall height (fw/2 - ft) to avoid inverted profile
        if gh >= fw / 2 - ft:
            return False
        if ins < 4 or hd >= ins * 0.8:
            return False
        if ins + hd / 2 > fw / 2 - 2:
            return False

        pw = params.get("gusset_pocket_width")
        pd = params.get("gusset_pocket_depth")
        if pw and pd:
            if pw >= gh * 0.6 or pd >= ft * 0.8:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        fw = params["flange_width"]
        ft = params["flange_thickness"]
        d = params["depth"]
        gh = params["gusset_height"]
        ins = params["mount_inset"]
        hd = params["mount_hole_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # L-profile with triangular gusset, right half, then mirrorY
        # Profile (looking along extrude axis = Z):
        # Start at origin (inner corner), draw:
        #   horizontal flange bottom edge → right
        #   up flange thickness
        #   diagonal gusset back to inner vertical
        #   up remaining inner wall
        #   close (back to origin)
        # Then mirrorY to get full L + 2 gussets
        half_fw = round(fw / 2, 3)
        pts = [
            (0.0, 0.0),
            (half_fw, 0.0),
            (half_fw, ft),
            (ft, gh),
            (ft, half_fw),
            (0.0, half_fw),
        ]
        ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
        for px, py in pts[1:]:
            ops.append(Op("lineTo", {"x": px, "y": py}))
        ops.append(Op("mirrorY", {}))
        ops.append(Op("extrude", {"distance": d}))

        # Chamfer (medium+) and fillet (hard) — BEFORE holes/pocket for clean edge selection
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Mounting holes on horizontal flange (>Y face = forward-facing)
        n_holes = params.get("holes_per_flange", 1)
        if n_holes == 1:
            hole_pts_h = [(0.0, round(ins - d / 2, 3))]
            hole_pts_v = [(0.0, round(ins - d / 2, 3))]
        else:
            dx = round((d / 2 - ins), 3)
            hole_pts_h = [(-dx, 0.0), (dx, 0.0)]
            hole_pts_v = [(-dx, 0.0), (dx, 0.0)]

        # Horizontal flange: >Y face (front face along flange)
        ops.append(Op("workplane", {"selector": "<Y"}))
        ops.append(
            Op(
                "pushPoints",
                {"points": [(round(half_fw / 2, 3), round(-d / 2 + ins, 3))]},
            )
        )
        ops.append(Op("hole", {"diameter": hd}))

        # Vertical flange: <X face
        ops.append(Op("workplane", {"selector": ">X"}))
        ops.append(
            Op(
                "pushPoints",
                {"points": [(round(half_fw / 2, 3), round(-d / 2 + ins, 3))]},
            )
        )
        ops.append(Op("hole", {"diameter": hd}))

        # Gusset pocket (hard) — cut into gusset face
        pw = params.get("gusset_pocket_width")
        pd = params.get("gusset_pocket_depth")
        if pw and pd:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op(
                    "center",
                    {"x": round(ft / 2 + pw / 2, 3), "y": round(ft / 2 + pw / 2, 3)},
                )
            )
            ops.append(Op("rect", {"length": pw, "width": pw}))
            ops.append(Op("cutBlind", {"depth": pd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
