"""Spur gear — involute tooth profile + 5 structural variants.

variant=solid_disc:   full disc + teeth + bore (default)
variant=spoked:       outer gear ring + N spokes + hub + bore
variant=rim_heavy:    thick outer rim + thin web + hub (stepped)
variant=internal_ring: smooth outer cylinder, gear teeth on inner surface
variant=multi_web:    hub → inner ring → outer gear ring (two concentric webs)

Gear geometry conventions (all dimensions in mm):
  m   = module [mm] — tooth size standard; pitch = π·m, tooth height ≈ 2.25·m
  z   = number of teeth
  r_p = pitch radius = m·z/2  (the "working" or reference radius)
  r_b = base circle radius = r_p·cos(α)  (involute unrolls from here)
  r_a = addendum circle (tip) = r_p + m  (outermost tooth radius)
  r_d = dedendum circle (root) = r_p − 1.25·m  (bottom of tooth valley)
  α   = pressure angle (standard = 20°)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ["solid_disc", "spoked", "rim_heavy", "internal_ring", "multi_web"]


def _gear_pts(m, z, pa_deg=20.0, n_inv=5):
    """Generate 2-D involute tooth profile polyline for one full gear circle.

    The profile consists of z teeth, each tooth built from:
      - root fillet point at r_d (bottom of tooth gap)
      - n_inv+1 sample points along the right involute flank
      - tip point at r_a
      - n_inv+1 sample points along the left involute flank (mirrored)

    Args:
        m:      gear module [mm]
        z:      number of teeth
        pa_deg: pressure angle [degrees], standard = 20°
        n_inv:  number of sample points per involute flank (higher = smoother)

    Returns:
        list of (x, y) tuples [mm] tracing the full tooth profile (closed by caller)
    """
    pa = math.radians(pa_deg)  # pressure angle in radians
    r_p = m * z / 2  # pitch radius [mm]
    r_b = r_p * math.cos(pa)  # base circle radius [mm] — involute origin
    r_a = r_p + m  # addendum (tip) radius [mm]
    # dedendum radius: at least 98% of base circle (prevents undercut for small z)
    r_d = max(r_b * 0.98, r_p - 1.25 * m)

    # involute of pressure angle — angular offset between pitch point and tooth centre
    inv_pa = math.tan(pa) - pa

    # involute parameter t at tip and root (t = tan(phi) where phi = pressure angle at r)
    t_tip = math.sqrt((r_a / r_b) ** 2 - 1)
    t_root = math.sqrt(max(0.0, (r_d / r_b) ** 2 - 1))

    def inv_xy(t, phi0, mirror=False):
        """Involute point at parameter t, rotated by phi0; mirror flips the flank."""
        # Standard involute parametric: x = r_b*(cos t + t*sin t), y = r_b*(sin t - t*cos t)
        x = r_b * (math.cos(t) + t * math.sin(t))
        y = r_b * (math.sin(t) - t * math.cos(t))
        if mirror:
            y = -y  # left flank is reflection of right flank
        c, s = math.cos(phi0), math.sin(phi0)
        return x * c - y * s, x * s + y * c

    pts = []
    for i in range(z):
        # Angular position of tooth centre on pitch circle
        tc = 2 * math.pi * i / z

        # Angular positions of right and left involute flanks (offset by half tooth)
        phi_r = tc - math.pi / (2 * z) - inv_pa  # right flank rotation
        phi_l = tc + math.pi / (2 * z) + inv_pa  # left flank rotation

        # Root point (centre of tooth gap, at dedendum radius)
        gap = tc - math.pi / z
        pts.append((round(r_d * math.cos(gap), 3), round(r_d * math.sin(gap), 3)))

        # Right involute flank: from root (t_root) to tip (t_tip)
        for j in range(n_inv + 1):
            t = t_root + (t_tip - t_root) * j / n_inv
            px, py = inv_xy(t, phi_r, mirror=False)
            pts.append((round(px, 3), round(py, 3)))

        # Tip point (tooth crown, at addendum radius)
        pts.append((round(r_a * math.cos(tc), 3), round(r_a * math.sin(tc), 3)))

        # Left involute flank: from tip back to root (mirrored)
        for j in range(n_inv + 1):
            t = t_tip - (t_tip - t_root) * j / n_inv
            px, py = inv_xy(t, phi_l, mirror=True)
            pts.append((round(px, 3), round(py, 3)))

    return pts


class SpurGearFamily(BaseFamily):
    name = "spur_gear"
    standard = "ISO 53"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Randomly sample parameters for one spur gear instance.

        Difficulty controls which features are present:
          easy:   bare gear (profile + bore)
          medium: + web recess or spoke/rim features + keyway
          hard:   + lightening holes + chamfer + rim boss (solid_disc only)
        """
        variant = rng.choice(VARIANTS)

        # --- Primary gear dimensions ---
        # Module m [mm]: ISO 54 preferred series (first + second choice, 0.8–4.0)
        _ISO54 = [
            0.8,
            1.0,
            1.25,
            1.5,
            2.0,
            2.5,
            3.0,
            4.0,
            0.9,
            1.125,
            1.375,
            1.75,
            2.25,
            2.75,
            3.5,
        ]
        m = float(rng.choice(_ISO54))

        # z: number of teeth. Fewer teeth → larger tooth fraction of disc; ≥12 avoids undercut
        z = int(rng.uniform(14, 36))

        # r_p = m·z/2 [mm]: pitch radius — the nominal "gear radius" used for all ratios
        r_p = m * z / 2

        # face_width [mm]: axial thickness of the gear body (along the shaft axis)
        # Typical spur gear: face_width ≈ 8–12× module
        face_w = round(rng.uniform(m * 6, m * 12), 1)

        # bore_diameter [mm]: centre shaft hole. Must be < r_p (no material left otherwise)
        # Range: 20%–50% of pitch radius
        bore_d = round(rng.uniform(r_p * 0.2, max(r_p * 0.21, r_p * 0.5)), 1)

        params = {
            "variant": variant,
            "module": m,  # tooth module [mm]
            "n_teeth": z,  # number of teeth
            "face_width": face_w,  # axial thickness [mm]
            "bore_diameter": bore_d,  # shaft bore diameter [mm]
            "pressure_angle": 20.0,  # involute pressure angle [degrees] — standard
            "difficulty": difficulty,
        }

        # Dedendum radius r_d [mm]: radius to root of tooth (bottom of tooth gap)
        # Used as clearance reference for spoke/multi_web inner features
        r_d = max(r_p * math.cos(math.radians(20)) * 0.98, r_p - 1.25 * m)

        # --- Variant-specific parameters ---

        if variant == "spoked":
            # Spoked gear: outer ring carries teeth; n_sp radial spokes connect to hub
            n_spokes = int(rng.choice([4, 5, 6]))  # typical: 4, 5, or 6 spokes

            # hub_radius [mm]: outer radius of central hub cylinder (surrounds bore)
            # Must be > bore_d/2 + 2 mm clearance
            hub_r = round(
                rng.uniform(bore_d / 2 + 2, max(bore_d / 2 + 3, r_p * 0.3)), 1
            )

            # inner_void_radius [mm]: inner edge of the tooth ring; defines spoke length
            # Spokes span from hub_r to inner_void_radius
            inner_r = round(rng.uniform(r_p * 0.56, max(r_p * 0.57, r_p * 0.72)), 1)

            # spoke_width [mm]: circumferential width of each spoke cross-section
            max_spoke_w = max(3.1, min(hub_r * 0.45, (inner_r - hub_r) * 0.55))
            spoke_w = round(rng.uniform(3, max_spoke_w), 1)

            params.update(
                n_spokes=n_spokes,
                hub_radius=hub_r,
                spoke_width=spoke_w,
                inner_void_radius=inner_r,
            )

        elif variant == "rim_heavy":
            # Rim-heavy gear: thick outer ring (carries teeth) + thin disc web + hub
            # The web recess cuts an annular pocket: circle(web_r) ∖ circle(hub_r)
            # Result: material only in 0..hub_r (hub) and web_r..r_a (outer rim)

            # web_radius [mm]: outer edge of the annular recess = inner edge of outer rim
            # Range 0.55–0.75×r_p keeps the outer rim (web_r..r_a) visibly thick
            web_r = round(rng.uniform(r_p * 0.55, max(r_p * 0.56, r_p * 0.75)), 1)

            # web_height [mm]: axial thickness of the thin web land left after recess
            # The recess depth = face_width − web_height (single) or (face_width − web_height)/2 (double)
            web_h = round(rng.uniform(face_w * 0.25, face_w * 0.50), 1)

            # hub_radius [mm]: outer radius of the hub column at centre
            # Constrained to ≤ web_r − 5mm so the annular recess band is wide enough to see
            hub_r_max = max(bore_d / 2 + 3, min(web_r - 5.0, web_r * 0.55))
            hub_r = round(
                rng.uniform(bore_d / 2 + 2, max(bore_d / 2 + 3, hub_r_max)), 1
            )

            # web_recess_sides: "single" (medium — one face) or "double" (hard — both faces)
            web_sides = "double" if difficulty == "hard" else "single"

            # web_recess_side: which face the single-sided recess opens toward
            # ">Z" = top face; "<Z" = bottom face (random for variety)
            web_side = rng.choice([">Z", "<Z"])

            params.update(
                web_radius=web_r,
                web_height=web_h,
                hub_radius=hub_r,
                web_recess_sides=web_sides,
                web_recess_side=str(web_side),
            )

        elif variant == "internal_ring":
            # Internal (ring) gear: outer smooth cylinder; teeth cut on inner bore surface
            # outer_smooth_radius [mm]: outer envelope of the ring gear body
            outer_r = round(r_p + m + rng.uniform(3, 8), 1)
            params["outer_smooth_radius"] = outer_r

        elif variant == "multi_web":
            # Multi-web gear: concentric rings connected by two stepped webs
            # Structure (radially outward): bore → hub → inner web → mid_ring → outer web → gear rim

            # mid_ring_radius [mm]: radius of the intermediate concentric ring
            mid_r = round(rng.uniform(r_p * 0.45, max(r_p * 0.46, r_p * 0.65)), 1)

            # hub_radius [mm]: outer radius of central hub (between bore and inner web)
            hub_r = round(
                rng.uniform(bore_d / 2 + 2, max(bore_d / 2 + 3, mid_r * 0.55)), 1
            )

            # web1_height [mm]: axial thickness of the outer web land (gear rim → mid_ring)
            web1_h = round(rng.uniform(face_w * 0.2, face_w * 0.45), 1)

            # web2_height [mm]: axial thickness of the inner web land (mid_ring → hub)
            web2_h = round(rng.uniform(face_w * 0.2, face_w * 0.45), 1)

            params.update(
                mid_ring_radius=mid_r,
                hub_radius=hub_r,
                web1_height=web1_h,
                web2_height=web2_h,
            )

        # --- Shared feature: web recess on solid_disc (medium/hard only) ---
        # Annular pocket cut from one or both flat faces → I-section cross-section.
        # On hard: rim_boss and web_recess are MUTUALLY EXCLUSIVE — having both makes the
        # outer rim protrude far above the thinned web, which looks physically wrong.
        _add_web_recess = False
        if difficulty == "medium" and variant == "solid_disc":
            _add_web_recess = True
        elif difficulty == "hard" and variant == "solid_disc":
            _add_web_recess = bool(rng.integers(0, 2))  # 50/50 choice

        if _add_web_recess:
            # web_recess_radius [mm]: outer radius of the recess pocket
            wcr = round(rng.uniform(r_p * 0.5, max(r_p * 0.51, r_p * 0.78)), 1)

            if difficulty == "hard":
                # double-sided: ≤25% fw per side → web land ≥ 50% fw, keeps proportions sane
                wrd = round(rng.uniform(face_w * 0.12, face_w * 0.25), 1)
            else:
                wrd = round(rng.uniform(face_w * 0.15, face_w * 0.35), 1)

            side = rng.choice(["<Z", ">Z"])
            params.update(
                web_recess_radius=wcr,
                web_recess_depth=wrd,
                web_recess_sides="double" if difficulty == "hard" else "single",
                web_recess_side=side,
            )

        # --- Keyway: medium+ all variants ---
        # Sample keyway BEFORE lightening holes so PCD min can account for keyway depth.
        if difficulty in ("medium", "hard"):
            key_w = round(
                rng.uniform(bore_d * 0.2, max(bore_d * 0.21, bore_d * 0.3)), 1
            )
            key_h = round(rng.uniform(key_w * 0.5, max(key_w * 0.51, key_w)), 1)
            params.update(keyway_width=key_w, keyway_height=key_h)

        # --- Hard solid_disc features ---
        if difficulty == "hard" and variant == "solid_disc":
            if _add_web_recess:
                # web_recess path: lightening holes in the web zone + chamfer
                n_light = int(rng.choice([4, 6]))
                light_r = round(rng.uniform(r_p * 0.1, max(r_p * 0.11, r_p * 0.18)), 1)
                kh_val = params.get("keyway_height", 0)
                l_pcd_min = max(r_p * 0.55, bore_d / 2 + kh_val + light_r + 3.0)
                light_pcd = round(
                    rng.uniform(l_pcd_min, max(l_pcd_min + 0.1, r_p * 0.75)), 1
                )
                params.update(
                    n_lightening=n_light,
                    lightening_radius=light_r,
                    lightening_pcd=light_pcd,
                )
            else:
                # rim_boss path: rim collar + matching hub boss, NO lightening holes.
                # Rule: if outer rim is enhanced, center hub must also be enhanced.
                rb_h = round(rng.uniform(face_w * 0.05, face_w * 0.12), 1)
                # hub_boss_radius: 1.8–2.5× bore_r so it reads as a visible hub shoulder
                hb_r = round(bore_d / 2 * rng.uniform(1.8, 2.5), 1)
                params["rim_boss_h"] = rb_h
                params["hub_boss_radius"] = hb_r

            params["chamfer_length"] = round(
                rng.uniform(0.3, max(0.31, min(1.0, m * 0.3))), 1
            )

        return params

    def validate_params(self, params: dict) -> bool:
        """Reject geometrically degenerate or physically implausible parameter sets."""
        m = params["module"]
        z = params["n_teeth"]
        r_p = m * z / 2  # pitch radius [mm]
        bd = params["bore_diameter"]
        variant = params.get("variant", "solid_disc")

        # Bore must not swallow most of the disc; teeth must be plentiful enough to avoid
        # severe undercut; module must be a real positive size
        if bd >= r_p * 0.6 or z < 12 or m < 0.5:
            return False

        if variant == "spoked":
            hr = params.get("hub_radius", 0)  # hub outer radius
            ir = params.get("inner_void_radius", 0)  # inner edge of tooth ring
            sw = params.get("spoke_width", 0)  # spoke cross-section width
            # hub must fit inside inner ring; inner ring must not eat into teeth;
            # spokes must not fill the full radial gap (leave airspace between them)
            if hr >= ir or ir >= r_p * 0.9 or sw >= (ir - hr) * 0.7:
                return False

        elif variant == "rim_heavy":
            wr = params.get("web_radius", 0)  # outer radius of annular recess
            wh = params.get("web_height", 0)  # remaining axial web thickness
            fw = params["face_width"]
            # web_radius must leave a real outer rim and must clear the bore
            if wr >= r_p * 0.8 or wr <= bd:
                return False
            # web land must be thin enough to show stepped shape, but not vanishingly thin
            if wh >= fw * 0.85 or wh < 1.0:
                return False
            # annular band must be at least 3mm wide to be visible
            hr = params.get("hub_radius", 0)
            if wr - hr < 3.0:
                return False
            # hub must clear keyway tip so recess doesn't clip keyway
            kh_v = params.get("keyway_height", 0)
            if kh_v and hr < bd / 2 + kh_v + 1.5:
                return False

        elif variant == "internal_ring":
            outr = params.get("outer_smooth_radius", 0)
            # Outer envelope must extend beyond the gear tip radius + clearance
            if outr <= r_p + m + 1:
                return False

        elif variant == "multi_web":
            mr = params.get("mid_ring_radius", 0)  # mid ring radius
            hr = params.get("hub_radius", 0)  # hub radius
            # Mid ring must be well inside teeth; hub must be well inside mid ring
            if mr >= r_p * 0.8 or hr >= mr * 0.9:
                return False

        if variant == "solid_disc":
            lr = params.get("lightening_radius")  # lightening hole radius
            lp = params.get("lightening_pcd")  # lightening hole pitch circle
            if lr and lp:
                kh = params.get("keyway_height", 0)
                # Holes must clear bore wall + keyway depth and not reach into tooth root
                if lp - lr <= bd / 2 + kh + 2.0 or lp + lr >= r_p * 0.85:
                    return False
            wcr = params.get("web_recess_radius")  # web recess outer radius
            wrd = params.get("web_recess_depth")  # web recess depth
            wcs = params.get("web_recess_sides", "single")
            fw = params["face_width"]
            if wcr and wcr >= r_p * 0.9:
                return False
            if wrd:
                # For double-sided: each pocket is wrd deep; web land = fw - 2*wrd ≥ 0.5*fw
                if wcs == "double" and wrd >= fw * 0.28:
                    return False
                # For single-sided: web land = fw - wrd ≥ 0.5*fw
                if wcs == "single" and wrd >= fw * 0.45:
                    return False

        return True

    def make_program(self, params: dict) -> Program:
        """Convert sampled parameters into an ordered Op sequence for CadQuery.

        Build order:
          1. Base solid (gear profile extrude or cylinder)
          2. Variant-specific subtractive / additive features
          3. Shared features: web recess, keyway, lightening holes, chamfer, rim boss
        """
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "solid_disc")
        m = params["module"]  # gear module [mm]
        z = params["n_teeth"]  # number of teeth
        fw = params["face_width"]  # axial face width [mm]
        bd = params["bore_diameter"]  # bore diameter [mm]
        pa = params["pressure_angle"]  # pressure angle [degrees]
        r_p = m * z / 2  # pitch radius [mm]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
            "pattern_like": True,
            "variant": variant,
        }

        # Pre-compute involute tooth profile points (shared by all variants)
        pts = _gear_pts(m, z, pa_deg=pa, n_inv=5)

        # ---------------------------------------------------------------
        # 1. Build base solid
        # ---------------------------------------------------------------

        if variant == "solid_disc":
            # Extrude tooth profile to full face_width → solid disc with gear teeth
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": fw}))
            # Central bore: through-hole of diameter bore_d
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

            # Lightening holes (hard only): through-holes on pitch circle
            # Use explicit per-hole cuts at world coords — polarArray origin drifts after
            # keyway cutThruAll shifts the >Z face centroid away from the gear axis.
            n_l = params.get("n_lightening")  # number of holes
            l_r = params.get("lightening_radius")  # hole radius [mm]
            l_pcd = params.get("lightening_pcd")  # pitch circle of hole centres [mm]
            if n_l and l_r and l_pcd:
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

            # Chamfer on top outer edge (hard only): small bevel for assembly clearance
            cl = params.get("chamfer_length")  # chamfer leg length [mm]
            if cl:
                tags["has_chamfer"] = True
                ops.append(Op("edges", {"selector": ">Z"}))
                ops.append(Op("chamfer", {"length": cl}))

        elif variant == "spoked":
            n_sp = params["n_spokes"]  # number of spokes
            hub_r = params["hub_radius"]  # hub outer radius [mm]
            inner_r = params["inner_void_radius"]  # inner edge of tooth ring [mm]
            spoke_w = params["spoke_width"]  # spoke cross-section width [mm]

            # Step 1: extrude gear profile to get full solid tooth ring
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": fw}))

            # Step 2: cut inner void — removes disc leaving only the outer tooth ring
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": inner_r}))
            ops.append(Op("cutThruAll", {}))

            # Step 3: add hub cylinder at centre shifted to z=[0,fw] to match gear ring
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(fw / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": fw, "radius": hub_r},
                            },
                        ]
                    },
                )
            )

            # Step 4: add spokes — evenly spaced radial box beams connecting hub to ring
            spoke_len = round(inner_r - hub_r + 1.0, 3)  # +1mm overlap on each side
            spoke_cx = round(
                (hub_r + inner_r) / 2, 3
            )  # radial midpoint for box centre [mm]
            for i in range(n_sp):
                angle = round(
                    360.0 * i / n_sp, 3
                )  # rotation angle for this spoke [degrees]
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                # First rotate to spoke angle, then translate to midpoint at correct z
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, 0, 0],
                                        "rotate": [0, 0, angle],  # rotate around Z axis
                                    },
                                },
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [
                                            spoke_cx,
                                            0,
                                            round(fw / 2, 3),
                                        ],  # shift radially + to mid-height
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": spoke_len,  # radial extent [mm]
                                        "width": spoke_w,  # circumferential width [mm]
                                        "height": fw,  # axial thickness = full face_width [mm]
                                        "centered": True,
                                    },
                                },
                            ]
                        },
                    )
                )

            # Step 5: central bore
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

            sf = params.get("spoke_fillet")  # optional fillet on spoke edges [mm]
            if sf:
                tags["has_fillet"] = True
                ops.append(Op("edges", {"selector": "|Z"}))
                ops.append(Op("fillet", {"radius": sf}))

        elif variant == "rim_heavy":
            web_r = params["web_radius"]  # outer radius of annular recess [mm]
            web_h = params["web_height"]  # axial thickness of web land [mm]
            hub_r = params["hub_radius"]  # hub outer radius (inner edge of recess) [mm]

            # Step 1: extrude full gear profile → solid
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": fw}))

            # Step 2: web recess — annular pocket from one or both faces
            # Annular profile: circle(web_r) with inner hole circle(hub_r)
            #   → cuts only the band hub_r..web_r, preserving 0..hub_r (hub) and web_r..r_a (rim)
            web_sides = params.get("web_recess_sides", "single")
            web_side = params.get("web_recess_side", "<Z")

            if web_sides == "double":
                # Hard: symmetric double-sided recess; each side removes (fw − web_h)/2
                recess = round((fw - web_h) / 2, 3)  # depth per side [mm]
                faces = [">Z", "<Z"]  # cut from both faces
            else:
                # Medium/easy: single-sided recess; removes fw − web_h from one face
                recess = round(fw - web_h, 3)  # full recess depth [mm]
                faces = [web_side]  # cut from selected face only

            # Inner boundary must clear keyway tip so recess doesn't eat keyway zone
            kh_val = params.get("keyway_height", 0)
            inner_r_cut = round(max(hub_r, bd / 2 + kh_val + 2.0), 3)

            if recess > 0.5:  # skip trivially shallow recesses
                for face in faces:
                    ops.append(Op("workplane", {"selector": face}))
                    ops.append(
                        Op("circle", {"radius": web_r})
                    )  # outer boundary of annulus
                    ops.append(
                        Op("circle", {"radius": inner_r_cut})
                    )  # inner boundary (clears keyway)
                    ops.append(
                        Op("cutBlind", {"depth": recess})
                    )  # builder auto-negates

            # No hub union needed — the region 0..inner_r_cut was never cut; it IS the hub.

            # Step 3: central bore through the hub
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        elif variant == "internal_ring":
            outer_r = params["outer_smooth_radius"]  # outer envelope radius [mm]

            # Step 1: solid outer cylinder (smooth exterior)
            ops.append(Op("cylinder", {"height": fw, "radius": outer_r}))

            # Step 2: cut gear-shaped void — subtracts external tooth profile from disc.
            # The gear profile extends to r_a = r_p+m < outer_r, so the outer shell
            # (r_a..outer_r) survives as one connected ring; the tooth-gap material
            # (r_d..r_a at gap angles) forms the internal teeth, all connected through
            # the outer ring → guaranteed single solid.
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("cutThruAll", {}))

            # Step 3: central bore
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        elif variant == "multi_web":
            mid_r = params[
                "mid_ring_radius"
            ]  # intermediate concentric ring radius [mm]
            hub_r = params["hub_radius"]  # hub outer radius [mm]
            w1h = params["web1_height"]  # outer web axial thickness [mm]
            w2h = params["web2_height"]  # inner web axial thickness [mm]

            # Step 1: extrude full gear profile → solid
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": fw}))

            # Step 2: outer web recess — pocket between mid ring and gear rim from top face
            # Uses full-disc cutBlind (no inner circle) so mid_ring union fills it back
            inner_void_r = round(mid_r - 2, 3)  # cut up to 2 mm inside mid ring edge
            recess1 = round(fw - w1h, 3)  # outer web pocket depth [mm]
            if recess1 > 0.5:
                ops.append(Op("workplane", {"selector": ">Z"}))
                ops.append(Op("circle", {"radius": inner_void_r}))
                ops.append(Op("cutBlind", {"depth": recess1}))

            # Step 3: union mid ring at z=[0,fw] to match gear ring
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(fw / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": fw, "radius": mid_r},
                            },
                        ]
                    },
                )
            )

            # Step 4: inner web recess — pocket between hub and mid ring from top face
            inner_void2_r = round(hub_r + 1, 3)  # cut up to 1 mm inside hub edge
            recess2 = round(fw - w2h, 3)  # inner web pocket depth [mm]
            if recess2 > 0.5:
                ops.append(Op("workplane", {"selector": ">Z"}))
                ops.append(Op("circle", {"radius": inner_void2_r}))
                ops.append(Op("cutBlind", {"depth": recess2}))

            # Step 5: union hub cylinder at z=[0,fw] to match gear ring
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(fw / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": fw, "radius": hub_r},
                            },
                        ]
                    },
                )
            )

            # Step 6: central bore
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": params["bore_diameter"]}))

        # ---------------------------------------------------------------
        # 2. Shared subtractive features (applied after base solid)
        # ---------------------------------------------------------------

        # Web recess (solid_disc medium/hard): annular pocket on face
        # Uses inner circle at bore_r so bore wall is preserved
        wcr = params.get("web_recess_radius")  # outer radius of recess annulus [mm]
        wrd = params.get("web_recess_depth")  # recess depth [mm]
        wcs = params.get("web_recess_sides", "single")  # "single" or "double"
        wc_side = params.get("web_recess_side", "<Z")  # face selector for single side
        if wcr and wrd:
            bore_r = round(bd / 2, 3)  # inner boundary = bore wall radius [mm]
            sides = ["<Z", ">Z"] if wcs == "double" else [wc_side]
            for side in sides:
                ops.append(Op("workplane", {"selector": side}))
                ops.append(Op("circle", {"radius": wcr}))  # outer annulus boundary
                ops.append(
                    Op("circle", {"radius": bore_r})
                )  # inner annulus boundary (preserved)
                ops.append(
                    Op("cutBlind", {"depth": round(wrd, 3)})
                )  # builder auto-negates

        # Keyway: rectangular slot through bore from top face
        # Allows a matching key to transmit torque between shaft and gear
        kw = params.get("keyway_width")  # slot width [mm]
        kh = params.get("keyway_height")  # slot depth measured from bore surface [mm]
        if kw and kh:
            tags["has_slot"] = True
            bore_r = bd / 2
            rect_width = round(kw, 3)
            # rect_height: extends from gear axis outward by bore_r + kh
            # centred at (bore_r + kh) / 2 from axis so it overlaps the bore hole
            rect_height = round(kh + bore_r, 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": 0.0, "y": round(rect_height / 2, 3)}))
            ops.append(Op("rect", {"length": rect_width, "width": rect_height}))
            ops.append(Op("cutThruAll", {}))

        # ---------------------------------------------------------------
        # 3. Additive features (applied last; always on top of final solid)
        # ---------------------------------------------------------------

        # Rim boss + hub boss: matching annular collars on outer rim AND center hub.
        # Rule: if outer rim is enhanced, center hub must also be enhanced (same height).
        rb_h = params.get("rim_boss_h")  # boss axial height [mm]
        hb_r = params.get("hub_boss_radius")  # hub boss outer radius [mm]
        if rb_h and variant == "solid_disc":
            rim_r = round(r_p + m + 0.3, 3)  # outer edge just beyond tooth tips
            # Rim boss inner radius: sits at dedendum circle so boss = just the tooth zone rim
            rim_inner_r = round(r_p - m * 0.8, 3)

            # --- Rim boss (outer annular collar) ---
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(fw + rb_h / 2 - 0.5, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": round(rb_h, 3), "radius": rim_r},
                            },
                        ]
                    },
                )
            )
            # Hollow out rim boss inner disc
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(fw + rb_h / 2 - 0.5, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(rb_h * 2, 3),
                                    "radius": rim_inner_r,
                                },
                            },
                        ]
                    },
                )
            )

            if hb_r:
                # --- Hub boss (center cylinder collar, same height as rim boss) ---
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, 0, round(fw + rb_h / 2 - 0.5, 3)],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(rb_h, 3),
                                        "radius": round(hb_r, 3),
                                    },
                                },
                            ]
                        },
                    )
                )
                # Extend bore through hub boss
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, 0, round(fw + rb_h / 2 - 0.5, 3)],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(rb_h * 2, 3),
                                        "radius": round(bd / 2, 3),
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
