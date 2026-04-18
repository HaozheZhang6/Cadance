"""Waffle / grid-pocket plate — plate with grid of square/round pockets (lightening).

Structural type: deep grid-pocket pattern. Very different from a plate with through holes.
Common in aerospace, motorsport, precision machine tools for weight reduction.

Easy:   plate + rarray of square pockets (cutBlind)
Medium: + mounting holes + chamfer on pockets
Hard:   + round pockets (mix) + fillet + through center hole
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class WafflePlateFamily(BaseFamily):
    name = "waffle_plate"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(60, 200)
        width = rng.uniform(50, 160)
        thick = rng.uniform(10, 35)
        margin = rng.uniform(6, max(7, min(20, length / 6, width / 6)))

        # Grid of square pockets
        nx = int(rng.choice([2, 3, 4]))
        ny = int(rng.choice([2, 3]))
        pocket_w = (length - 2 * margin) / nx * rng.uniform(0.55, 0.78)
        pocket_h = (width - 2 * margin) / ny * rng.uniform(0.55, 0.78)
        pocket_depth = rng.uniform(thick * 0.4, thick * 0.75)
        x_spacing = (length - 2 * margin - pocket_w) / max(1, nx - 1) if nx > 1 else 1
        y_spacing = (width - 2 * margin - pocket_h) / max(1, ny - 1) if ny > 1 else 1

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thick, 1),
            "margin": round(margin, 1),
            "pocket_nx": nx,
            "pocket_ny": ny,
            "pocket_width": round(pocket_w, 1),
            "pocket_height": round(pocket_h, 1),
            "pocket_depth": round(pocket_depth, 1),
            "x_spacing": round(x_spacing, 2),
            "y_spacing": round(y_spacing, 2),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            inset = rng.uniform(5, max(6, min(16, margin * 0.8)))
            params["mount_inset"] = round(inset, 1)
            params["mount_hole_diameter"] = round(rng.uniform(3.0, max(3.1, min(6.0, inset * 0.5))), 1)
            params["pocket_chamfer"] = round(rng.uniform(0.3, min(1.5, pocket_w * 0.08)), 1)

        if difficulty == "hard":
            # Some pockets round instead of square (variation)
            params["round_pocket_diameter"] = round(
                min(pocket_w, pocket_h) * rng.uniform(0.7, 0.95), 1
            )
            params["center_hole_diameter"] = round(
                rng.uniform(8, min(25, width * 0.2)), 1
            )
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, thick * 0.08)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, t = params["length"], params["width"], params["thickness"]
        m = params["margin"]
        nx, ny = params["pocket_nx"], params["pocket_ny"]
        pw, ph = params["pocket_width"], params["pocket_height"]
        pd = params["pocket_depth"]
        xs = params["x_spacing"]
        ys = params["y_spacing"]

        if pw < 4 or ph < 4 or pd < 3:
            return False
        if pd >= t * 0.85:
            return False
        # Pockets fit in length
        if nx > 1 and xs * (nx - 1) + pw > l - 2 * m + 0.5:
            return False
        if nx == 1 and pw > l - 2 * m + 0.5:
            return False
        # Pockets fit in width
        if ny > 1 and ys * (ny - 1) + ph > w - 2 * m + 0.5:
            return False
        if ny == 1 and ph > w - 2 * m + 0.5:
            return False

        chd = params.get("center_hole_diameter")
        if chd and chd >= min(w, l) * 0.4:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, t = params["length"], params["width"], params["thickness"]
        nx, ny = params["pocket_nx"], params["pocket_ny"]
        pw, ph = params["pocket_width"], params["pocket_height"]
        pd = params["pocket_depth"]
        xs = params["x_spacing"]
        ys = params["y_spacing"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "pattern_like": True, "has_pocket": True,
        }

        # Base plate
        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Pocket edge chamfer (medium+) — BEFORE pockets to avoid complex face boundary
        pc = params.get("pocket_chamfer")
        if pc:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": pc}))

        # Grid pockets (square cutBlind)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rarray", {
            "xSpacing": xs if nx > 1 else 1,
            "ySpacing": ys if ny > 1 else 1,
            "xCount": nx,
            "yCount": ny,
        }))
        ops.append(Op("rect", {"length": pw, "width": ph}))
        ops.append(Op("cutBlind", {"depth": pd}))

        # Round pockets on bottom face (hard, variation)
        rpd = params.get("round_pocket_diameter")
        if rpd:
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("rarray", {
                "xSpacing": xs if nx > 1 else 1,
                "ySpacing": ys if ny > 1 else 1,
                "xCount": nx,
                "yCount": ny,
            }))
            ops.append(Op("circle", {"radius": rpd / 2}))
            ops.append(Op("cutBlind", {"depth": round(t - pd - 2, 2)}))

        # Center through hole (hard)
        chd = params.get("center_hole_diameter")
        if chd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": chd}))

        # Mounting holes (medium+)
        ins = params.get("mount_inset")
        mhd = params.get("mount_hole_diameter")
        if ins and mhd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            pts = [
                (round( l/2 - ins, 3), round( w/2 - ins, 3)),
                (round( l/2 - ins, 3), round(-w/2 + ins, 3)),
                (round(-l/2 + ins, 3), round( w/2 - ins, 3)),
                (round(-l/2 + ins, 3), round(-w/2 + ins, 3)),
            ]
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": mhd}))

        # Fillet (hard)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
