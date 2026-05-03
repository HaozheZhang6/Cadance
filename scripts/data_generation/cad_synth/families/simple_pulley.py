"""simple_pulley — stepped disc with optional V-groove rect cut.

Variants:
  flat_disc:        single disc + bore                                 (easy)
  stepped:          inner hub + outer flange (two cylinders union)     (med)
  rect_groove:      stepped + rectangular V-groove cut on rim          (hard)
  thin_plate_pull:  revolved sketch outline (single shot)              (hard, sketch-first)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("flat_disc", "stepped", "rect_groove", "thin_plate_pull")


class SimplePulleyFamily(BaseFamily):
    name = "simple_pulley"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "flat_disc"
        elif difficulty == "medium":
            v = str(rng.choice(["stepped", "stepped"]))
        else:
            v = str(rng.choice(["rect_groove", "thin_plate_pull", "stepped"]))

        r_out = round(float(rng.uniform(15, 40)), 1)
        r_hub = round(r_out * float(rng.uniform(0.3, 0.55)), 1)
        h_out = round(float(rng.uniform(5, 12)), 1)
        h_hub = round(h_out * float(rng.uniform(1.4, 2.4)), 1)
        bore = round(float(rng.uniform(4, max(5, r_hub * 0.55))), 1)
        groove_w = round(h_out * float(rng.uniform(0.4, 0.65)), 2)
        groove_d = round(r_out * float(rng.uniform(0.08, 0.18)), 2)
        return {
            "variant": v,
            "r_outer": r_out,
            "r_hub": r_hub,
            "h_outer": h_out,
            "h_hub": h_hub,
            "bore_d": bore,
            "groove_w": groove_w,
            "groove_d": groove_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_outer"] > p["r_hub"] + 2
            and p["bore_d"] < p["r_hub"] * 1.6
            and p["h_outer"] >= 3
            and p["bore_d"] >= 2
        )

    def make_program(self, p):
        v = p["variant"]
        ro, rh = p["r_outer"], p["r_hub"]
        ho, hh = p["h_outer"], p["h_hub"]
        bore = p["bore_d"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "flat_disc":
            ops += [
                Op("circle", {"radius": ro}),
                Op("extrude", {"distance": ho}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
        elif v == "thin_plate_pull":
            # Revolved sketch profile: rectangle (rim) + central hub bump.
            pts = [
                (bore / 2, 0.0),
                (rh, 0.0),
                (rh, hh),
                (ro, hh),
                (ro, hh - ho),
                (rh + 0.5, hh - ho),
                (rh + 0.5, 0.0 + 0.0),  # not great; use simpler shape
            ]
            # Simpler: rim trapezoid revolved
            pts = [
                (bore / 2, 0.0),
                (rh, 0.0),
                (rh, hh - ho),
                (ro, hh - ho),
                (ro, hh),
                (bore / 2, hh),
            ]
            ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
            for x, y in pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": y}))
            ops += [
                Op("close", {}),
                Op(
                    "revolve",
                    {"angleDeg": 360, "axisStart": (0, 0, 0), "axisEnd": (0, 1, 0)},
                ),
            ]
            tags["thin_plate"] = True
        else:
            # stepped: hub cylinder + outer flange disc
            ops += [
                Op("circle", {"radius": rh}),
                Op("extrude", {"distance": hh}),
                Op("workplane_offset", {"offset": round((hh - ho) / 2, 2)}),
                Op("circle", {"radius": ro}),
                Op("extrude", {"distance": ho}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["has_step"] = True
            if v == "rect_groove":
                # Cut rectangular V-groove around rim mid-plane
                gw = p["groove_w"]
                gd = p["groove_d"]
                # Approximate via revolve of cutter rect about Y axis (no — easier: cylinder cut)
                # Cut by ring: outer cylinder (ro) minus inner cylinder (ro-gd) of height gw
                # We'll use a "cut" sub-program: outer cylinder slice − inner cylinder.
                ops += [
                    Op("workplane_offset", {"offset": round((hh - gw) / 2 - hh, 2)}),
                    Op("circle", {"radius": ro + 0.5}),
                    Op("circle", {"radius": ro - gd}),
                    Op("cutBlind", {"depth": gw}),
                ]
                tags["has_groove"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
