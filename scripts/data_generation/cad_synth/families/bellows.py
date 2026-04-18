"""Bellows / accordion tube — alternating large/small circle loft.

Structural type: periodic N-section loft between outer and inner circles.
Covers: bellows seals, hydraulic boots, accordion couplings, expansion joints.

variant=round:     circular cross-section convolutions
variant=conical:   each convolution tapers (outer_r decreases toward one end)

Easy:   3-5 convolutions, simple loft
Medium: + end flanges (collar cylinders)
Hard:   + bore hole + flange bolt holes
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ["round", "conical"]


class BellowsFamily(BaseFamily):
    name = "bellows"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        outer_r = rng.uniform(8, 40)
        inner_r = rng.uniform(outer_r * 0.45, max(outer_r * 0.46, outer_r * 0.65))
        n_conv = int(rng.uniform(4, 9))  # number of convolutions
        conv_h = rng.uniform(
            max(3, outer_r * 0.25), max(3.1, outer_r * 0.55)
        )  # height per half-conv

        params = {
            "variant": variant,
            "outer_radius": round(outer_r, 1),
            "inner_radius": round(inner_r, 1),
            "n_convolutions": n_conv,
            "convolution_height": round(conv_h, 1),
            "difficulty": difficulty,
        }

        if variant == "conical":
            taper = rng.uniform(0.05, 0.25)
            params["taper_factor"] = round(taper, 3)

        if difficulty in ("medium", "hard"):
            flange_r = round(outer_r * rng.uniform(1.05, 1.15), 1)
            flange_h = round(rng.uniform(2, max(2.1, conv_h * 0.6)), 1)
            params["flange_radius"] = flange_r
            params["flange_height"] = flange_h

        if difficulty == "hard":
            bore_r = round(inner_r * rng.uniform(0.6, 0.9), 1)
            params["bore_radius"] = bore_r
            n_bolts = int(rng.choice([4, 6]))
            params["n_bolts"] = n_bolts
            bolt_d = round(rng.uniform(2, max(2.1, min(6, flange_r * 0.12))), 1)
            params["bolt_diameter"] = bolt_d

        return params

    def validate_params(self, params: dict) -> bool:
        ir = params["inner_radius"]
        or_ = params["outer_radius"]
        n = params["n_convolutions"]

        if ir >= or_ * 0.9 or ir < 3:
            return False
        if n < 2 or n > 10:
            return False

        fr = params.get("flange_radius")
        if fr and fr <= or_ * 1.02:
            return False

        br = params.get("bore_radius")
        if br and br >= ir * 0.95:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "round")
        or_ = params["outer_radius"]
        ir = params["inner_radius"]
        n = params["n_convolutions"]
        ch = params["convolution_height"]
        taper = params.get("taper_factor", 0.0)
        fr = params.get("flange_radius")
        fh = params.get("flange_height")

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        wall_t = max(1.2, round((or_ - ir) * 0.35, 3))
        bore_r = round(max(1.0, ir - wall_t), 3)

        # Build 2-D profile in XY plane (X=radius, Y=height), revolve around Y axis.
        # Profile traces outer contour so bore is intrinsic — no post-cut needed.
        pts = []

        # Bottom inner edge
        y = 0.0
        if fr and fh:
            pts.append((bore_r, round(y, 3)))
            pts.append((or_, round(y, 3)))
            pts.append((fr, round(y, 3)))
            y += fh
            pts.append((fr, round(y, 3)))
            pts.append((or_, round(y, 3)))
        else:
            pts.append((bore_r, round(y, 3)))
            pts.append((or_, round(y, 3)))

        # Accordion convolutions
        for i in range(n):
            frac_start = (2 * i) / (2 * n)
            frac_end = (2 * i + 1) / (2 * n)
            if variant == "conical":
                cur_ir = round(ir * (1.0 - taper * frac_end * 0.5), 3)
                cur_or = round(
                    or_ * (1.0 - taper * (frac_start + (frac_end - frac_start) / 2)), 3
                )
            else:
                cur_ir = ir
                cur_or = or_
            y += ch
            pts.append((round(cur_ir, 3), round(y, 3)))
            y += ch
            pts.append((round(cur_or, 3), round(y, 3)))

        total_z = round(y, 3)

        # Top flange
        if fr and fh:
            pts.append((fr, round(total_z + fh, 3)))
            pts.append((or_, round(total_z + fh, 3)))
            pts.append((bore_r, round(total_z + fh, 3)))
        else:
            pts.append((bore_r, total_z))

        # Close profile back to start
        pts.append((bore_r, 0.0))

        ops.append(Op("polyline", {"points": pts}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            )
        )

        # Hard bore override (wider bore than wall_t allows)
        br = params.get("bore_radius")
        if br and br > bore_r:
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("hole", {"diameter": br * 2}))

        # Bolt holes (hard) — blind cuts through top and bottom flanges only, not body
        nb = params.get("n_bolts")
        bd = params.get("bolt_diameter")
        if nb and bd and fr and fh:
            # PCD between bellows outer edge and flange outer edge
            bolt_pcd = round(or_ + (fr - or_) * 0.55, 3)
            for face_sel in (">Y", "<Y"):
                ops.append(Op("workplane", {"selector": face_sel}))
                ops.append(
                    Op(
                        "polarArray",
                        {
                            "radius": bolt_pcd,
                            "startAngle": 0,
                            "angle": 360,
                            "count": nb,
                        },
                    )
                )
                ops.append(Op("circle", {"radius": round(bd / 2, 3)}))
                ops.append(Op("cutBlind", {"depth": fh}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
