"""Geometry + realism validation (Stages E & F)."""


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
