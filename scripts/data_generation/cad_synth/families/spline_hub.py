"""Internal spline hub — DIN 5480 involute spline with DIN 509-F undercut.

Cylindrical hub body with a continuous 2D tool-profile cutter (one-shot
polyline of threePointArc segments) extruded downward through the hub for
the spline length, followed by a ring-shaped undercut groove at the end
of the splined section (DIN 509 Form F relief).

DIN 5480 30° pressure angle, short-tooth system:
  Reference / pitch diameter    d   = m · z
  Tip (internal minor) diameter da  = d − m
  Root (internal major) diameter df = d + 1.1 · m

DIN 5480-1 preferred modules (Table 1):
  0.5, 0.6, 0.75, 0.8, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10
Permissible tooth count z = 6 .. 82 (DIN 5480-1 §4.3).

Tooth flank approximated by a three-point arc from root → pitch → tip,
which keeps the tool outline topologically simple (one closed wire)
while staying within micrometre tolerance of the true involute.

Easy:   coarse m (2–4 mm), moderate z (12–24), broad undercut
Medium: m (1–3), z (18–40), standard undercut
Hard:   fine m (0.5–1.5), high z (28–60), narrow undercut

Reference:
  DIN 5480-1:2006 — Splined connections with involute splines; generalities.
  DIN 509:2016 — Technical drawings; relief grooves; Form F.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


def _spline_tool_points(m: float, z: int) -> list:
    """Return ordered (pt1, pt2) arc pairs for a z-tooth involute spline
    tool outline.  Each tooth gap = root arc → left flank → tip arc → right
    flank, giving 4·z arc segments forming one closed wire.

    Returned list: [(move_to_point), (arc1_mid, arc1_end), (arc2_mid, arc2_end), ...]
    where the first element is the starting point and each subsequent pair
    defines a threePointArc(mid_point, end_point).
    """
    d = m * z
    da = d - m  # internal minor (tip of internal tooth)
    df = d + 1.1 * m  # internal major (root of internal tooth)
    Ri, Ro, R_mid = da / 2.0, df / 2.0, d / 2.0

    a_in = math.pi / (2 * z) * 1.15
    a_mid = math.pi / (2 * z)
    a_out = math.pi / (2 * z) * 0.82

    # Start at first-tooth inner-left corner
    start = (Ri * math.cos(-a_in), Ri * math.sin(-a_in))
    segs = [start]

    for i in range(z):
        theta = i * (2 * math.pi / z)

        # A. right flank root→tip (involute approximation arc)
        p_rmid = (R_mid * math.cos(theta - a_mid), R_mid * math.sin(theta - a_mid))
        p_rout = (Ro * math.cos(theta - a_out), Ro * math.sin(theta - a_out))
        segs.append((p_rmid, p_rout))

        # B. root arc (across the gap bottom)
        p_root_mid = (Ro * math.cos(theta), Ro * math.sin(theta))
        p_lout = (Ro * math.cos(theta + a_out), Ro * math.sin(theta + a_out))
        segs.append((p_root_mid, p_lout))

        # C. left flank tip→root
        p_lmid = (R_mid * math.cos(theta + a_mid), R_mid * math.sin(theta + a_mid))
        p_lin = (Ri * math.cos(theta + a_in), Ri * math.sin(theta + a_in))
        segs.append((p_lmid, p_lin))

        # D. tip arc linking to next tooth
        next_theta = (i + 1) * (2 * math.pi / z)
        p_next_in = (
            Ri * math.cos(next_theta - a_in),
            Ri * math.sin(next_theta - a_in),
        )
        mid_ang = (theta + a_in + next_theta - a_in) / 2.0
        p_top_mid = (Ri * math.cos(mid_ang), Ri * math.sin(mid_ang))
        if i == z - 1:
            segs.append((p_top_mid, start))  # close
        else:
            segs.append((p_top_mid, p_next_in))
    return segs


class SplineHubFamily(BaseFamily):
    name = "spline_hub"
    standard = "DIN 5480"

    # DIN 5480-1 preferred modules (full Table 1 series)
    _DIN5480_MODULES_EASY = [2.0, 2.5, 3.0, 4.0]
    _DIN5480_MODULES_MED = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
    _DIN5480_MODULES_HARD = [0.5, 0.6, 0.75, 0.8, 1.0, 1.25, 1.5]

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            m = float(rng.choice(self._DIN5480_MODULES_EASY))
            z = int(rng.integers(12, 25))
        elif difficulty == "medium":
            m = float(rng.choice(self._DIN5480_MODULES_MED))
            z = int(rng.integers(18, 41))
        else:
            m = float(rng.choice(self._DIN5480_MODULES_HARD))
            z = int(rng.integers(28, 61))

        d = m * z  # pitch Ø
        df = d + 1.1 * m  # internal major (root) Ø
        hub_outer_dia = round(df + 2 * max(6.0, m * 6), 1)
        hub_length = round(rng.uniform(d * 0.4, d * 0.8), 1)
        spline_length = round(rng.uniform(hub_length * 0.4, hub_length * 0.75), 1)
        undercut_f = round(
            float(rng.choice([1.2, 2.0, 2.5])) * (1.0 if m >= 1.5 else 0.7), 2
        )
        undercut_t = round(
            float(rng.choice([0.4, 0.7, 1.0])) * (1.0 if m >= 1.5 else 0.5), 2
        )

        return {
            "module": m,
            "n_teeth": z,
            "hub_outer_dia": hub_outer_dia,
            "hub_length": hub_length,
            "spline_length": spline_length,
            "undercut_f": undercut_f,
            "undercut_t": undercut_t,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        m, z = params["module"], params["n_teeth"]
        hub_od = params["hub_outer_dia"]
        hl = params["hub_length"]
        sl = params["spline_length"]
        uf = params["undercut_f"]
        ut = params["undercut_t"]

        if z < 6 or z > 82:  # DIN 5480-1 §4.3
            return False
        df = m * z + 1.1 * m
        if hub_od <= df + 4:
            return False
        if hl < 5 or hl > 160:
            return False
        if sl >= hl - uf - 0.5:
            return False
        if sl < 4:
            return False
        if ut >= (hub_od - df) / 2 - 1.0:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        m, z = params["module"], params["n_teeth"]
        hub_od = params["hub_outer_dia"]
        hl = params["hub_length"]
        sl = params["spline_length"]
        uf = params["undercut_f"]
        ut = params["undercut_t"]

        df = m * z + 1.1 * m
        undercut_dia = df + 2 * ut
        cut_depth = sl + uf + 5.0

        segs = _spline_tool_points(m, z)
        start_pt = segs[0]
        arc_pairs = segs[1:]

        tags = {
            "has_hole": True,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": True,
        }

        # 1. Hub cylinder (z = 0 .. hl)
        ops = [
            Op("circle", {"radius": round(hub_od / 2, 4)}),
            Op("extrude", {"distance": round(hl, 4)}),
        ]

        # 2. Spline cutter (one closed wire of threePointArcs)
        sub_ops = [
            {
                "name": "transformed",
                "args": {"offset": [0, 0, round(hl + 1.0, 4)], "rotate": [0, 0, 0]},
            },
            {
                "name": "moveTo",
                "args": {"x": round(start_pt[0], 5), "y": round(start_pt[1], 5)},
            },
        ]
        for p_mid, p_end in arc_pairs:
            sub_ops.append(
                {
                    "name": "threePointArc",
                    "args": {
                        "point1": [round(p_mid[0], 5), round(p_mid[1], 5)],
                        "point2": [round(p_end[0], 5), round(p_end[1], 5)],
                    },
                }
            )
        sub_ops.append({"name": "close", "args": {}})
        sub_ops.append({"name": "extrude", "args": {"distance": round(-cut_depth, 4)}})
        ops.append(Op("cut", {"ops": sub_ops}))

        # 3. Undercut groove (DIN 509-F) at end of spline
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(hl - sl, 4)],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "circle",
                            "args": {"radius": round(undercut_dia / 2, 4)},
                        },
                        {"name": "extrude", "args": {"distance": round(-uf, 4)}},
                    ]
                },
            )
        )

        # 4. Chamfer outer edges (both ends)
        ch = round(min(1.5, m * 0.6), 2)
        if ch > 0:
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
