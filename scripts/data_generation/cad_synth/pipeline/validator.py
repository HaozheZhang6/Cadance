"""Geometry + realism validation (Stages E & F)."""


def validate_roundtrip(program, wp) -> tuple[bool, str]:
    """Reject samples whose emitted gt_code doesn't re-exec to matching geometry.

    Catches families where _apply_op succeeded but the string-emitted code
    crashes on re-exec (e.g. chamfer on a selector that silently produced an
    empty edge list at build time but raises on re-exec), or where the two
    paths produce different face counts (divergence between wp and code).
    """
    try:
        from .builder import render_program_to_code

        code = render_program_to_code(program)
    except Exception as e:
        return False, f"emit_fail: {type(e).__name__}: {str(e)[:120]}"

    code_clean = "\n".join(
        l
        for l in code.splitlines()
        if l.strip() not in ("import cadquery as cq", "import cadquery")
    )

    import cadquery as cq

    globs = {
        "cq": cq,
        "show_object": lambda *a, **kw: None,
    }
    try:
        exec(compile(code_clean, "<roundtrip>", "exec"), globs)
    except Exception as e:
        return False, f"roundtrip_exec_fail: {type(e).__name__}: {str(e)[:120]}"

    r = globs.get("result") or globs.get("r")
    if r is None:
        return False, "roundtrip_no_result"

    try:
        wp_faces = len(wp.val().Faces())
        r_faces = len(r.val().Faces())
    except Exception as e:
        return False, f"roundtrip_face_count_fail: {e}"

    if abs(wp_faces - r_faces) > 2:
        return False, f"roundtrip_face_mismatch: wp={wp_faces} code={r_faces}"

    return True, ""


def validate_geometry(wp) -> tuple[bool, str]:
    """Check CadQuery result for degenerate geometry (Stage E).

    Returns (ok, reason).
    """
    try:
        solid = wp.val()
    except Exception as e:
        return False, f"no_solid: {e}"

    try:
        bb = solid.BoundingBox()
    except Exception as e:
        return False, f"no_bbox: {e}"

    xlen = bb.xmax - bb.xmin
    ylen = bb.ymax - bb.ymin
    zlen = bb.zmax - bb.zmin
    if xlen < 0.01 or ylen < 0.01 or zlen < 0.01:
        return False, f"degenerate_bbox: {xlen:.4f} x {ylen:.4f} x {zlen:.4f}"

    try:
        from OCP.GProp import GProp_GProps
        from OCP.BRepGProp import brepgprop

        props = GProp_GProps()
        brepgprop.VolumeProperties(solid.wrapped, props)
        vol = props.Mass()
        if vol < 1e-6:
            return False, f"zero_volume: {vol}"
    except Exception:
        pass  # volume check optional if OCP not fully available

    return True, ""


def validate_realism(program) -> tuple[bool, str]:
    """Family-specific realism filter (Stage F).

    Returns (ok, reason).
    """
    p = program.params
    family = program.family

    if family == "mounting_plate":
        t = p.get("thickness", 0)
        if t < 3:
            return False, f"thickness_too_thin: {t}"
        hd = p.get("hole_diameter")
        if hd is not None:
            if hd >= min(p["length"], p["width"]) / 3:
                return False, f"hole_too_large: {hd}"

    elif family == "round_flange":
        ir = p.get("inner_radius", 0)
        otr = p.get("outer_radius", 0)
        if ir >= otr:
            return False, f"inner_ge_outer: {ir} >= {otr}"
        bcr = p.get("bolt_circle_radius")
        if bcr is not None:
            if bcr <= ir + 3 or bcr >= otr - 3:
                return False, f"bolt_circle_out_of_range: {bcr}"

    return True, ""
