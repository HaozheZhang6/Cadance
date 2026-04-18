"""Bearing retainer cap — hollow boss + optional flange/ear collar.

Structural type: central hollow cylinder (boss) + mounting provision.
Covers: bearing end-caps, shaft seal covers, hub covers.

variant=disc:  full circular flange disc at base + hollow boss + bolt pattern
variant=ear:   hollow boss + thin base collar ring + 2 symmetric ear tabs (180° apart)
               simple 空心圆筒 union with 对称小耳朵的空心圆环

Easy:   boss + flange/collar + bore
Medium: + chamfer on boss top + shoulder step on bore
Hard:   + oil seal groove on boss inner bore
"""

import math

from ..pipeline.builder import Op, Program
from ..pipeline.plane_utils import plane_offset
from .base import BaseFamily

# ISO 15 / 62xx series ball bearings — (shaft_bore_d, bearing_od, width_b) mm
_ISO15_62XX = [
    (10, 30, 9),
    (12, 32, 10),
    (15, 35, 11),
    (17, 40, 12),
    (20, 47, 14),
    (25, 52, 15),
    (30, 62, 16),
    (35, 72, 17),
    (40, 80, 18),
    (45, 85, 19),
    (50, 90, 20),
    (55, 100, 21),
    (60, 110, 22),
    (65, 120, 23),
    (70, 125, 24),
    (80, 140, 26),
]
_SMALL = _ISO15_62XX[:5]  # bore 10–20 mm
_MID = _ISO15_62XX[2:10]  # bore 15–45 mm
_ALL = _ISO15_62XX

VARIANTS = ["disc", "ear"]


class BearingRetainerCapFamily(BaseFamily):
    name = "bearing_retainer_cap"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        bore_d, bearing_od, bearing_w = pool[int(rng.integers(0, len(pool)))]
        bore_d = float(bore_d)
        # boss OD = bearing OD + housing clearance (cap sits around or over bearing)
        boss_od = round(rng.uniform(bearing_od * 1.0, bearing_od * 1.30), 1)
        boss_h = round(rng.uniform(bearing_w * 1.2, bearing_w * 2.5), 1)
        boss_h = max(boss_h, 15)

        variant = rng.choice(VARIANTS)

        params = {
            "variant": str(variant),
            "boss_diameter": boss_od,
            "boss_height": boss_h,
            "bore_diameter": bore_d,
            "difficulty": difficulty,
        }

        if variant == "disc":
            flange_od = rng.uniform(max(boss_od * 1.6, boss_od + 26), boss_od * 2.8)
            flange_t = rng.uniform(4, max(5, boss_h * 0.20))
            n_bolts = int(rng.choice([4, 6, 8]))
            pcd_lo = boss_od / 2 + 5
            pcd_hi = max(pcd_lo + 2, flange_od / 2 - 6)
            bolt_pcd = round(rng.uniform(pcd_lo, pcd_hi), 1)
            spacing = 2 * math.pi * bolt_pcd / n_bolts
            b_hi = min(14.0, spacing * 0.40)
            b_lo = max(4.0, min(b_hi * 0.80, spacing * 0.22))
            bolt_d = round(rng.uniform(b_lo, b_hi), 1)
            params.update(
                flange_diameter=round(flange_od, 1),
                flange_thickness=round(flange_t, 1),
                n_bolts=n_bolts,
                bolt_pcd_radius=bolt_pcd,
                bolt_diameter=bolt_d,
            )
        else:  # ear: thin collar ring + 2 symmetric ear tabs at 0°/180°
            collar_od = rng.uniform(boss_od * 1.25, boss_od * 1.7)
            collar_h = rng.uniform(max(6, boss_h * 0.12), max(10, boss_h * 0.28))
            ear_pcd = round(
                rng.uniform(collar_od / 2 + 4, collar_od / 2 + collar_od * 0.35), 1
            )
            ear_d = round(
                rng.uniform(max(20, collar_od * 0.20), max(21, collar_od * 0.35)), 1
            )
            bolt_d = round(rng.uniform(ear_d * 0.30, ear_d * 0.52), 1)
            # tangent style requires (boss_r - ear_r) / ear_pcd < 0.625 (ensures neck ≥ 3x old min)
            r1, r2, d = boss_od / 2, ear_d / 2, ear_pcd
            web_style = "tangent" if (r1 - r2) / d < 0.625 else "bar"
            web_style = str(rng.choice(["bar", web_style]))  # 50/50 when tangent ok
            params.update(
                collar_diameter=round(collar_od, 1),
                collar_height=round(collar_h, 1),
                ear_pcd_radius=ear_pcd,
                ear_diameter=ear_d,
                bolt_diameter=bolt_d,
                web_style=web_style,
            )

        if difficulty in ("medium", "hard"):
            step_d = round(
                rng.uniform(bore_d * 1.08, min(bore_d * 1.30, boss_od * 0.92)), 1
            )
            step_h = round(rng.uniform(boss_h * 0.20, boss_h * 0.50), 1)
            params["shoulder_diameter"] = step_d
            params["shoulder_height"] = step_h
            params["boss_chamfer"] = round(rng.uniform(0.5, min(2.0, boss_h * 0.08)), 1)

        if difficulty == "hard":
            groove_w = round(rng.uniform(2.0, min(5.0, boss_h * 0.15)), 1)
            groove_d = round(
                rng.uniform(0.8, min(2.5, (boss_od - bore_d) / 2 * 0.35)), 1
            )
            params["oil_groove_width"] = groove_w
            params["oil_groove_depth"] = groove_d

        return params

    def validate_params(self, params: dict) -> bool:
        bod = params["boss_diameter"]
        bh = params["boss_height"]
        bd = params["bore_diameter"]
        variant = params.get("variant", "disc")

        if bd >= bod * 0.80 or bd < 6 or bh < 10:
            return False

        if variant == "disc":
            fod = params.get("flange_diameter", 0)
            ft = params.get("flange_thickness", 0)
            bpr = params.get("bolt_pcd_radius", 0)
            blt_d = params.get("bolt_diameter", 0)
            n = params.get("n_bolts", 4)
            if fod <= bod * 1.4 or ft < 3:
                return False
            if bpr <= bod / 2 + 3 or bpr >= fod / 2 - 3:
                return False
            if blt_d >= 2 * math.pi * bpr / n * 0.50:
                return False
        else:  # ear
            col_od = params.get("collar_diameter", 0)
            col_h = params.get("collar_height", 0)
            ear_pcd = params.get("ear_pcd_radius", 0)
            ear_d = params.get("ear_diameter", 0)
            bolt_d = params.get("bolt_diameter", 0)
            if col_od <= bod * 1.15 or col_h < 3:
                return False
            if ear_pcd <= col_od / 2 + 2:
                return False
            if bolt_d >= ear_d * 0.60:
                return False

        sd = params.get("shoulder_diameter")
        sh = params.get("shoulder_height")
        if sd and sh:
            if sd <= bd or sd >= bod * 0.98 or sh >= bh:
                return False

        gd = params.get("oil_groove_depth")
        if gd and gd >= (bod - bd) / 2 * 0.6:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bp = params.get("base_plane", "XY")
        variant = params.get("variant", "disc")
        bod = params["boss_diameter"]
        bh = params["boss_height"]
        bd = params["bore_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": variant == "disc",
            "pattern_like": True,
        }

        if variant == "disc":
            fod = params["flange_diameter"]
            ft = params["flange_thickness"]
            n = params["n_bolts"]
            bpr = params["bolt_pcd_radius"]
            blt_d = params["bolt_diameter"]

            # 1. Flange disc
            ops.append(Op("cylinder", {"height": ft, "radius": round(fod / 2, 3)}))

            # 2. Boss cylinder above flange — 0.5mm overlap into flange for clean fuse
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": plane_offset(
                                        bp, 0, 0, round(ft / 2 + bh / 2 - 0.5, 3)
                                    ),
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(bh, 3),
                                    "radius": round(bod / 2, 3),
                                },
                            },
                        ]
                    },
                )
            )

            # 3. Bolt holes through flange
            for i in range(n):
                ang = 2 * math.pi * i / n
                hx = round(bpr * math.cos(ang), 3)
                hy = round(bpr * math.sin(ang), 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": plane_offset(
                                            bp, hx, hy, round(ft / 2, 3)
                                        ),
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(ft * 2, 3),
                                        "radius": round(blt_d / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        else:  # ear variant: boss + web + round ear lugs
            col_h = params["collar_height"]
            ear_pcd = params["ear_pcd_radius"]
            ear_d = params["ear_diameter"]
            ear_w = round(ear_d * 0.90, 1)  # bar width close to ear_d for thick neck
            blt_d = params["bolt_diameter"]
            web_style = params.get("web_style", "bar")

            # 1. Boss cylinder (full height)
            ops.append(
                Op("cylinder", {"height": round(bh, 3), "radius": round(bod / 2, 3)})
            )

            # boss.cylinder() is centered → boss spans z=[-bh/2, +bh/2]
            # ears start 0.5mm below boss bottom for volumetric overlap (prevents Compound)
            z_bottom = round(-bh / 2 - 0.5, 3)
            z_ear = round(z_bottom + col_h / 2, 3)

            if web_style == "tangent":
                # Bone/dumbbell profile: two ear arcs + two boss arcs + tangent lines
                r1 = round(bod / 2, 3)
                r2 = round(ear_d / 2, 3)
                d = ear_pcd
                sin_a = max(-0.95, min(0.95, (r1 - r2) / d))
                cos_a = math.sqrt(1 - sin_a**2)
                a_ru = math.atan2(cos_a, sin_a)

                def _pt(angle, cx=0.0, cy=0.0, r=r1):
                    return [
                        round(cx + r * math.cos(angle), 3),
                        round(cy + r * math.sin(angle), 3),
                    ]

                p1u_r = _pt(a_ru, r=r1)
                p1l_r = _pt(-a_ru, r=r1)
                p1u_l = _pt(math.pi - a_ru, r=r1)
                p1l_l = _pt(-(math.pi - a_ru), r=r1)
                p2u_r = _pt(a_ru, cx=d, r=r2)
                p2l_r = _pt(-a_ru, cx=d, r=r2)
                p2u_l = _pt(math.pi - a_ru, cx=-d, r=r2)
                p2l_l = _pt(-(math.pi - a_ru), cx=-d, r=r2)
                ear_r_tip = [round(d + r2, 3), 0.0]
                ear_l_tip = [round(-d - r2, 3), 0.0]
                boss_top = [0.0, round(r1, 3)]
                boss_bot = [0.0, round(-r1, 3)]

                # 2. Tangent web: profile includes boss + tangent neck + ear lugs
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": plane_offset(bp, 0, 0, z_bottom),
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "moveTo",
                                    "args": {"x": p2l_r[0], "y": p2l_r[1]},
                                },
                                {
                                    "name": "threePointArc",
                                    "args": {"point1": ear_r_tip, "point2": p2u_r},
                                },
                                {
                                    "name": "lineTo",
                                    "args": {"x": p1u_r[0], "y": p1u_r[1]},
                                },
                                {
                                    "name": "threePointArc",
                                    "args": {"point1": boss_top, "point2": p1u_l},
                                },
                                {
                                    "name": "lineTo",
                                    "args": {"x": p2u_l[0], "y": p2u_l[1]},
                                },
                                {
                                    "name": "threePointArc",
                                    "args": {"point1": ear_l_tip, "point2": p2l_l},
                                },
                                {
                                    "name": "lineTo",
                                    "args": {"x": p1l_l[0], "y": p1l_l[1]},
                                },
                                {
                                    "name": "threePointArc",
                                    "args": {"point1": boss_bot, "point2": p1l_r},
                                },
                                {
                                    "name": "lineTo",
                                    "args": {"x": p2l_r[0], "y": p2l_r[1]},
                                },
                                {"name": "close", "args": {}},
                                {
                                    "name": "extrude",
                                    "args": {"distance": round(col_h, 3)},
                                },
                            ]
                        },
                    )
                )

            else:  # bar style
                # 2. Cross-bar web through center — overlap with boss, flush with bottom face
                bar_len = round(2 * (ear_pcd + ear_d / 2), 3)
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": plane_offset(bp, 0, 0, z_ear),
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": bar_len,
                                        "width": round(ear_w, 3),
                                        "height": round(col_h, 3),
                                        "centered": True,
                                    },
                                },
                            ]
                        },
                    )
                )

                # 3. Round ear lugs at ±ear_pcd — flush with bottom face
                for x_off in [round(ear_pcd, 3), round(-ear_pcd, 3)]:
                    ops.append(
                        Op(
                            "union",
                            {
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": plane_offset(bp, x_off, 0, z_ear),
                                            "rotate": [0, 0, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(col_h, 3),
                                            "radius": round(ear_d / 2, 3),
                                        },
                                    },
                                ]
                            },
                        )
                    )

            # Bolt holes through ear lugs (both styles)
            for x_off in [round(ear_pcd, 3), round(-ear_pcd, 3)]:
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": plane_offset(bp, x_off, 0, z_ear),
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(col_h * 3, 3),
                                        "radius": round(blt_d / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        # Boss top chamfer before bore (>Z has only outer edge before hole is cut)
        bc = params.get("boss_chamfer")
        if bc:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": bc}))

        # Center bore through boss (after chamfer so bore inner edge doesn't interfere)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bd, 3)}))

        # Shoulder step in bore (medium+)
        sd = params.get("shoulder_diameter")
        sh = params.get("shoulder_height")
        if sd and sh:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": plane_offset(bp, 0, 0, round(sh / 2, 3)),
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh * 1.1, 3),
                                    "radius": round(sd / 2, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # Oil seal groove on inner bore (hard)
        gw = params.get("oil_groove_width")
        gd_val = params.get("oil_groove_depth")
        if gw and gd_val:
            tags["has_slot"] = True
            ft_v = params.get("flange_thickness", 0)
            groove_z = round(ft_v + bh * 0.45, 3)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": plane_offset(bp, 0, 0, groove_z),
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(gw, 3),
                                    "radius": round(bd / 2 + gd_val, 3),
                                },
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
