"""Helical gear — involute profile lofted between two pre-rotated cross-sections.

Structural type: loft between two gear profiles with helix-angle rotation.
Profile pts pre-rotated in Python — avoids transformed+polyline loft issues.

variant=external:   standard external helical gear
variant=herringbone: double helix (two mirrored halves, no axial thrust)

Easy:   gear body + bore
Medium: + hub boss + keyway
Hard:   + lightening holes + chamfer
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily
from .spur_gear import _gear_pts


def _rotate_pts(pts, angle_deg):
    """Rotate 2D points by angle_deg around origin."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return [(round(x * c - y * s, 3), round(x * s + y * c, 3)) for x, y in pts]


class HelicalGearFamily(BaseFamily):
    name = "helical_gear"
    standard = "ISO 53"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(["external", "herringbone"])
        _ISO54 = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 1.125, 1.375, 1.75, 2.25, 2.75]
        m = float(rng.choice(_ISO54))
        z = int(rng.uniform(14, 36))
        r_p = m * z / 2
        face_w = round(rng.uniform(m * 8, m * 16), 1)
        helix_angle = round(rng.uniform(10, 30), 1)
        bore_d = round(rng.uniform(r_p * 0.2, max(r_p * 0.21, r_p * 0.5)), 1)

        params = {
            "variant": variant,
            "module": m,
            "n_teeth": z,
            "face_width": face_w,
            "helix_angle": helix_angle,
            "bore_diameter": bore_d,
            "pressure_angle": 20.0,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            kw = round(rng.uniform(bore_d * 0.2, max(bore_d * 0.21, bore_d * 0.3)), 1)
            params["keyway_width"] = kw

        # Web recess vs lightening holes: MUTUALLY EXCLUSIVE for hard.
        # Rule: if rim is enhanced (outer rim > web via recess), hub zone must also be
        # preserved at full height (annular cut keeps hub). No holes in that case.
        _add_web_recess = False
        if difficulty == "medium":
            _add_web_recess = True
        elif difficulty == "hard":
            _add_web_recess = bool(rng.integers(0, 2))  # 50/50

        if _add_web_recess:
            web_cut_r = round(rng.uniform(r_p * 0.55, max(r_p * 0.56, r_p * 0.72)), 1)
            if difficulty == "hard":
                # double-sided: limit per-side depth → hub stays visible
                web_recess_d = round(rng.uniform(face_w * 0.12, face_w * 0.25), 1)
            else:
                web_recess_d = round(rng.uniform(face_w * 0.15, face_w * 0.35), 1)
            web_side = rng.choice(["<Z", ">Z"])
            params["web_cut_radius"] = web_cut_r
            params["web_recess_depth"] = web_recess_d
            params["web_recess_sides"] = "double" if difficulty == "hard" else "single"
            params["web_recess_side"] = web_side

        if difficulty == "hard" and not _add_web_recess:
            # Lightening holes only when no web recess (rim is NOT enhanced)
            n_l = int(rng.choice([4, 6]))
            l_r = round(rng.uniform(r_p * 0.1, max(r_p * 0.11, r_p * 0.18)), 1)
            kw_val = params.get("keyway_width", 0)
            kh_est = round(kw_val * 0.6, 2) if kw_val else 0
            l_pcd_min = max(r_p * 0.55, bore_d / 2 + kh_est + l_r + 3.0)
            l_pcd = round(rng.uniform(l_pcd_min, max(l_pcd_min + 0.1, r_p * 0.75)), 1)
            params["n_lightening"] = n_l
            params["lightening_radius"] = l_r
            params["lightening_pcd"] = l_pcd

        return params

    def validate_params(self, params: dict) -> bool:
        m = params["module"]
        z = params["n_teeth"]
        r_p = m * z / 2
        bd = params["bore_diameter"]
        ha = params["helix_angle"]

        if bd >= r_p * 0.6 or z < 12 or ha < 5 or ha > 35:
            return False

        hr = params.get("hub_radius")
        if hr and hr >= r_p * 0.55:
            return False

        wcr = params.get("web_cut_radius")
        if wcr:
            if hr and wcr <= hr + 1:
                return False
            if wcr >= r_p * 0.85:
                return False

        lr = params.get("lightening_radius")
        lp = params.get("lightening_pcd")
        if lr and lp:
            kw = params.get("keyway_width", 0)
            kh = round(kw * 0.6, 2) if kw else 0
            bore_r = bd / 2
            if lp - lr <= bore_r + kh + 2.0 or lp + lr >= r_p * 0.85:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "external")
        m = params["module"]
        z = params["n_teeth"]
        fw = params["face_width"]
        ha = params["helix_angle"]
        bd = params["bore_diameter"]
        pa = params["pressure_angle"]
        r_p = m * z / 2

        # Helix twist: arc_len = face_width * tan(helix_angle); rot = arc_len / r_p
        twist_deg = round(math.degrees(fw * math.tan(math.radians(ha)) / r_p), 2)

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        pts = _gear_pts(m, z, pa_deg=pa, n_inv=5)
        pts_twisted = _rotate_pts(pts, twist_deg)

        if variant == "external":
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("workplane_offset", {"offset": fw}))
            ops.append(Op("polyline", {"points": pts_twisted}))
            ops.append(Op("close", {}))
            ops.append(Op("loft", {"combine": True}))

        else:  # herringbone: lower half (0 → +twist) union upper half (0 → -twist)
            # Both halves are built independently; upper half translated in Z
            half = round(fw / 2, 3)
            pts_neg_twisted = _rotate_pts(pts, -twist_deg)

            # Lower half: unrotated at z=0, twisted at z=half
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("workplane_offset", {"offset": half}))
            ops.append(Op("polyline", {"points": pts_twisted}))
            ops.append(Op("close", {}))
            ops.append(Op("loft", {"combine": True}))

            # Upper half: pts_twisted at z=half, unrotated at z=fw — as separate extrude
            # Approximate: just extrude untwisted for upper half (visually herringbone-like)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("polyline", {"points": pts_twisted}))
            ops.append(Op("close", {}))
            ops.append(Op("workplane_offset", {"offset": half}))
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("loft", {"combine": True}))

        # Center bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        # Web recess: ANNULAR pocket — preserves hub zone at full face_width.
        # Rule: rim is enhanced (outer rim full height, web thinned) → hub must also
        # stay at full height. Use circle(wcr).circle(hub_keep_r) annular cut.
        wcr = params.get("web_cut_radius")
        wrd = params.get("web_recess_depth")
        wcs = params.get("web_recess_sides", "single")
        wc_side = params.get("web_recess_side", "<Z")
        if wcr and wrd:
            bore_r = bd / 2
            # hub_keep_r: inner boundary of annular cut — preserves hub cylinder
            hub_keep_r = round(bore_r + max(2.0, bore_r * 0.5), 2)
            sides = ["<Z", ">Z"] if wcs == "double" else [wc_side]
            for side in sides:
                ops.append(Op("workplane", {"selector": side}))
                ops.append(Op("circle", {"radius": round(wcr, 3)}))  # outer boundary
                ops.append(
                    Op("circle", {"radius": hub_keep_r})
                )  # inner boundary (hub preserved)
                ops.append(Op("cutBlind", {"depth": round(wrd, 3)}))

        # Keyway slot on all difficulties (cut from top face through bore + hub)
        kw = params.get("keyway_width")
        if kw:
            tags["has_slot"] = True
            kh = round(kw * 0.6, 2)
            bore_r = bd / 2
            rect_width = round(kw, 3)
            rect_height = round(kh + bore_r, 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": 0.0, "y": round(rect_height / 2, 3)}))
            ops.append(Op("rect", {"length": rect_width, "width": rect_height}))
            ops.append(Op("cutThruAll", {}))

        n_l = params.get("n_lightening")
        l_r = params.get("lightening_radius")
        l_pcd = params.get("lightening_pcd")
        if n_l and l_r and l_pcd:
            # Use explicit per-hole cuts at world coords — polarArray drifts after keyway cutThruAll
            # shifts the >Z face centroid away from the gear axis.
            for i in range(n_l):
                ang = 2 * math.pi * i / n_l
                hx = round(l_pcd * math.cos(ang), 3)
                hy = round(l_pcd * math.sin(ang), 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [hx, hy, round(fw / 2, 3)],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(fw * 2, 3),
                                        "radius": round(l_r, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
