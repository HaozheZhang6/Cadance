"""Op/Program dataclasses and execution/rendering engine.

`build_from_program` executes Ops on a CadQuery Workplane.
`render_program_to_code` serialises Ops to executable Python source.
Both derive from the same Program — geometry cannot diverge.
"""

from dataclasses import dataclass, field


@dataclass
class Op:
    """One build step in a structured program."""

    name: str
    args: dict = field(default_factory=dict)


@dataclass
class Program:
    """Structured, ordered build plan for a part."""

    family: str
    difficulty: str
    params: dict
    ops: list
    feature_tags: dict = field(default_factory=dict)
    base_plane: str = "XY"  # starting workplane: "XY", "YZ", or "XZ"


# ---------------------------------------------------------------------------
# Op → CadQuery execution
# ---------------------------------------------------------------------------


def _apply_op(wp, op: Op):
    """Apply a single Op to a CadQuery Workplane, return updated wp."""
    global _pending_sketch
    name = op.name
    a = op.args

    if name == "box":
        wp = wp.box(
            a["length"], a["width"], a["height"], centered=a.get("centered", True)
        )
    elif name == "cylinder":
        wp = wp.cylinder(a["height"], a["radius"])
    elif name == "circle":
        wp = wp.circle(a["radius"])
    elif name == "rect":
        wp = wp.rect(a["length"], a["width"])
    elif name == "extrude":
        taper = a.get("taper", 0)
        both = a.get("both", False)
        if taper:
            wp = wp.extrude(a["distance"], taper=taper, both=both)
        else:
            wp = wp.extrude(a["distance"], both=both)
    elif name == "cutThruAll":
        wp = wp.cutThruAll()
    elif name == "cutBlind":
        # CadQuery cutBlind requires negative depth to cut INTO the solid from the selected face.
        # Family code passes positive "depth" values (intuitive), so negate here.
        try:
            wp = wp.cutBlind(-abs(a["depth"]))
        except Exception:
            wp = wp.newObject(wp.objects)  # skip if face selection invalid
    elif name == "lineTo":
        wp = wp.lineTo(a["x"], a["y"])
    elif name == "close":
        wp = wp.close()
    elif name == "tag":
        wp = wp.tag(a["name"])
    elif name == "hole":
        try:
            wp = wp.hole(a["diameter"], depth=a.get("depth"))
        except Exception:
            wp = wp.newObject(wp.objects)  # skip hole if face selection invalid
    elif name == "cboreHole":
        wp = wp.cboreHole(
            a["diameter"], a["cboreDiameter"], a["cboreDepth"], depth=a.get("depth")
        )
    elif name == "fillet":
        wp = wp.fillet(a["radius"])
    elif name == "chamfer":
        wp = wp.chamfer(a["length"])
    elif name == "shell":
        wp = wp.shell(a["thickness"])
    elif name == "workplane":
        try:
            wp = wp.faces(_remap_sel(a["selector"])).workplane()
        except Exception:
            try:
                wp = wp.newObject([wp.findSolid()])
            except Exception:
                pass
    elif name == "pushPoints":
        wp = wp.pushPoints(a["points"])
    elif name == "polarArray":
        wp = wp.polarArray(
            a["radius"], a.get("startAngle", 0), a.get("angle", 360), a["count"]
        )
    elif name == "rarray":
        wp = wp.rarray(a["xSpacing"], a["ySpacing"], a["xCount"], a["yCount"])
    elif name == "center":
        wp = wp.center(a["x"], a["y"])
    elif name == "moveTo":
        wp = wp.moveTo(a["x"], a["y"])
    elif name == "faces":
        wp = wp.faces(_remap_sel(a["selector"]))
    elif name == "edges":
        sel = a.get("selector")
        wp = wp.edges(_remap_sel(sel)) if sel else wp.edges()
    elif name == "revolve":
        axis_start = tuple(a.get("axisStart", (0, 0, 0)))
        axis_end = tuple(a.get("axisEnd", (0, 1, 0)))
        wp = wp.revolve(a["angleDeg"], axis_start, axis_end)
    elif name == "loft":
        wp = wp.loft(combine=a.get("combine", True))
    elif name == "polyline":
        wp = wp.polyline(a["points"])
    elif name == "mirrorY":
        wp = wp.mirrorY()
    elif name == "mirrorX":
        wp = wp.mirrorX()
    elif name == "polygon":
        wp = wp.polygon(a["n"], a["diameter"])
    elif name == "slot2D":
        wp = wp.slot2D(a["length"], a["width"], a.get("angle", 0))
    elif name == "ellipse":
        wp = wp.ellipse(a["xRadius"], a["yRadius"])
    elif name == "threePointArc":
        wp = wp.threePointArc(tuple(a["point1"]), tuple(a["point2"]))
    elif name == "sphere":
        wp = wp.sphere(a["radius"])
    elif name == "torus":
        import cadquery as cq

        pnt = cq.Vector(*a.get("pnt", (0, 0, 0)))
        dir_ = cq.Vector(*a.get("dir", (0, 0, 1)))
        torus = cq.Solid.makeTorus(a["majorRadius"], a["minorRadius"], pnt, dir_)
        wp = wp.union(cq.Workplane("XY").newObject([torus]))
    elif name == "transformed":
        import cadquery as cq

        off = a.get("offset", [0, 0, 0])
        rot = a.get("rotate", [0, 0, 0])
        wp = wp.transformed(offset=cq.Vector(*off), rotate=cq.Vector(*rot))
    elif name == "cskHole":
        wp = wp.cskHole(
            a["diameter"], a["cskDiameter"], a["cskAngle"], depth=a.get("depth")
        )
    elif name == "hLine":
        wp = wp.hLine(a["distance"])
    elif name == "vLine":
        wp = wp.vLine(a["distance"])
    elif name == "workplane_offset":
        wp = wp.workplane(offset=a["offset"])
    elif name == "union":
        import cadquery as cq

        sub_plane = a.get("plane", _current_base_plane)
        sub = cq.Workplane(sub_plane)
        for o in a["ops"]:
            sub = _apply_op(sub, Op(o["name"], o.get("args", {})))
        wp = wp.union(sub)
    elif name == "cut":
        import cadquery as cq

        sub_plane = a.get("plane", _current_base_plane)
        sub = cq.Workplane(sub_plane)
        for o in a["ops"]:
            sub = _apply_op(sub, Op(o["name"], o.get("args", {})))
        wp = wp.cut(sub)
    elif name == "sweep":
        import cadquery as cq

        path_type = a["path_type"]
        is_frenet = a.get("isFrenet", path_type == "helix")
        if path_type == "helix":
            pa = a["path_args"]
            path = cq.Wire.makeHelix(pa["pitch"], pa["height"], pa["radius"])
        elif path_type == "helix_with_legs":
            # Continuous wire: straight leg1 → helix → straight leg2.
            # Legs tangent to helix at its actual endpoints — uses helix vertices
            # and the helix parametric tangent at t_start=0 and t_end=2π·H/p.
            import math as _m

            pa = a["path_args"]
            _p, _H, _R, _ll = pa["pitch"], pa["height"], pa["radius"], pa["leg_length"]
            _helix = cq.Wire.makeHelix(_p, _H, _R)
            _verts = _helix.Vertices()
            _p_start = cq.Vector(_verts[0].X, _verts[0].Y, _verts[0].Z)
            _p_end = cq.Vector(_verts[1].X, _verts[1].Y, _verts[1].Z)
            _dz = _p / (2 * _m.pi)
            _t0 = 0.0
            _t1 = 2 * _m.pi * _H / _p
            _tan0 = cq.Vector(-_R * _m.sin(_t0), _R * _m.cos(_t0), _dz)
            _tan1 = cq.Vector(-_R * _m.sin(_t1), _R * _m.cos(_t1), _dz)
            _m0 = _m.sqrt(_tan0.x**2 + _tan0.y**2 + _tan0.z**2)
            _m1 = _m.sqrt(_tan1.x**2 + _tan1.y**2 + _tan1.z**2)
            _tan0n = cq.Vector(_tan0.x / _m0, _tan0.y / _m0, _tan0.z / _m0)
            _tan1n = cq.Vector(_tan1.x / _m1, _tan1.y / _m1, _tan1.z / _m1)
            _leg1_start = _p_start - _tan0n.multiply(_ll)
            _leg2_end = _p_end + _tan1n.multiply(_ll)
            _leg1 = cq.Edge.makeLine(_leg1_start, _p_start)
            _leg2 = cq.Edge.makeLine(_p_end, _leg2_end)
            path = cq.Wire.assembleEdges([_leg1] + list(_helix.Edges()) + [_leg2])
        elif path_type == "spline":
            pts = [tuple(p) for p in a["path_points"]]
            path = cq.Workplane(a.get("path_plane", "XZ")).spline(pts)
        elif path_type == "line_pts":
            pts = [tuple(p) for p in a["path_points"]]
            path = cq.Workplane(a.get("path_plane", "XZ")).polyline(pts)
        elif path_type == "elbow_arc":
            # 90° pipe elbow: straight lead → radiusArc → straight trail (XZ plane)
            ll = a["lead_length"]
            br = a["bend_radius"]
            tl = a["trail_length"]
            path = (
                cq.Workplane("XZ")
                .moveTo(0.0, 0.0)
                .lineTo(0.0, ll)
                .radiusArc((br, ll + br), br)
                .lineTo(br + tl, ll + br)
            )
        else:
            raise ValueError(f"Unknown sweep path_type: {path_type}")
        wp = wp.sweep(path, isFrenet=is_frenet)
    elif name == "sketch_subtract":
        import cadquery as cq

        sk = cq.Sketch().circle(a["outer_radius"])
        for prof in a["profiles"]:
            sub = cq.Workplane(_current_base_plane)
            for o in prof["wire_ops"]:
                sub = _apply_op(sub, Op(o["name"], o.get("args", {})))
            rot = prof.get("rotate_deg", 0.0)
            if rot:
                sub = sub.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), rot)
            sk = sk.face(sub.val(), mode="s")
        _pending_sketch = sk.clean()
    elif name == "placeSketch":
        wp = wp.placeSketch(_pending_sketch)
        _pending_sketch = None
    elif name == "twistExtrude":
        wp = wp.twistExtrude(a["distance"], a["angle"])
    elif name == "intersect":
        import cadquery as cq

        sub = cq.Workplane(_current_base_plane)
        for o in a["ops"]:
            sub = _apply_op(sub, Op(o["name"], o.get("args", {})))
        wp = wp.intersect(sub)
    else:
        raise ValueError(f"Unknown op: {name}")
    return wp


def _patch_ocp_hashcode():
    """Monkey-patch HashCode on OCP TopoDS types (needed in this env)."""
    from OCP.TopoDS import (
        TopoDS_Compound,
        TopoDS_CompSolid,
        TopoDS_Edge,
        TopoDS_Face,
        TopoDS_Shape,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Vertex,
        TopoDS_Wire,
    )

    for _cls in [
        TopoDS_Shape,
        TopoDS_Face,
        TopoDS_Edge,
        TopoDS_Vertex,
        TopoDS_Wire,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Compound,
        TopoDS_CompSolid,
    ]:
        if not hasattr(_cls, "HashCode"):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub


_current_base_plane = "XY"  # module-level so union/cut subs can inherit

# Module-level sketch handoff between sketch_subtract → placeSketch Ops.
# cq.Sketch is a non-Workplane object, so we can't thread it via wp alone.
_pending_sketch = None
_pending_sketch_code = None

# Map selectors that reference the build axis (Z in XY) to the correct axis
# for each standard workplane.  Only the axial/normal-direction selectors
# are remapped; radial selectors (>X, <X when plane=XY, etc.) are left alone.
_AXIAL_REMAP = {
    # Axial selectors (normal direction of the base plane)
    ">Z": {"XY": ">Z", "YZ": ">X", "XZ": ">Y"},
    "<Z": {"XY": "<Z", "YZ": "<X", "XZ": "<Y"},
    "|Z": {"XY": "|Z", "YZ": "|X", "XZ": "|Y"},
    # First-lateral selectors (u-axis: X for XY/XZ, Y for YZ)
    ">X": {"XY": ">X", "YZ": ">Y", "XZ": ">X"},
    "<X": {"XY": "<X", "YZ": "<Y", "XZ": "<X"},
    "|X": {"XY": "|X", "YZ": "|Y", "XZ": "|X"},
    # Second-lateral selectors (v-axis: Y for XY, Z for XZ/YZ)
    ">Y": {"XY": ">Y", "YZ": ">Z", "XZ": ">Z"},
    "<Y": {"XY": "<Y", "YZ": "<Z", "XZ": "<Z"},
    "|Y": {"XY": "|Y", "YZ": "|Z", "XZ": "|Z"},
    # Shell face plane name aliases
    "XY": {"XY": "XY", "YZ": "YZ", "XZ": "XZ"},
}


def _remap_sel(sel: str) -> str:
    """Remap an axial face selector to match the current base plane."""
    row = _AXIAL_REMAP.get(sel)
    if row:
        return row.get(_current_base_plane, sel)
    return sel


def build_from_program(program: Program):
    """Execute a Program and return the CadQuery Workplane result."""
    import cadquery as cq

    global _current_base_plane, _pending_sketch

    _patch_ocp_hashcode()
    _current_base_plane = program.base_plane or "XY"
    _pending_sketch = None
    wp = cq.Workplane(_current_base_plane)
    for op in program.ops:
        wp = _apply_op(wp, op)
    return wp


# ---------------------------------------------------------------------------
# Op → Python source
# ---------------------------------------------------------------------------


def _op_to_code(op: Op) -> str:
    """Render one Op as a CadQuery method call string."""
    global _pending_sketch_code
    name = op.name
    a = op.args

    if name == "box":
        centered = a.get("centered", True)
        if centered:
            return f".box({a['length']}, {a['width']}, {a['height']})"
        return f".box({a['length']}, {a['width']}, {a['height']}, centered=False)"
    elif name == "cylinder":
        return f".cylinder({a['height']}, {a['radius']})"
    elif name == "circle":
        return f".circle({a['radius']})"
    elif name == "rect":
        return f".rect({a['length']}, {a['width']})"
    elif name == "extrude":
        taper = a.get("taper", 0)
        both = a.get("both", False)
        if taper and both:
            return f".extrude({a['distance']}, taper={taper}, both=True)"
        if taper:
            return f".extrude({a['distance']}, taper={taper})"
        if both:
            return f".extrude({a['distance']}, both=True)"
        return f".extrude({a['distance']})"
    elif name == "cutThruAll":
        return ".cutThruAll()"
    elif name == "cutBlind":
        return f".cutBlind(-{abs(a['depth'])})"
    elif name == "lineTo":
        return f".lineTo({a['x']}, {a['y']})"
    elif name == "close":
        return ".close()"
    elif name == "hole":
        depth = a.get("depth")
        if depth is not None:
            return f".hole({a['diameter']}, depth={depth})"
        return f".hole({a['diameter']})"
    elif name == "cboreHole":
        depth = a.get("depth")
        base = f".cboreHole({a['diameter']}, {a['cboreDiameter']}, {a['cboreDepth']}"
        if depth is not None:
            base += f", depth={depth}"
        return base + ")"
    elif name == "fillet":
        return f".fillet({a['radius']})"
    elif name == "chamfer":
        return f".chamfer({a['length']})"
    elif name == "shell":
        return f".shell({a['thickness']})"
    elif name == "workplane":
        return f'.faces("{_remap_sel(a["selector"])}").workplane()'
    elif name == "pushPoints":
        return f".pushPoints({a['points']})"
    elif name == "polarArray":
        sa = a.get("startAngle", 0)
        ang = a.get("angle", 360)
        return f".polarArray({a['radius']}, {sa}, {ang}, {a['count']})"
    elif name == "rarray":
        return (
            f".rarray({a['xSpacing']}, {a['ySpacing']}, {a['xCount']}, {a['yCount']})"
        )
    elif name == "center":
        return f".center({a['x']}, {a['y']})"
    elif name == "moveTo":
        return f".moveTo({a['x']}, {a['y']})"
    elif name == "faces":
        return f'.faces("{_remap_sel(a["selector"])}")'
    elif name == "edges":
        sel = a.get("selector")
        return f'.edges("{_remap_sel(sel)}")' if sel else ".edges()"
    elif name == "revolve":
        ax0 = a.get("axisStart", (0, 0, 0))
        ax1 = a.get("axisEnd", (0, 1, 0))
        return f".revolve({a['angleDeg']}, {tuple(ax0)}, {tuple(ax1)})"
    elif name == "loft":
        combine = a.get("combine", True)
        return f".loft(combine={combine})"
    elif name == "polyline":
        return f".polyline({a['points']})"
    elif name == "mirrorY":
        return ".mirrorY()"
    elif name == "mirrorX":
        return ".mirrorX()"
    elif name == "polygon":
        return f".polygon({a['n']}, {a['diameter']})"
    elif name == "slot2D":
        ang = a.get("angle", 0)
        return f".slot2D({a['length']}, {a['width']}, {ang})"
    elif name == "ellipse":
        return f".ellipse({a['xRadius']}, {a['yRadius']})"
    elif name == "threePointArc":
        return f".threePointArc({tuple(a['point1'])}, {tuple(a['point2'])})"
    elif name == "sphere":
        return f".sphere({a['radius']})"
    elif name == "torus":
        pnt = tuple(a.get("pnt", (0, 0, 0)))
        dir_ = tuple(a.get("dir", (0, 0, 1)))
        return (
            f'.union(cq.Workplane("XY").newObject(['
            f"cq.Solid.makeTorus({a['majorRadius']}, {a['minorRadius']}, "
            f"cq.Vector{pnt}, cq.Vector{dir_})]))"
        )
    elif name == "transformed":
        off = a.get("offset", [0, 0, 0])
        rot = a.get("rotate", [0, 0, 0])
        return (
            f".transformed(offset=cq.Vector{tuple(off)}, rotate=cq.Vector{tuple(rot)})"
        )
    elif name == "cskHole":
        depth = a.get("depth")
        base = f".cskHole({a['diameter']}, {a['cskDiameter']}, {a['cskAngle']}"
        if depth is not None:
            base += f", depth={depth}"
        return base + ")"
    elif name == "hLine":
        return f".hLine({a['distance']})"
    elif name == "vLine":
        return f".vLine({a['distance']})"
    elif name == "workplane_offset":
        return f".workplane(offset={a['offset']})"
    elif name in ("union", "cut"):
        sub_plane = a.get("plane", _current_base_plane)
        sub_lines = "".join(
            f"\n        {_op_to_code(Op(o['name'], o.get('args', {})))}"
            for o in a["ops"]
        )
        return f'.{name}(\n    cq.Workplane("{sub_plane}"){sub_lines}\n)'
    elif name == "sweep":
        path_type = a["path_type"]
        is_frenet = a.get("isFrenet", path_type == "helix")
        if path_type == "helix":
            pa = a["path_args"]
            return (
                f'.sweep(cq.Wire.makeHelix({pa["pitch"]}, {pa["height"]}, {pa["radius"]})'
                f", isFrenet={is_frenet})"
            )
        elif path_type == "helix_with_legs":
            pa = a["path_args"]
            return (
                f".sweep(\n"
                f"    _helix_with_legs_path({pa['pitch']}, {pa['height']},"
                f" {pa['radius']}, {pa['leg_length']}),\n"
                f"    isFrenet={is_frenet})"
            )
        elif path_type == "elbow_arc":
            ll, br, tl = a["lead_length"], a["bend_radius"], a["trail_length"]
            return (
                f".sweep(\n"
                f'    cq.Workplane("XZ").moveTo(0.0,0.0).lineTo(0.0,{ll})'
                f".radiusArc(({br},{ll+br}),{br}).lineTo({br+tl},{ll+br}),\n"
                f"    isFrenet=True)"
            )
        else:
            pts = a["path_points"]
            plane = a.get("path_plane", "XZ")
            method = "spline" if path_type == "spline" else "polyline"
            return (
                f'.sweep(cq.Workplane("{plane}").{method}({pts}), isFrenet={is_frenet})'
            )
    elif name == "sketch_subtract":
        face_exprs = []
        for prof in a["profiles"]:
            wire_chain = "".join(
                _op_to_code(Op(o["name"], o.get("args", {}))) for o in prof["wire_ops"]
            )
            wire_expr = f'cq.Workplane("{_current_base_plane}"){wire_chain}'
            rot = prof.get("rotate_deg", 0.0)
            if rot:
                wire_expr = f"{wire_expr}.rotate((0,0,0),(0,0,1),{rot})"
            face_exprs.append(f'\n        .face({wire_expr}.val(), mode="s")')
        _pending_sketch_code = (
            f"(\n        cq.Sketch()"
            f"\n        .circle({a['outer_radius']})"
            f"{''.join(face_exprs)}"
            f"\n        .clean()\n    )"
        )
        return ""  # placeSketch emits the inlined Sketch expression
    elif name == "placeSketch":
        code = _pending_sketch_code
        _pending_sketch_code = None
        return f".placeSketch{code}"
    elif name == "twistExtrude":
        return f".twistExtrude({a['distance']}, {a['angle']})"
    elif name == "intersect":
        sub_lines = "".join(
            f"\n        {_op_to_code(Op(o['name'], o.get('args', {})))}"
            for o in a["ops"]
        )
        return f'.intersect(\n    cq.Workplane("{_current_base_plane}"){sub_lines}\n)'
    else:
        raise ValueError(f"Unknown op: {name}")


def render_program_to_code(program: Program, include_params_hint: bool = False) -> str:
    """Render a Program to an executable Python source string.

    If include_params_hint is True, emits a `# --- parameters ---` comment
    block listing numeric params at the top (for edit-bench, where models
    need to ground instructions to parameter semantics). Default False to
    preserve byte-identical output for existing pipeline consumers.
    """
    global _current_base_plane, _pending_sketch_code
    bp = program.base_plane or "XY"
    _current_base_plane = bp
    _pending_sketch_code = None

    def _uses_helix_with_legs(ops):
        for o in ops:
            if o.name == "sweep" and o.args.get("path_type") == "helix_with_legs":
                return True
            sub = o.args.get("ops") if isinstance(o.args, dict) else None
            if sub:
                for s in sub:
                    if (
                        s.get("name") == "sweep"
                        and s.get("args", {}).get("path_type") == "helix_with_legs"
                    ):
                        return True
        return False

    lines = ["import cadquery as cq"]
    if include_params_hint and program.params:
        hint_lines = ["", "# --- parameters ---"]
        for k, v in program.params.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                hint_lines.append(f"# {k} = {v}")
        if len(hint_lines) > 2:
            lines += hint_lines
    if _uses_helix_with_legs(program.ops):
        lines += [
            "import math",
            "",
            "def _helix_with_legs_path(pitch, height, radius, leg_length):",
            "    helix = cq.Wire.makeHelix(pitch, height, radius)",
            "    v = helix.Vertices()",
            "    p0 = cq.Vector(v[0].X, v[0].Y, v[0].Z)",
            "    p1 = cq.Vector(v[1].X, v[1].Y, v[1].Z)",
            "    dz = pitch / (2 * math.pi)",
            "    t0 = 0.0",
            "    t1 = 2 * math.pi * height / pitch",
            "    tan0 = cq.Vector(-radius*math.sin(t0), radius*math.cos(t0), dz)",
            "    tan1 = cq.Vector(-radius*math.sin(t1), radius*math.cos(t1), dz)",
            "    m0 = math.sqrt(tan0.x**2 + tan0.y**2 + tan0.z**2)",
            "    m1 = math.sqrt(tan1.x**2 + tan1.y**2 + tan1.z**2)",
            "    tan0n = cq.Vector(tan0.x/m0, tan0.y/m0, tan0.z/m0)",
            "    tan1n = cq.Vector(tan1.x/m1, tan1.y/m1, tan1.z/m1)",
            "    leg1 = cq.Edge.makeLine(p0 - tan0n.multiply(leg_length), p0)",
            "    leg2 = cq.Edge.makeLine(p1, p1 + tan1n.multiply(leg_length))",
            "    return cq.Wire.assembleEdges([leg1] + list(helix.Edges()) + [leg2])",
        ]
    lines += ["", "result = (", f'    cq.Workplane("{bp}")']
    for op in program.ops:
        code = _op_to_code(op)
        if not code:  # sketch_subtract is state-only; placeSketch emits the Sketch
            continue
        # Re-indent every line of multi-line ops (union/cut/sweep)
        indented = "\n".join("    " + line for line in code.split("\n"))
        lines.append(indented)
    lines.append(")")
    lines.append("")
    # Export helpers
    lines.append("# Export")
    lines.append("show_object(result)")
    return "\n".join(lines)
