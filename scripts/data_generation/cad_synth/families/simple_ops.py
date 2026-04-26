"""simple_ops — synthetic families focused on individual CadQuery ops.

Goal: maximize per-op coverage and op-composition diversity for model
training. Not ISO-faithful — pure procedural geometry that exercises
revolve, loft, sweep (helix/spline), twistExtrude, polarArray, mirror,
union, cut.

Each family showcases ONE focal op with minimal scaffolding so the model
learns the op semantics rather than family-template patterns.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# Profile shapes shared by sweep / twist families. All centered at workplane
# origin so callers can `Op("center", ...)` to relocate the profile to the
# sweep path start point.
PROFILE_KINDS = ("circle", "rect", "ellipse", "polygon", "slot", "star", "T", "L", "cross")


def _profile_ops(kind: str, s: float, polygon_n: int = 4) -> list:
    """Return Ops drawing a closed profile centered at the workplane origin."""
    if kind == "circle":
        return [Op("circle", {"radius": round(s, 3)})]
    if kind == "rect":
        return [Op("rect", {"length": round(s * 2, 3), "width": round(s * 1.2, 3)})]
    if kind == "ellipse":
        return [Op("ellipse", {"xRadius": round(s * 1.5, 3), "yRadius": round(s * 0.9, 3)})]
    if kind == "polygon":
        return [Op("polygon", {"n": polygon_n, "diameter": round(s * 2, 3)})]
    if kind == "slot":
        return [Op("slot2D", {"length": round(s * 2.5, 3), "width": round(s, 3)})]
    if kind == "star":
        n = 5
        r_out, r_in = s, s * 0.45
        pts = []
        for i in range(2 * n):
            ang = math.pi / 2 - i * math.pi / n
            rr = r_out if i % 2 == 0 else r_in
            pts.append((round(rr * math.cos(ang), 3), round(rr * math.sin(ang), 3)))
        return [Op("polyline", {"points": pts}), Op("close", {})]
    if kind == "T":
        w, h = s * 2, s * 1.4
        bw = s * 0.5
        sw = s * 0.6
        pts = [
            (-w / 2, h / 2 - bw), (-w / 2, h / 2), (w / 2, h / 2), (w / 2, h / 2 - bw),
            (sw / 2, h / 2 - bw), (sw / 2, -h / 2),
            (-sw / 2, -h / 2), (-sw / 2, h / 2 - bw),
        ]
        pts = [(round(x, 3), round(y, 3)) for x, y in pts]
        return [Op("polyline", {"points": pts}), Op("close", {})]
    if kind == "L":
        w, h, t = s * 1.8, s * 1.8, s * 0.5
        pts = [
            (-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, -h / 2 + t),
            (-w / 2 + t, -h / 2 + t), (-w / 2 + t, h / 2), (-w / 2, h / 2),
        ]
        pts = [(round(x, 3), round(y, 3)) for x, y in pts]
        return [Op("polyline", {"points": pts}), Op("close", {})]
    if kind == "cross":
        w, a = s * 1.8, s * 0.5
        pts = [
            (-a / 2, -w / 2), (a / 2, -w / 2), (a / 2, -a / 2),
            (w / 2, -a / 2), (w / 2, a / 2), (a / 2, a / 2),
            (a / 2, w / 2), (-a / 2, w / 2), (-a / 2, a / 2),
            (-w / 2, a / 2), (-w / 2, -a / 2), (-a / 2, -a / 2),
        ]
        pts = [(round(x, 3), round(y, 3)) for x, y in pts]
        return [Op("polyline", {"points": pts}), Op("close", {})]
    raise ValueError(f"Unknown profile kind: {kind}")


# --- simple_revolve ---------------------------------------------------------


class SimpleRevolveFamily(BaseFamily):
    name = "simple_revolve"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "profile_kind": str(rng.choice(["L", "stepped", "trapezoid", "T"])),
            "scale": round(float(rng.uniform(8, 22)), 1),
            "angle_deg": float(rng.choice([90, 180, 270, 360])),
            "axis": str(rng.choice(["Y", "Y_offset"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["scale"] >= 5 and p["angle_deg"] >= 30

    def make_program(self, p):
        s = p["scale"]
        kind = p["profile_kind"]
        if kind == "L":
            pts = [
                (s * 0.5, 0.0), (s * 1.5, 0.0), (s * 1.5, s * 0.3),
                (s * 0.7, s * 0.3), (s * 0.7, s * 1.2), (s * 0.5, s * 1.2),
            ]
        elif kind == "stepped":
            pts = [
                (s * 0.4, 0.0), (s * 1.4, 0.0), (s * 1.4, s * 0.4),
                (s * 1.0, s * 0.4), (s * 1.0, s * 0.9), (s * 0.7, s * 0.9),
                (s * 0.7, s * 1.4), (s * 0.4, s * 1.4),
            ]
        elif kind == "trapezoid":
            pts = [(s * 0.3, 0.0), (s * 1.5, 0.0), (s * 1.2, s * 1.1), (s * 0.4, s * 1.1)]
        else:
            pts = [
                (s * 0.4, 0.0), (s * 1.6, 0.0), (s * 1.6, s * 0.3),
                (s * 0.9, s * 0.3), (s * 0.9, s * 1.2), (s * 0.6, s * 1.2),
                (s * 0.6, s * 0.3), (s * 0.4, s * 0.3),
            ]
        pts = [(round(x, 3), round(y, 3)) for x, y in pts]

        offset = s * 0.4 if p["axis"] == "Y_offset" else 0.0
        ops = [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {
                    "angleDeg": p["angle_deg"],
                    "axisStart": (-offset, 0, 0),
                    "axisEnd": (-offset, 1, 0),
                },
            )
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"revolve_angle": p["angle_deg"], "axis": p["axis"]},
        )


# --- simple_loft ------------------------------------------------------------


class SimpleLoftFamily(BaseFamily):
    name = "simple_loft"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        n = int(rng.choice([2, 3, 3]))
        kinds = [str(rng.choice(["circle", "rect", "polygon", "ellipse"])) for _ in range(n)]
        scales = [round(float(rng.uniform(8, 20)), 1) for _ in range(n)]
        return {
            "n_sections": n,
            "section_kinds": kinds,
            "scales": scales,
            "height": round(float(rng.uniform(15, 45)), 1),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        if p["height"] < 5 or any(s < 4 for s in p["scales"]):
            return False
        return True

    def make_program(self, p):
        n = p["n_sections"]
        kinds = p["section_kinds"]
        scales = p["scales"]
        h = p["height"]
        pn = p["polygon_n"]

        ops = []
        dz = h / max(1, n - 1) if n > 1 else 0.0
        for i in range(n):
            if i > 0:
                ops.append(
                    Op("transformed", {"offset": [0, 0, round(i * dz, 3)], "rotate": [0, 0, 0]})
                )
            k = kinds[i]
            r = scales[i]
            if k == "circle":
                ops.append(Op("circle", {"radius": round(r, 3)}))
            elif k == "rect":
                ops.append(Op("rect", {"length": round(r * 1.5, 3), "width": round(r, 3)}))
            elif k == "ellipse":
                ops.append(Op("ellipse", {"xRadius": round(r * 1.3, 3), "yRadius": round(r * 0.8, 3)}))
            else:
                ops.append(Op("polygon", {"n": pn, "diameter": round(r * 2, 3)}))
        ops.append(Op("loft", {"combine": True}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"loft_sections": n},
        )


# --- simple_sweep_helix -----------------------------------------------------


class SimpleSweepHelixFamily(BaseFamily):
    name = "simple_sweep_helix"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "profile_kind": str(rng.choice(PROFILE_KINDS)),
            "profile_size": round(float(rng.uniform(2.5, 5.5)), 2),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "pitch": round(float(rng.uniform(8, 22)), 1),
            "height": round(float(rng.uniform(30, 90)), 1),
            "radius": round(float(rng.uniform(10, 28)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["profile_size"] > 1.0 and p["radius"] > p["profile_size"] * 1.8

    def make_program(self, p):
        ops = [Op("center", {"x": p["radius"], "y": 0})]
        ops.extend(_profile_ops(p["profile_kind"], p["profile_size"], p["polygon_n"]))
        ops.append(
            Op(
                "sweep",
                {
                    "path_type": "helix",
                    "path_args": {
                        "pitch": p["pitch"],
                        "height": p["height"],
                        "radius": p["radius"],
                    },
                    "isFrenet": True,
                },
            )
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"sweep_path": "helix", "profile": p["profile_kind"]},
        )


# --- simple_sweep_spline ----------------------------------------------------


class SimpleSweepSplineFamily(BaseFamily):
    name = "simple_sweep_spline"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        # Snake-curve path: STRICTLY monotonic in x, gentle z waves — never coils
        # so the result is visually distinct from twist_sweep (which is a coil).
        n_ctl = int(rng.choice([4, 5, 6]))
        pts = [(0.0, 0.0)]
        x, z = 0.0, 0.0
        for _ in range(n_ctl):
            x += round(float(rng.uniform(15, 28)), 1)  # always large positive
            z += round(float(rng.uniform(-14, 14)), 1)
            pts.append((round(x, 1), round(z, 1)))
        # Smooth tube look: prefer round/regular profiles; exclude T/L/cross/star/slot
        # so it is unmistakable as "tube along curve" rather than "twisted ribbon".
        smooth_kinds = ("circle", "ellipse", "polygon", "rect")
        return {
            "profile_kind": str(rng.choice(smooth_kinds)),
            "profile_size": round(float(rng.uniform(4.0, 8.0)), 2),
            "polygon_n": int(rng.choice([5, 6, 8])),
            "spline_pts_xz": [list(p) for p in pts],
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return len(p["spline_pts_xz"]) >= 3 and p["profile_size"] > 2

    def make_program(self, p):
        ops = list(_profile_ops(p["profile_kind"], p["profile_size"], p["polygon_n"]))
        ops.append(
            Op(
                "sweep",
                {
                    "path_type": "spline",
                    "path_points": p["spline_pts_xz"],
                    "path_plane": "XZ",
                    "isFrenet": True,
                },
            )
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"sweep_path": "spline", "profile": p["profile_kind"]},
        )


# --- simple_twist_extrude ---------------------------------------------------


class SimpleTwistExtrudeFamily(BaseFamily):
    name = "simple_twist_extrude"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        # Twist needs non-rotational profile to be visible — exclude circle/ellipse.
        kinds = tuple(k for k in PROFILE_KINDS if k not in ("circle", "ellipse"))
        return {
            "profile_kind": str(rng.choice(kinds)),
            "polygon_n": int(rng.choice([3, 4, 5, 6])),
            "profile_size": round(float(rng.uniform(8, 18)), 1),
            "height": round(float(rng.uniform(20, 60)), 1),
            "twist_deg": float(rng.choice([45, 90, 180, 270, 360, 540, 720])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["profile_size"] > 4 and p["height"] > 5

    def make_program(self, p):
        ops = list(_profile_ops(p["profile_kind"], p["profile_size"], p["polygon_n"]))
        ops.append(Op("twistExtrude", {"distance": p["height"], "angle": p["twist_deg"]}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"twist_deg": p["twist_deg"], "profile": p["profile_kind"]},
        )


# --- simple_twist_sweep -----------------------------------------------------


class SimpleTwistSweepFamily(BaseFamily):
    """Non-circular profile + helix sweep — ribbon-twist look."""

    name = "simple_twist_sweep"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        # Non-rotational profile only — coil must look twisted, not like a tube.
        # Heavy bias to ribbon-y / pointy shapes (rect/star/cross/T/L/slot).
        kinds = ("rect", "polygon", "star", "T", "L", "cross", "slot")
        # Force height/pitch >= 3 so multiple turns are always visible.
        pitch = round(float(rng.uniform(8, 16)), 1)
        height = round(float(rng.uniform(pitch * 4, pitch * 7)), 1)
        return {
            "profile_kind": str(rng.choice(kinds)),
            "polygon_n": int(rng.choice([3, 4, 5, 6])),
            "profile_size": round(float(rng.uniform(4.5, 8.0)), 2),
            "pitch": pitch,
            "height": height,
            "radius": round(float(rng.uniform(15, 28)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        # Profile must comfortably fit inside the helix radius.
        return p["profile_size"] < p["radius"] * 0.5

    def make_program(self, p):
        ops = [Op("center", {"x": p["radius"], "y": 0})]
        ops.extend(_profile_ops(p["profile_kind"], p["profile_size"], p["polygon_n"]))
        ops.append(
            Op(
                "sweep",
                {
                    "path_type": "helix",
                    "path_args": {
                        "pitch": p["pitch"],
                        "height": p["height"],
                        "radius": p["radius"],
                    },
                    "isFrenet": True,
                },
            )
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"twist_sweep": True, "profile": p["profile_kind"]},
        )


# --- simple_polar_array -----------------------------------------------------


class SimplePolarArrayFamily(BaseFamily):
    name = "simple_polar_array"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        hub_r = round(float(rng.uniform(20, 35)), 1)
        return {
            "hub_radius": hub_r,
            "hub_thick": round(float(rng.uniform(6, 14)), 1),
            "feature_kind": str(rng.choice(["cylinder", "rect", "polygon"])),
            "feature_size": round(float(rng.uniform(3, 7)), 1),
            "feature_count": int(rng.choice([4, 6, 8, 10, 12])),
            "feature_radius": round(hub_r * 0.7, 1),
            "polygon_n": int(rng.choice([3, 4, 6])),
            "feature_height": round(float(rng.uniform(8, 18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["feature_size"] < p["hub_radius"] * 0.5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["hub_radius"]}),
            Op("extrude", {"distance": p["hub_thick"]}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": p["feature_radius"],
                    "startAngle": 0,
                    "angle": 360,
                    "count": p["feature_count"],
                },
            ),
        ]
        k = p["feature_kind"]
        s = p["feature_size"]
        if k == "cylinder":
            ops.append(Op("circle", {"radius": s}))
        elif k == "rect":
            ops.append(Op("rect", {"length": s * 2, "width": s}))
        else:
            ops.append(Op("polygon", {"n": p["polygon_n"], "diameter": s * 2}))
        ops.append(Op("extrude", {"distance": p["feature_height"]}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"polar_count": p["feature_count"]},
        )


# --- simple_union -----------------------------------------------------------


def _primitive_sub_ops(kind: str, size: float, polygon_n: int, offset: tuple) -> list:
    """Build a sub-program (list of dicts) that creates one primitive at offset."""
    ox, oy, oz = offset
    sub = [{"name": "transformed",
            "args": {"offset": [round(ox, 2), round(oy, 2), round(oz, 2)],
                     "rotate": [0, 0, 0]}}]
    if kind == "cylinder":
        sub.append({"name": "cylinder",
                    "args": {"height": round(size * 1.6, 2), "radius": round(size * 0.55, 2)}})
    elif kind == "box":
        sub.append({"name": "box",
                    "args": {"length": round(size * 1.4, 2),
                             "width": round(size, 2),
                             "height": round(size * 0.9, 2)}})
    elif kind == "sphere":
        sub.append({"name": "sphere", "args": {"radius": round(size * 0.7, 2)}})
    elif kind == "polygon_prism":
        sub.append({"name": "polygon",
                    "args": {"n": polygon_n, "diameter": round(size * 1.5, 2)}})
        sub.append({"name": "extrude",
                    "args": {"distance": round(size * 0.8, 2), "both": True}})
    else:
        raise ValueError(f"Unknown sub kind: {kind}")
    return sub


class SimpleUnionFamily(BaseFamily):
    """Base solid + 1–2 union'd sub-primitives at offsets."""

    name = "simple_union"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        bs = round(float(rng.uniform(15, 28)), 1)
        return {
            "base_kind": str(rng.choice(["cylinder", "box", "sphere"])),
            "base_size": bs,
            "sub_kind": str(rng.choice(["cylinder", "box", "sphere", "polygon_prism"])),
            "sub_size": round(float(rng.uniform(8, 16)), 1),
            "polygon_n": int(rng.choice([3, 4, 5, 6])),
            "n_subs": int(rng.choice([1, 1, 2])),
            "offsets": [
                [round(float(rng.uniform(-bs * 0.6, bs * 0.6)), 1),
                 round(float(rng.uniform(-bs * 0.4, bs * 0.4)), 1),
                 round(float(rng.uniform(0, bs * 0.8)), 1)],
                [round(float(rng.uniform(-bs * 0.6, bs * 0.6)), 1),
                 round(float(rng.uniform(-bs * 0.4, bs * 0.4)), 1),
                 round(float(rng.uniform(-bs * 0.5, bs * 0.5)), 1)],
            ],
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["base_size"] > 8 and p["sub_size"] > 4

    def make_program(self, p):
        bs = p["base_size"]
        ops = []
        if p["base_kind"] == "cylinder":
            ops.append(Op("cylinder", {"height": round(bs * 1.2, 2), "radius": round(bs * 0.6, 2)}))
        elif p["base_kind"] == "box":
            ops.append(Op("box", {"length": round(bs * 1.4, 2), "width": round(bs, 2),
                                  "height": round(bs * 0.8, 2)}))
        else:
            ops.append(Op("sphere", {"radius": round(bs * 0.75, 2)}))

        for i in range(p["n_subs"]):
            sub = _primitive_sub_ops(p["sub_kind"], p["sub_size"], p["polygon_n"], tuple(p["offsets"][i]))
            ops.append(Op("union", {"ops": sub, "plane": "XY"}))

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"n_unions": p["n_subs"], "sub_kind": p["sub_kind"]},
        )


# --- simple_cut -------------------------------------------------------------


class SimpleCutFamily(BaseFamily):
    """Base solid - 1–2 cut sub-primitives → notches / through-holes / pockets."""

    name = "simple_cut"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        bs = round(float(rng.uniform(20, 35)), 1)
        return {
            "base_kind": str(rng.choice(["cylinder", "box"])),
            "base_size": bs,
            "cut_kind": str(rng.choice(["cylinder", "box", "polygon_prism", "sphere"])),
            "cut_size": round(float(rng.uniform(0.25, 0.55)) * bs, 1),
            "polygon_n": int(rng.choice([3, 4, 6, 8])),
            "n_cuts": int(rng.choice([1, 2])),
            "offsets": [
                [round(float(rng.uniform(-bs * 0.4, bs * 0.4)), 1),
                 round(float(rng.uniform(-bs * 0.3, bs * 0.3)), 1),
                 round(float(rng.uniform(-bs * 0.3, bs * 0.3)), 1)],
                [round(float(rng.uniform(-bs * 0.4, bs * 0.4)), 1),
                 round(float(rng.uniform(-bs * 0.3, bs * 0.3)), 1),
                 round(float(rng.uniform(-bs * 0.3, bs * 0.3)), 1)],
            ],
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["cut_size"] < p["base_size"] * 0.7 and p["cut_size"] > 3

    def make_program(self, p):
        bs = p["base_size"]
        ops = []
        if p["base_kind"] == "cylinder":
            ops.append(Op("cylinder", {"height": round(bs * 1.2, 2), "radius": round(bs * 0.6, 2)}))
        else:
            ops.append(Op("box", {"length": round(bs * 1.4, 2), "width": round(bs, 2),
                                  "height": round(bs, 2)}))

        # For cuts we make sub primitives oversized so they pass through.
        cut_oversize = bs * 1.8
        for i in range(p["n_cuts"]):
            sub = _primitive_sub_ops(p["cut_kind"], p["cut_size"], p["polygon_n"], tuple(p["offsets"][i]))
            # Override last primitive args to extend through base when relevant.
            last = sub[-1]
            if last["name"] == "cylinder":
                last["args"]["height"] = round(cut_oversize, 2)
            elif last["name"] == "box":
                last["args"]["height"] = round(cut_oversize, 2)
            elif last["name"] == "extrude":
                last["args"]["distance"] = round(cut_oversize / 2, 2)
                last["args"]["both"] = True
            ops.append(Op("cut", {"ops": sub, "plane": "XY"}))

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"n_cuts": p["n_cuts"], "cut_kind": p["cut_kind"]},
        )


# --- simple_fillet ----------------------------------------------------------


class SimpleFilletFamily(BaseFamily):
    """Base solid + fillet on a chosen edge subset (>Z / <Z / |Z / all)."""

    name = "simple_fillet"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        base = str(rng.choice(["box", "cylinder", "stepped"]))
        # cylinder lateral surface has no |Z edges — exclude.
        if base == "cylinder":
            sel = str(rng.choice([">Z", "<Z", "all"]))
        else:
            sel = str(rng.choice([">Z", "<Z", "|Z", "all"]))
        return {
            "base_kind": base,
            "scale": round(float(rng.uniform(20, 35)), 1),
            "fillet_radius": round(float(rng.uniform(1.5, 5.0)), 1),
            "edge_selector": sel,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["fillet_radius"] < p["scale"] * 0.22 and p["scale"] > 8

    def make_program(self, p):
        s = p["scale"]
        ops = []
        if p["base_kind"] == "box":
            ops.append(Op("box", {"length": round(s * 1.4, 2),
                                  "width": round(s, 2),
                                  "height": round(s * 0.8, 2)}))
        elif p["base_kind"] == "cylinder":
            ops.append(Op("cylinder", {"height": round(s * 1.0, 2),
                                       "radius": round(s * 0.55, 2)}))
        else:  # stepped — bigger box base + smaller box on top
            ops.append(Op("box", {"length": round(s * 1.4, 2),
                                  "width": round(s, 2),
                                  "height": round(s * 0.5, 2)}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("rect", {"length": round(s * 0.9, 2),
                                   "width": round(s * 0.6, 2)}))
            ops.append(Op("extrude", {"distance": round(s * 0.5, 2)}))

        if p["edge_selector"] != "all":
            ops.append(Op("edges", {"selector": p["edge_selector"]}))
        ops.append(Op("fillet", {"radius": p["fillet_radius"]}))

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "fillet_radius": p["fillet_radius"],
                "edge_selector": p["edge_selector"],
                "base": p["base_kind"],
            },
        )


# --- simple_taper_extrude ---------------------------------------------------


class SimpleTaperExtrudeFamily(BaseFamily):
    """Profile + tapered extrude (extrude with taper-deg arg) — frusta and pyramids."""

    name = "simple_taper_extrude"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        # Avoid star/cross/T/L (concave) — taper on concave wires often fails.
        kinds = ("circle", "rect", "ellipse", "polygon", "slot")
        return {
            "profile_kind": str(rng.choice(kinds)),
            "profile_size": round(float(rng.uniform(10, 22)), 1),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "height": round(float(rng.uniform(15, 35)), 1),
            "taper_deg": float(rng.choice([-15, -10, -5, 5, 10, 15, 20])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["profile_size"] > 5 and p["height"] > 5 and abs(p["taper_deg"]) <= 25

    def make_program(self, p):
        ops = list(_profile_ops(p["profile_kind"], p["profile_size"], p["polygon_n"]))
        ops.append(Op("extrude", {"distance": p["height"], "taper": p["taper_deg"]}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"taper_deg": p["taper_deg"], "profile": p["profile_kind"]},
        )


# --- simple_compose ---------------------------------------------------------


def _rare_op_solid_ops(rare: str, s: float, polygon_n: int) -> list:
    """Build a solid using one rare op (revolve/loft/sweep_*/twist_*/taper_extrude).

    Output is the Op sequence to apply on the current Workplane. Solid is sized
    around `s` so subsequent compose primitives can be sized relative to it.
    """
    if rare == "revolve":
        pts = [
            (s * 0.45, 0.0), (s * 1.3, 0.0), (s * 1.3, s * 0.4),
            (s * 0.7, s * 0.4), (s * 0.7, s * 1.0), (s * 0.45, s * 1.0),
        ]
        pts = [(round(x, 3), round(y, 3)) for x, y in pts]
        ops = [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(Op("revolve", {"angleDeg": 360,
                                  "axisStart": (0, 0, 0), "axisEnd": (0, 1, 0)}))
        return ops
    if rare == "loft":
        return [
            Op("circle", {"radius": round(s * 0.55, 3)}),
            Op("transformed", {"offset": [0, 0, round(s * 1.2, 3)], "rotate": [0, 0, 0]}),
            Op("rect", {"length": round(s * 0.9, 3), "width": round(s * 0.7, 3)}),
            Op("loft", {"combine": True}),
        ]
    if rare == "sweep_helix":
        r = round(s * 0.7, 3)
        return [
            Op("center", {"x": r, "y": 0}),
            Op("circle", {"radius": round(s * 0.18, 3)}),
            Op("sweep", {
                "path_type": "helix",
                "path_args": {"pitch": round(s * 0.5, 3),
                              "height": round(s * 1.6, 3), "radius": r},
                "isFrenet": True,
            }),
        ]
    if rare == "sweep_spline":
        pts = [[0.0, 0.0], [s * 0.9, s * 0.4], [s * 1.7, -s * 0.3], [s * 2.4, s * 0.5]]
        return [
            Op("circle", {"radius": round(s * 0.22, 3)}),
            Op("sweep", {
                "path_type": "spline", "path_points": pts,
                "path_plane": "XZ", "isFrenet": True,
            }),
        ]
    if rare == "twist_extrude":
        return [
            Op("polygon", {"n": polygon_n, "diameter": round(s * 1.4, 3)}),
            Op("twistExtrude", {"distance": round(s * 1.5, 3), "angle": 180.0}),
        ]
    if rare == "twist_sweep":
        r = round(s * 0.7, 3)
        return [
            Op("center", {"x": r, "y": 0}),
            Op("rect", {"length": round(s * 0.5, 3), "width": round(s * 0.18, 3)}),
            Op("sweep", {
                "path_type": "helix",
                "path_args": {"pitch": round(s * 0.55, 3),
                              "height": round(s * 1.8, 3), "radius": r},
                "isFrenet": True,
            }),
        ]
    if rare == "taper_extrude":
        return [
            Op("rect", {"length": round(s * 1.2, 3), "width": round(s * 1.0, 3)}),
            Op("extrude", {"distance": round(s * 1.3, 3), "taper": -10.0}),
        ]
    raise ValueError(f"Unknown rare op: {rare}")


class SimpleComposeFamily(BaseFamily):
    """Rare-op solid + union/cut with a basic primitive (box/cylinder/sphere).

    Goal: model sees rare ops in composition with booleans, not just standalone.
    """

    name = "simple_compose"
    standard = "N/A"

    RARE_OPS = (
        "revolve", "loft", "sweep_helix", "sweep_spline",
        "twist_extrude", "twist_sweep", "taper_extrude",
    )

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(15, 25)), 1)
        return {
            "rare_op": str(rng.choice(self.RARE_OPS)),
            "boolean": str(rng.choice(["union", "cut"])),
            "basic_primitive": str(rng.choice(["box", "cylinder", "sphere"])),
            "scale": s,
            "prim_size": round(float(rng.uniform(s * 0.35, s * 0.7)), 1),
            "polygon_n": int(rng.choice([3, 4, 6])),
            "offset": [
                round(float(rng.uniform(-s * 0.4, s * 0.4)), 1),
                round(float(rng.uniform(-s * 0.4, s * 0.4)), 1),
                round(float(rng.uniform(s * 0.0, s * 0.7)), 1),
            ],
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["scale"] > 8 and p["prim_size"] > 3

    def make_program(self, p):
        ops = _rare_op_solid_ops(p["rare_op"], p["scale"], p["polygon_n"])
        sub = _primitive_sub_ops(
            p["basic_primitive"], p["prim_size"], p["polygon_n"], tuple(p["offset"])
        )
        if p["boolean"] == "cut":
            # Oversize cut primitive so it actually pierces the solid.
            last = sub[-1]
            if last["name"] in ("cylinder", "box"):
                last["args"]["height"] = round(p["scale"] * 2.5, 2)
        ops.append(Op(p["boolean"], {"ops": sub, "plane": "XY"}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "rare_op": p["rare_op"],
                "boolean": p["boolean"],
                "primitive": p["basic_primitive"],
            },
        )


# --- simple_polyline --------------------------------------------------------


class SimplePolylineFamily(BaseFamily):
    """Closed polyline (random N-gon with varying radii) → extrude.

    Showcases the polyline op as a primary wire-builder (vs sketch primitives).
    """

    name = "simple_polyline"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        n = int(rng.choice([5, 6, 7, 8, 10, 12]))
        scale = round(float(rng.uniform(15, 30)), 1)
        # Vertex radii mix so result is clearly an irregular polygon, not a clean ngon.
        radii = [round(scale * float(rng.uniform(0.55, 1.0)), 2) for _ in range(n)]
        return {
            "n_points": n,
            "scale": scale,
            "radii": radii,
            "thickness": round(float(rng.uniform(5, 18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["scale"] > 8 and min(p["radii"]) > 3 and len(p["radii"]) >= 4

    def make_program(self, p):
        n = p["n_points"]
        radii = p["radii"]
        pts = []
        for i in range(n):
            ang = 2 * math.pi * i / n
            r = radii[i]
            pts.append((round(r * math.cos(ang), 3), round(r * math.sin(ang), 3)))
        ops = [
            Op("polyline", {"points": pts}),
            Op("close", {}),
            Op("extrude", {"distance": round(p["thickness"], 3)}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"polyline_n": n},
        )


# --- simple_arc -------------------------------------------------------------


class SimpleArcFamily(BaseFamily):
    """threePointArc-built profile (capsule / lens / teardrop) → extrude.

    Showcases the threePointArc op constructing curved wire segments.
    """

    name = "simple_arc"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "kind": str(rng.choice(["capsule", "lens", "teardrop", "double_arc"])),
            "scale": round(float(rng.uniform(15, 28)), 1),
            "thickness": round(float(rng.uniform(5, 18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["scale"] > 8

    def make_program(self, p):
        s = p["scale"]
        kind = p["kind"]
        if kind == "capsule":
            ops = [
                Op("moveTo", {"x": -s, "y": -s / 2}),
                Op("lineTo", {"x": s, "y": -s / 2}),
                Op("threePointArc", {"point1": [s + s / 2, 0.0], "point2": [s, s / 2]}),
                Op("lineTo", {"x": -s, "y": s / 2}),
                Op("threePointArc", {"point1": [-s - s / 2, 0.0], "point2": [-s, -s / 2]}),
                Op("close", {}),
            ]
        elif kind == "lens":
            ops = [
                Op("moveTo", {"x": -s, "y": 0.0}),
                Op("threePointArc", {"point1": [0.0, s * 0.55], "point2": [s, 0.0]}),
                Op("threePointArc", {"point1": [0.0, -s * 0.55], "point2": [-s, 0.0]}),
                Op("close", {}),
            ]
        elif kind == "teardrop":
            ops = [
                Op("moveTo", {"x": s, "y": 0.0}),
                Op("lineTo", {"x": -s * 0.5, "y": s * 0.7}),
                Op("threePointArc", {"point1": [-s, 0.0], "point2": [-s * 0.5, -s * 0.7]}),
                Op("close", {}),
            ]
        else:  # double_arc — pill with one straight side
            ops = [
                Op("moveTo", {"x": -s, "y": -s / 2}),
                Op("lineTo", {"x": s, "y": -s / 2}),
                Op("threePointArc", {"point1": [0.0, s * 0.9], "point2": [-s, -s / 2]}),
                Op("close", {}),
            ]
        ops.append(Op("extrude", {"distance": round(p["thickness"], 3)}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"arc_kind": kind},
        )


# --- simple_polygon ---------------------------------------------------------


class SimplePolygonFamily(BaseFamily):
    """Pure polygon primitive at varied N (3–16) + extrude with optional rotation."""

    name = "simple_polygon"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "n_sides": int(rng.choice([3, 4, 5, 6, 7, 8, 10, 12, 16])),
            "diameter": round(float(rng.uniform(18, 40)), 1),
            "height": round(float(rng.uniform(8, 28)), 1),
            "rotation_deg": float(rng.choice([0, 15, 30, 45])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["diameter"] > 6 and p["height"] > 2 and p["n_sides"] >= 3

    def make_program(self, p):
        ops = []
        if p["rotation_deg"] != 0:
            ops.append(
                Op("transformed", {"offset": [0, 0, 0], "rotate": [0, 0, p["rotation_deg"]]})
            )
        ops.extend(
            [
                Op("polygon", {"n": p["n_sides"], "diameter": round(p["diameter"], 3)}),
                Op("extrude", {"distance": round(p["height"], 3)}),
            ]
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"n_sides": p["n_sides"], "rotation_deg": p["rotation_deg"]},
        )


# --- simple_sphere ----------------------------------------------------------


class SimpleSphereFamily(BaseFamily):
    """Sphere primitive — single sphere, two-sphere union, or sphere ± rod / cap."""

    name = "simple_sphere"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "kind": str(rng.choice(["single", "two_union", "sphere_rod", "sphere_cut"])),
            "radius": round(float(rng.uniform(12, 24)), 1),
            "second_radius": round(float(rng.uniform(6, 13)), 1),
            "second_offset": round(float(rng.uniform(10, 22)), 1),
            "rod_radius": round(float(rng.uniform(3, 6)), 1),
            "rod_height": round(float(rng.uniform(18, 35)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] > 5 and p["second_radius"] < p["radius"]

    def make_program(self, p):
        r = p["radius"]
        kind = p["kind"]
        ops = [Op("sphere", {"radius": round(r, 3)})]
        if kind == "two_union":
            sub = [
                {"name": "transformed",
                 "args": {"offset": [round(p["second_offset"], 2), 0, 0], "rotate": [0, 0, 0]}},
                {"name": "sphere", "args": {"radius": round(p["second_radius"], 3)}},
            ]
            ops.append(Op("union", {"ops": sub, "plane": "XY"}))
        elif kind == "sphere_rod":
            sub = [
                {"name": "transformed",
                 "args": {"offset": [0, 0, round(r * 0.4, 2)], "rotate": [0, 0, 0]}},
                {"name": "cylinder",
                 "args": {"height": round(p["rod_height"], 3),
                          "radius": round(p["rod_radius"], 3)}},
            ]
            ops.append(Op("union", {"ops": sub, "plane": "XY"}))
        elif kind == "sphere_cut":
            sub = [
                {"name": "transformed",
                 "args": {"offset": [round(r * 0.6, 2), 0, 0], "rotate": [0, 0, 0]}},
                {"name": "sphere", "args": {"radius": round(p["second_radius"], 3)}},
            ]
            ops.append(Op("cut", {"ops": sub, "plane": "XY"}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"sphere_kind": kind},
        )


# --- simple_shell -----------------------------------------------------------


class SimpleShellFamily(BaseFamily):
    """Base solid + shell (hollow) with one face removed (>Z or <Z)."""

    name = "simple_shell"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "base_kind": str(rng.choice(["cylinder", "box", "stepped"])),
            "scale": round(float(rng.uniform(22, 38)), 1),
            "thickness": round(float(rng.uniform(2.0, 4.5)), 1),
            "open_face": str(rng.choice([">Z", "<Z"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return 1.5 < p["thickness"] < p["scale"] * 0.18

    def make_program(self, p):
        s = p["scale"]
        ops = []
        if p["base_kind"] == "cylinder":
            ops.append(Op("cylinder", {"height": round(s, 2), "radius": round(s * 0.5, 2)}))
        elif p["base_kind"] == "box":
            ops.append(Op("box", {"length": round(s * 1.4, 2),
                                  "width": round(s, 2), "height": round(s * 0.9, 2)}))
        else:  # stepped
            ops.append(Op("box", {"length": round(s * 1.4, 2),
                                  "width": round(s, 2), "height": round(s * 0.5, 2)}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("rect", {"length": round(s * 0.9, 2), "width": round(s * 0.6, 2)}))
            ops.append(Op("extrude", {"distance": round(s * 0.5, 2)}))
        ops.append(Op("faces", {"selector": p["open_face"]}))
        ops.append(Op("shell", {"thickness": round(-p["thickness"], 2)}))  # inward
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thickness": p["thickness"], "open_face": p["open_face"]},
        )


# --- simple_hole ------------------------------------------------------------


class SimpleHoleFamily(BaseFamily):
    """Base solid + 1–N holes via pushPoints + hole on >Z face."""

    name = "simple_hole"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        layout = str(rng.choice(["center", "two_x", "four_corners", "row3"]))
        return {
            "base_kind": str(rng.choice(["box", "cylinder", "polygon_prism"])),
            "scale": round(float(rng.uniform(22, 38)), 1),
            "polygon_n": int(rng.choice([4, 6, 8])),
            "thickness": round(float(rng.uniform(8, 18)), 1),
            "hole_diameter": round(float(rng.uniform(3, 7)), 1),
            "layout": layout,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_diameter"] < p["scale"] * 0.2 and p["thickness"] > 4

    def make_program(self, p):
        s = p["scale"]
        ops = []
        if p["base_kind"] == "box":
            ops.append(Op("rect", {"length": round(s * 1.4, 2), "width": round(s, 2)}))
        elif p["base_kind"] == "cylinder":
            ops.append(Op("circle", {"radius": round(s * 0.55, 2)}))
        else:
            ops.append(Op("polygon", {"n": p["polygon_n"], "diameter": round(s, 2)}))
        ops.append(Op("extrude", {"distance": round(p["thickness"], 2)}))

        layout = p["layout"]
        d = p["hole_diameter"]
        ofs = s * 0.4
        if layout == "center":
            pts = [(0.0, 0.0)]
        elif layout == "two_x":
            pts = [(-ofs, 0.0), (ofs, 0.0)]
        elif layout == "four_corners":
            pts = [(-ofs, -ofs * 0.6), (ofs, -ofs * 0.6),
                   (-ofs, ofs * 0.6), (ofs, ofs * 0.6)]
        else:  # row3
            pts = [(-ofs, 0.0), (0.0, 0.0), (ofs, 0.0)]
        pts = [(round(x, 2), round(y, 2)) for x, y in pts]

        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(Op("hole", {"diameter": round(d, 2)}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"layout": layout, "n_holes": len(pts)},
        )


# === Explicit base × modifier combo families ================================
# Each pairs a specific base solid with one specific modifier op for cleaner
# per-combo training labels and Op programs.


def _hole_layout_pts(layout: str, ofs: float) -> list:
    if layout == "center":
        return [(0.0, 0.0)]
    if layout == "two_x":
        return [(-ofs, 0.0), (ofs, 0.0)]
    if layout == "four_corners":
        return [(-ofs, -ofs * 0.6), (ofs, -ofs * 0.6),
                (-ofs, ofs * 0.6), (ofs, ofs * 0.6)]
    if layout == "row3":
        return [(-ofs, 0.0), (0.0, 0.0), (ofs, 0.0)]
    return [(-ofs * 0.5, -ofs * 0.5), (ofs * 0.5, -ofs * 0.5),
            (-ofs * 0.5, ofs * 0.5), (ofs * 0.5, ofs * 0.5)]


# --- simple_box_hole --------------------------------------------------------


class SimpleBoxHoleFamily(BaseFamily):
    name = "simple_box_hole"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(28, 50)), 1),
            "width": round(float(rng.uniform(20, 38)), 1),
            "thickness": round(float(rng.uniform(8, 18)), 1),
            "hole_diameter": round(float(rng.uniform(3, 8)), 1),
            "layout": str(rng.choice(["center", "two_x", "four_corners", "row3", "grid2x2"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (p["hole_diameter"] < min(p["length"], p["width"]) * 0.2
                and p["thickness"] > 4)

    def make_program(self, p):
        ofs = min(p["length"], p["width"]) * 0.32
        pts = [(round(x, 2), round(y, 2)) for x, y in _hole_layout_pts(p["layout"], ofs)]
        ops = [
            Op("box", {"length": p["length"], "width": p["width"], "height": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": pts}),
            Op("hole", {"diameter": p["hole_diameter"]}),
        ]
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"layout": p["layout"]})


# --- simple_box_cut ---------------------------------------------------------


class SimpleBoxCutFamily(BaseFamily):
    """Box base − sub-primitive (sphere pocket / cylinder bore / box notch)."""

    name = "simple_box_cut"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(25, 40)), 1)
        return {
            "scale": s,
            "cut_kind": str(rng.choice(["sphere", "cylinder", "box"])),
            "cut_size": round(float(rng.uniform(0.25, 0.5)) * s, 1),
            "offset": [
                round(float(rng.uniform(-s * 0.3, s * 0.3)), 1),
                round(float(rng.uniform(-s * 0.2, s * 0.2)), 1),
                round(float(rng.uniform(-s * 0.2, s * 0.2)), 1),
            ],
            "polygon_n": 4,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["cut_size"] < p["scale"] * 0.6 and p["cut_size"] > 4

    def make_program(self, p):
        s = p["scale"]
        sub = _primitive_sub_ops(p["cut_kind"], p["cut_size"], 4, tuple(p["offset"]))
        last = sub[-1]
        if last["name"] in ("cylinder", "box"):
            last["args"]["height"] = round(s * 2.5, 2)
        ops = [
            Op("box", {"length": round(s * 1.4, 2), "width": round(s, 2), "height": round(s, 2)}),
            Op("cut", {"ops": sub, "plane": "XY"}),
        ]
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"cut_kind": p["cut_kind"]})


# --- simple_box_chamfer -----------------------------------------------------


class SimpleBoxChamferFamily(BaseFamily):
    name = "simple_box_chamfer"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(20, 35)), 1)
        return {
            "scale": s,
            "chamfer_length": round(float(rng.uniform(1.5, 5.0)), 1),
            "edge_selector": str(rng.choice([">Z", "<Z", "|Z", "all"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["chamfer_length"] < p["scale"] * 0.22

    def make_program(self, p):
        s = p["scale"]
        ops = [Op("box", {"length": round(s * 1.4, 2), "width": round(s, 2),
                          "height": round(s * 0.8, 2)})]
        if p["edge_selector"] != "all":
            ops.append(Op("edges", {"selector": p["edge_selector"]}))
        ops.append(Op("chamfer", {"length": p["chamfer_length"]}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"edge_selector": p["edge_selector"]})


# --- simple_cyl_hole --------------------------------------------------------


class SimpleCylHoleFamily(BaseFamily):
    name = "simple_cyl_hole"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 28)), 1),
            "thickness": round(float(rng.uniform(8, 18)), 1),
            "hole_diameter": round(float(rng.uniform(3, 8)), 1),
            "layout": str(rng.choice(["center", "two_x", "four_corners", "row3", "ring4"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_diameter"] < p["radius"] * 0.4

    def make_program(self, p):
        r = p["radius"]
        ofs = r * 0.55
        if p["layout"] == "ring4":
            pts = [(ofs, 0), (-ofs, 0), (0, ofs), (0, -ofs)]
        else:
            pts = _hole_layout_pts(p["layout"], ofs)
        pts = [(round(x, 2), round(y, 2)) for x, y in pts]
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": pts}),
            Op("hole", {"diameter": p["hole_diameter"]}),
        ]
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"layout": p["layout"]})


# --- simple_cyl_chamfer -----------------------------------------------------


class SimpleCylChamferFamily(BaseFamily):
    name = "simple_cyl_chamfer"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 28)), 1),
            "height": round(float(rng.uniform(15, 35)), 1),
            "chamfer_length": round(float(rng.uniform(1.5, 4.5)), 1),
            "edge_selector": str(rng.choice([">Z", "<Z", "all"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["chamfer_length"] < p["radius"] * 0.4

    def make_program(self, p):
        ops = [Op("cylinder", {"height": p["height"], "radius": p["radius"]})]
        if p["edge_selector"] != "all":
            ops.append(Op("edges", {"selector": p["edge_selector"]}))
        ops.append(Op("chamfer", {"length": p["chamfer_length"]}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"edge_selector": p["edge_selector"]})


# --- simple_extrude_cut -----------------------------------------------------


class SimpleExtrudeCutFamily(BaseFamily):
    """Extrude (rect/polygon profile) - sub-primitive cut."""

    name = "simple_extrude_cut"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(25, 40)), 1)
        return {
            "profile_kind": str(rng.choice(["rect", "polygon", "ellipse"])),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "scale": s,
            "height": round(float(rng.uniform(s * 0.5, s * 1.2)), 1),
            "cut_kind": str(rng.choice(["cylinder", "box", "sphere"])),
            "cut_size": round(float(rng.uniform(0.25, 0.5)) * s, 1),
            "offset": [
                round(float(rng.uniform(-s * 0.25, s * 0.25)), 1),
                round(float(rng.uniform(-s * 0.2, s * 0.2)), 1),
                round(float(rng.uniform(-s * 0.1, s * 0.1)), 1),
            ],
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["cut_size"] < p["scale"] * 0.6 and p["cut_size"] > 4

    def make_program(self, p):
        s = p["scale"]
        ops = list(_profile_ops(p["profile_kind"], s, p["polygon_n"]))
        ops.append(Op("extrude", {"distance": round(p["height"], 2)}))
        sub = _primitive_sub_ops(p["cut_kind"], p["cut_size"], p["polygon_n"], tuple(p["offset"]))
        last = sub[-1]
        if last["name"] in ("cylinder", "box"):
            last["args"]["height"] = round(p["height"] * 3, 2)
        ops.append(Op("cut", {"ops": sub, "plane": "XY"}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"profile": p["profile_kind"], "cut_kind": p["cut_kind"]})


# --- simple_extrude_hole ----------------------------------------------------


class SimpleExtrudeHoleFamily(BaseFamily):
    name = "simple_extrude_hole"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(28, 45)), 1)
        return {
            "profile_kind": str(rng.choice(["rect", "polygon", "ellipse", "slot"])),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "scale": s,
            "height": round(float(rng.uniform(8, 18)), 1),
            "hole_diameter": round(float(rng.uniform(3, 7)), 1),
            "layout": str(rng.choice(["center", "two_x", "row3", "grid2x2"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_diameter"] < p["scale"] * 0.18

    def make_program(self, p):
        s = p["scale"]
        ops = list(_profile_ops(p["profile_kind"], s, p["polygon_n"]))
        ops.append(Op("extrude", {"distance": round(p["height"], 2)}))
        ofs = s * 0.3
        pts = [(round(x, 2), round(y, 2)) for x, y in _hole_layout_pts(p["layout"], ofs)]
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(Op("hole", {"diameter": p["hole_diameter"]}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"profile": p["profile_kind"], "layout": p["layout"]})


# --- simple_extrude_chamfer -------------------------------------------------


class SimpleExtrudeChamferFamily(BaseFamily):
    name = "simple_extrude_chamfer"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "profile_kind": str(rng.choice(["rect", "polygon", "ellipse"])),
            "polygon_n": int(rng.choice([3, 4, 5, 6, 8])),
            "scale": round(float(rng.uniform(20, 35)), 1),
            "height": round(float(rng.uniform(15, 30)), 1),
            "chamfer_length": round(float(rng.uniform(1.5, 4.0)), 1),
            "edge_selector": str(rng.choice([">Z", "<Z", "all"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["chamfer_length"] < p["scale"] * 0.18

    def make_program(self, p):
        ops = list(_profile_ops(p["profile_kind"], p["scale"], p["polygon_n"]))
        ops.append(Op("extrude", {"distance": p["height"]}))
        if p["edge_selector"] != "all":
            ops.append(Op("edges", {"selector": p["edge_selector"]}))
        ops.append(Op("chamfer", {"length": p["chamfer_length"]}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"profile": p["profile_kind"]})


# --- simple_polygon_hole ----------------------------------------------------


class SimplePolygonHoleFamily(BaseFamily):
    name = "simple_polygon_hole"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        return {
            "n_sides": int(rng.choice([3, 4, 5, 6, 7, 8, 10, 12])),
            "diameter": round(float(rng.uniform(25, 45)), 1),
            "height": round(float(rng.uniform(8, 18)), 1),
            "hole_diameter": round(float(rng.uniform(3, 8)), 1),
            "layout": str(rng.choice(["center", "two_x", "row3"])),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_diameter"] < p["diameter"] * 0.2

    def make_program(self, p):
        d = p["diameter"]
        ofs = d * 0.28
        pts = [(round(x, 2), round(y, 2)) for x, y in _hole_layout_pts(p["layout"], ofs)]
        ops = [
            Op("polygon", {"n": p["n_sides"], "diameter": d}),
            Op("extrude", {"distance": p["height"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": pts}),
            Op("hole", {"diameter": p["hole_diameter"]}),
        ]
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"n_sides": p["n_sides"], "layout": p["layout"]})


# --- simple_revolve_cut -----------------------------------------------------


class SimpleRevolveCutFamily(BaseFamily):
    """Revolve solid - sub-primitive cut."""

    name = "simple_revolve_cut"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(15, 25)), 1)
        return {
            "scale": s,
            "cut_kind": str(rng.choice(["box", "cylinder", "sphere"])),
            "cut_size": round(float(rng.uniform(0.25, 0.5)) * s, 1),
            "offset": [
                round(float(rng.uniform(-s * 0.4, s * 0.4)), 1),
                0.0,
                round(float(rng.uniform(s * 0.1, s * 0.7)), 1),
            ],
            "polygon_n": 4,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["cut_size"] < p["scale"] * 0.7

    def make_program(self, p):
        s = p["scale"]
        ops = _rare_op_solid_ops("revolve", s, 4)
        sub = _primitive_sub_ops(p["cut_kind"], p["cut_size"], 4, tuple(p["offset"]))
        last = sub[-1]
        if last["name"] in ("cylinder", "box"):
            last["args"]["height"] = round(s * 3, 2)
        ops.append(Op("cut", {"ops": sub, "plane": "XY"}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"cut_kind": p["cut_kind"]})


# --- simple_loft_cut --------------------------------------------------------


class SimpleLoftCutFamily(BaseFamily):
    """Loft solid - sub-primitive cut."""

    name = "simple_loft_cut"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        s = round(float(rng.uniform(15, 25)), 1)
        return {
            "scale": s,
            "cut_kind": str(rng.choice(["cylinder", "sphere", "box"])),
            "cut_size": round(float(rng.uniform(0.25, 0.5)) * s, 1),
            "offset": [
                round(float(rng.uniform(-s * 0.3, s * 0.3)), 1),
                round(float(rng.uniform(-s * 0.2, s * 0.2)), 1),
                round(float(rng.uniform(s * 0.2, s * 1.0)), 1),
            ],
            "polygon_n": 4,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["cut_size"] < p["scale"] * 0.6

    def make_program(self, p):
        s = p["scale"]
        ops = _rare_op_solid_ops("loft", s, 4)
        sub = _primitive_sub_ops(p["cut_kind"], p["cut_size"], 4, tuple(p["offset"]))
        last = sub[-1]
        if last["name"] in ("cylinder", "box"):
            last["args"]["height"] = round(s * 3, 2)
        ops.append(Op("cut", {"ops": sub, "plane": "XY"}))
        return Program(family=self.name, difficulty=p["difficulty"], params=p, ops=ops,
                       feature_tags={"cut_kind": p["cut_kind"]})
