"""
Transform CadQuery source code so that the produced geometry is bbox-normalized:
  - bbox center → origin
  - longest extent → 1.0

Given normalization params (cx, cy, cz, scale = 1/longest_extent) derived from
executing the original code or from the GT STEP file.

Handles:
  - ast.Constant floats/ints
  - BinOp expressions like `x * mm` or `x * 10`
  - UnaryOp like `-x`
  - Named variables from simple assignments (e.g. `mm = 10.0`)
  - workplane tracking (XY/XZ/YZ) for correct sketch-center translation
  - .faces().workplane() chains: falls back to scale-only (no translation)
"""

import ast
import copy
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Normalization param extraction
# ---------------------------------------------------------------------------

def get_norm_params(step_path: str) -> tuple[float, float, float, float]:
    """Load STEP, return (cx, cy, cz, scale) where scale = 1/longest_extent."""
    import cadquery as cq
    shape = cq.importers.importStep(str(step_path))
    bb = shape.val().BoundingBox()
    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    cz = (bb.zmin + bb.zmax) / 2
    longest = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
    if longest < 1e-12:
        raise ValueError(f"Degenerate geometry in {step_path}")
    return cx, cy, cz, 1.0 / longest


# ---------------------------------------------------------------------------
# Per-workplane sketch-center helpers
# ---------------------------------------------------------------------------

def _sketch_centers(cx, cy, cz, plane):
    """Return (uc, vc) = translation centers for sketch (u, v) coords."""
    if plane == "XY":
        return cx, cy
    elif plane == "XZ":
        return cx, cz
    elif plane == "YZ":
        return cy, cz
    return 0.0, 0.0  # unknown


def _normal_center(cx, cy, cz, plane):
    """Return center along the workplane normal axis (used for offset=)."""
    if plane == "XY":
        return cz
    elif plane == "XZ":
        return cy
    elif plane == "YZ":
        return cx
    return 0.0


# ---------------------------------------------------------------------------
# Pre-pass: collect simple variable assignments
# ---------------------------------------------------------------------------

def _try_eval_2tuple(node: ast.expr, vars_: dict) -> Optional[tuple]:
    """Try to evaluate a node as a (float, float) pair."""
    if isinstance(node, ast.Tuple) and len(node.elts) == 2:
        v0 = _eval_node_static(node.elts[0], vars_)
        v1 = _eval_node_static(node.elts[1], vars_)
        if v0 is not None and v1 is not None:
            return (v0, v1)
    return None


def _collect_vars(tree: ast.AST) -> dict:
    """
    Collect variable assignments.

    Returns dict mapping name → value where value is:
      float         — simple numeric constant
      (float,float) — 2-element tuple like `pt = (x, y)`
      list          — list of (float,float) tuples like `pts = [(x1,y1), ...]`
    """
    vars_: dict = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0] if len(node.targets) == 1 else None

        # --- single name target: `name = expr` ---
        if isinstance(target, ast.Name):
            name = target.id
            # Simple numeric
            val = _eval_node_static(node.value, vars_)
            if val is not None:
                vars_[name] = val
                continue
            # 2-tuple
            pair = _try_eval_2tuple(node.value, vars_)
            if pair is not None:
                vars_[name] = pair
                continue
            # list of 2-tuples: pts = [(x1,y1), (x2,y2), ...]
            if isinstance(node.value, ast.List):
                items = []
                ok = True
                for elt in node.value.elts:
                    p = _try_eval_2tuple(elt, vars_)
                    if p is None:
                        ok = False
                        break
                    items.append(p)
                if ok and items:
                    vars_[name] = items
                    continue

        # --- tuple-unpack target: `x1, y1 = expr_u, expr_v` ---
        if isinstance(target, ast.Tuple) and all(
            isinstance(e, ast.Name) for e in target.elts
        ):
            if isinstance(node.value, ast.Tuple) and len(node.value.elts) == len(target.elts):
                for tgt_elt, val_elt in zip(target.elts, node.value.elts):
                    v = _eval_node_static(val_elt, vars_)
                    if v is not None:
                        vars_[tgt_elt.id] = v

    return vars_


def _eval_node_static(node: ast.expr, vars_: dict) -> Optional[float]:
    """Try to statically evaluate a numeric expression.  Returns None on failure."""
    import math as _math
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
    elif isinstance(node, ast.Name):
        # math.pi etc. accessible as plain name after `import math`
        if node.id == "pi":
            return _math.pi
        val = vars_.get(node.id)
        return val if isinstance(val, (int, float)) else None
    elif isinstance(node, ast.Attribute):
        # math.pi, math.e, math.sqrt etc.
        if isinstance(node.value, ast.Name) and node.value.id == "math":
            if node.attr == "pi":
                return _math.pi
            if node.attr == "e":
                return _math.e
            if node.attr == "tau":
                return _math.tau
    elif isinstance(node, ast.Call):
        # Python builtins: abs(x), round(x), int(x), float(x), min(a,b), max(a,b), pow(a,b)
        func = node.func
        if isinstance(func, ast.Name) and func.id in ("abs", "round", "int", "float"):
            if len(node.args) == 1 and not node.keywords:
                v = _eval_node_static(node.args[0], vars_)
                if v is not None:
                    fn_map = {"abs": abs, "round": round, "int": int, "float": float}
                    try:
                        return float(fn_map[func.id](v))
                    except (ValueError, TypeError):
                        return None
        if isinstance(func, ast.Name) and func.id in ("min", "max", "pow"):
            if len(node.args) == 2 and not node.keywords:
                a = _eval_node_static(node.args[0], vars_)
                b = _eval_node_static(node.args[1], vars_)
                if a is not None and b is not None:
                    try:
                        return float({"min": min, "max": max, "pow": pow}[func.id](a, b))
                    except (ValueError, ZeroDivisionError):
                        return None
        # math.sqrt(x), math.cos(x), math.sin(x), math.tan(x),
        # math.radians(x), math.degrees(x), math.fabs(x), math.ceil(x), math.floor(x)
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "math":
            fn = func.attr
            if fn in ("sqrt", "cos", "sin", "tan", "radians", "degrees", "fabs", "ceil", "floor", "log", "log2", "log10", "exp"):
                if len(node.args) == 1:
                    v = _eval_node_static(node.args[0], vars_)
                    if v is not None:
                        try:
                            return float(getattr(_math, fn)(v))
                        except (ValueError, ZeroDivisionError):
                            return None
            if fn == "atan2" and len(node.args) == 2:
                y = _eval_node_static(node.args[0], vars_)
                x = _eval_node_static(node.args[1], vars_)
                if y is not None and x is not None:
                    return _math.atan2(y, x)
            if fn == "pow" and len(node.args) == 2:
                base = _eval_node_static(node.args[0], vars_)
                exp_ = _eval_node_static(node.args[1], vars_)
                if base is not None and exp_ is not None:
                    try:
                        return float(base ** exp_)
                    except (ValueError, ZeroDivisionError):
                        return None
            if fn in ("hypot", "copysign") and len(node.args) == 2:
                a = _eval_node_static(node.args[0], vars_)
                b = _eval_node_static(node.args[1], vars_)
                if a is not None and b is not None:
                    try:
                        return float(getattr(_math, fn)(a, b))
                    except (ValueError, ZeroDivisionError):
                        return None
    elif isinstance(node, ast.UnaryOp):
        v = _eval_node_static(node.operand, vars_)
        if v is None:
            return None
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
    elif isinstance(node, ast.BinOp):
        left = _eval_node_static(node.left, vars_)
        right = _eval_node_static(node.right, vars_)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Div):
            return (left / right) if right != 0 else None
    elif isinstance(node, ast.Subscript):
        # name[0] or name[1] where name is a (float,float) 2-tuple variable
        if isinstance(node.value, ast.Name):
            pair = vars_.get(node.value.id)
            if isinstance(pair, tuple) and len(pair) == 2:
                idx = _eval_node_static(node.slice, vars_)
                if idx is not None:
                    ii = int(idx)
                    if 0 <= ii < 2:
                        return float(pair[ii])
        # pts[i][j] where pts is list of 2-tuples → scalar (j=0 or 1)
        if isinstance(node.value, ast.Subscript) and isinstance(node.value.value, ast.Name):
            lst = vars_.get(node.value.value.id)
            if isinstance(lst, list):
                i = _eval_node_static(node.value.slice, vars_)
                j = _eval_node_static(node.slice, vars_)
                if i is not None and j is not None:
                    ii, jj = int(i), int(j)
                    if 0 <= ii < len(lst) and isinstance(lst[ii], tuple) and 0 <= jj < len(lst[ii]):
                        return float(lst[ii][jj])
    return None


def _eval_2tuple_node(node: ast.expr, vars_: dict) -> Optional[tuple]:
    """Evaluate node as a (float, float) pair, including pts[i] subscripts."""
    # Direct 2-tuple
    pair = _try_eval_2tuple(node, vars_)
    if pair is not None:
        return pair
    # pts[i] subscript
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        lst = vars_.get(node.value.id)
        if isinstance(lst, list):
            idx = _eval_node_static(node.slice, vars_)
            if idx is not None:
                i = int(idx)
                if 0 <= i < len(lst):
                    return lst[i]
    # Named variable that is a tuple
    if isinstance(node, ast.Name):
        val = vars_.get(node.id)
        if isinstance(val, tuple):
            return val
    return None


# ---------------------------------------------------------------------------
# AST transformer
# ---------------------------------------------------------------------------

class _CQNormalizer(ast.NodeTransformer):
    """
    Walks CQ method-call chains and transforms geometric arguments.

    Workplane tracking:
      self.plane         current workplane name ("XY"/"XZ"/"YZ")
      self.faces_chain   True after .faces() — sketch coords become scale-only
    """

    def __init__(self, cx, cy, cz, scale, vars_):
        self.cx = cx
        self.cy = cy
        self.cz = cz
        self.scale = scale
        self.vars_ = vars_
        self.plane = "XY"
        self.faces_chain = False   # True after .faces(); resets on explicit Workplane()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _eval(self, node) -> Optional[float]:
        return _eval_node_static(node, self.vars_)

    def _sc(self, val: float) -> float:
        """Scale only (distances, radii)."""
        return val * self.scale

    def _tc(self, val: float, center: float) -> float:
        """Translate then scale (absolute positions)."""
        return (val - center) * self.scale

    @staticmethod
    def _c(val: float) -> ast.Constant:
        return ast.Constant(value=round(val, 10))

    def _dist(self, node: ast.expr) -> ast.expr:
        """Transform a distance/size argument (scale only, sign preserved)."""
        v = self._eval(node)
        return self._c(self._sc(v)) if v is not None else node

    def _nxy_wrap(self, node: ast.expr) -> ast.expr:
        """Inline-normalize a 2-tuple Name using the correct plane centers.

        Generates: ((node[0] - uc) * scale, (node[1] - vc) * scale)
        with uc/vc derived from the current workplane — no runtime helper needed.
        """
        if isinstance(node, ast.Name):
            uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
            sc = self.scale

            def _sub_scale(idx: int, center: float) -> ast.expr:
                subscript = ast.Subscript(
                    value=ast.Name(id=node.id, ctx=ast.Load()),
                    slice=ast.Constant(value=idx),
                    ctx=ast.Load(),
                )
                diff = ast.BinOp(left=subscript, op=ast.Sub(),
                                 right=ast.Constant(value=round(center, 10)))
                return ast.BinOp(left=diff, op=ast.Mult(),
                                 right=ast.Constant(value=round(sc, 10)))

            return ast.Tuple(elts=[_sub_scale(0, uc), _sub_scale(1, vc)],
                             ctx=ast.Load())
        return node

    def _pos(self, node: ast.expr, center: float) -> ast.expr:
        """Transform a positional argument (translate + scale)."""
        if self.faces_chain:
            return self._dist(node)   # lose absolute position after .faces()
        v = self._eval(node)
        return self._c(self._tc(v, center)) if v is not None else node

    def _sketch_u(self, node):
        uc, _ = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
        return self._pos(node, uc)

    def _sketch_v(self, node):
        _, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
        return self._pos(node, vc)

    def _expand_starred_uv(self, starred_node):
        """
        Expand `*expr` in a moveTo/lineTo context.

        Handles *varname and *pts[i] — returns two transformed Constant nodes
        [u_norm, v_norm] if the expression evaluates to a (u, v) pair.
        """
        if not isinstance(starred_node, ast.Starred):
            return None
        pair = _eval_2tuple_node(starred_node.value, self.vars_)
        if pair is None:
            return None
        uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
        u_new = self._c(self._tc(pair[0], uc) if not self.faces_chain
                        else pair[0] * self.scale)
        v_new = self._c(self._tc(pair[1], vc) if not self.faces_chain
                        else pair[1] * self.scale)
        return [u_new, v_new]

    def _offset(self, node):
        # workplane(offset=d) is a relative distance along normal — scale only, no translation
        return self._dist(node)

    # ------------------------------------------------------------------
    # tuple helpers
    # ------------------------------------------------------------------

    def _transform_uv_tuple(self, tup: ast.Tuple) -> ast.Tuple:
        """Transform (u, v) sketch-coordinate tuple."""
        if len(tup.elts) == 2:
            new_elts = [self._sketch_u(tup.elts[0]), self._sketch_v(tup.elts[1])]
            return ast.Tuple(elts=new_elts, ctx=tup.ctx)
        return tup

    def _transform_xyz_tuple(self, tup: ast.Tuple) -> ast.Tuple:
        """Transform (x, y, z) world-coordinate tuple (e.g. Workplane origin=)."""
        if len(tup.elts) == 3:
            new_elts = [
                self._pos(tup.elts[0], self.cx),
                self._pos(tup.elts[1], self.cy),
                self._pos(tup.elts[2], self.cz),
            ]
            return ast.Tuple(elts=new_elts, ctx=tup.ctx)
        return tup

    def _transform_local_offset_tuple(self, tup: ast.Tuple) -> ast.Tuple:
        """Transform transformed(offset=(a,b,c)) in local workplane coords.

        CadQuery .transformed(offset=) is in local workplane axes:
          XY: a=worldX(cx), b=worldY(cy), c=worldZ(cz) [normal=+Z]
          XZ: a=worldX(cx), b=worldZ(cz), c=-worldY → center=-cy  [normal=-Y]
          YZ: a=worldY(cy), b=worldZ(cz), c=worldX(cx) [normal=+X]
        """
        if len(tup.elts) != 3:
            return tup
        plane = self.plane
        if plane == "XZ":
            # a→worldX, b→worldZ, c→-worldY (normal=-Y, so c=-worldY → center=-cy)
            new_elts = [
                self._pos(tup.elts[0], self.cx),
                self._pos(tup.elts[1], self.cz),
                self._pos(tup.elts[2], -self.cy),
            ]
        elif plane == "YZ":
            # a→worldY, b→worldZ, c→worldX (normal=+X)
            new_elts = [
                self._pos(tup.elts[0], self.cy),
                self._pos(tup.elts[1], self.cz),
                self._pos(tup.elts[2], self.cx),
            ]
        else:  # XY (normal=+Z): a→worldX, b→worldY, c→worldZ
            new_elts = [
                self._pos(tup.elts[0], self.cx),
                self._pos(tup.elts[1], self.cy),
                self._pos(tup.elts[2], self.cz),
            ]
        return ast.Tuple(elts=new_elts, ctx=tup.ctx)

    # ------------------------------------------------------------------
    # visit_Call — main transformation entry point
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> ast.AST:
        # --- descend into non-target children first ---
        # (We'll handle target args manually below)
        func = node.func

        # Not a method call: visit normally
        if not isinstance(func, ast.Attribute):
            return self.generic_visit(node)

        method = func.attr
        args = node.args
        kwargs = {kw.arg: kw for kw in node.keywords}

        # Visit the receiver (left-hand chain) — may update self.plane / self.faces_chain
        new_func_value = self.visit(func.value)
        new_func = ast.Attribute(value=new_func_value, attr=func.attr, ctx=func.ctx)

        # ----------------------------------------------------------------
        def build(new_args, new_keywords=None):
            if new_keywords is None:
                new_keywords = [self.visit(kw) for kw in node.keywords]
            return ast.Call(func=new_func, args=new_args, keywords=new_keywords)

        # ----------------------------------------------------------------
        # Workplane constructor — set current plane, handle origin=
        if method == "Workplane":
            new_args = list(args)
            new_kws = list(node.keywords)
            # First positional arg = plane name string
            if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                p = args[0].value.upper()
                if p in ("XY", "XZ", "YZ"):
                    self.plane = p
                self.faces_chain = False
            # origin= keyword
            for i, kw in enumerate(new_kws):
                if kw.arg == "origin" and isinstance(kw.value, ast.Tuple):
                    new_kws[i] = ast.keyword(
                        arg="origin",
                        value=self._transform_xyz_tuple(kw.value),
                    )
                else:
                    new_kws[i] = self.visit(kw)
            return build(new_args, new_kws)

        # .workplane(offset=d) — relative offset along normal
        if method == "workplane":
            new_kws = []
            for kw in node.keywords:
                if kw.arg == "offset":
                    new_kws.append(ast.keyword(arg="offset", value=self._offset(kw.value)))
                else:
                    new_kws.append(self.visit(kw))
            return build(list(args), new_kws)

        # .faces(...) — lose absolute workplane tracking
        if method == "faces":
            self.faces_chain = True
            return build([self.visit(a) for a in args])

        # .moveTo(u, v) / .lineTo(u, v)  — also handles moveTo(*pt) unpack
        if method in ("moveTo", "lineTo"):
            if len(args) == 1 and isinstance(args[0], ast.Starred):
                expanded = self._expand_starred_uv(args[0])
                if expanded:
                    return build(expanded)
            if len(args) >= 2:
                return build([self._sketch_u(args[0]), self._sketch_v(args[1])]
                             + [self.visit(a) for a in args[2:]])

        # .hLineTo(u) — absolute horizontal position in sketch
        if method == "hLineTo":
            if args:
                return build([self._sketch_u(args[0])] + [self.visit(a) for a in args[1:]])

        # .vLineTo(v) — absolute vertical position in sketch
        if method == "vLineTo":
            if args:
                return build([self._sketch_v(args[0])] + [self.visit(a) for a in args[1:]])

        # .radiusArc((u, v), r) — also handles named-variable tuple arg
        if method == "radiusArc":
            if len(args) >= 2:
                pt = args[0]
                if isinstance(pt, ast.Tuple):
                    pt = self._transform_uv_tuple(pt)
                elif isinstance(pt, ast.Name):
                    pair = _eval_2tuple_node(pt, self.vars_)
                    if pair is not None:
                        uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
                        nu = self._tc(pair[0], uc) if not self.faces_chain else pair[0]*self.scale
                        nv = self._tc(pair[1], vc) if not self.faces_chain else pair[1]*self.scale
                        pt = ast.Tuple(elts=[self._c(nu), self._c(nv)], ctx=ast.Load())
                    else:
                        pt = self._nxy_wrap(pt)
                r_node = self._dist(args[1])  # scale only, preserve sign
                return build([pt, r_node] + [self.visit(a) for a in args[2:]])

        # .threePointArc((u1,v1), (u2,v2))  — handles Tuple, Starred, and named-variable args
        if method == "threePointArc":
            uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
            new_args = []
            for a in args:
                if isinstance(a, ast.Tuple):
                    new_args.append(self._transform_uv_tuple(a))
                elif isinstance(a, ast.Starred):
                    expanded = self._expand_starred_uv(a)
                    if expanded:
                        new_args.append(ast.Tuple(elts=expanded, ctx=ast.Load()))
                    else:
                        new_args.append(self.visit(a))
                elif isinstance(a, ast.Name):
                    pair = _eval_2tuple_node(a, self.vars_)
                    if pair is not None:
                        nu = self._tc(pair[0], uc) if not self.faces_chain else pair[0]*self.scale
                        nv = self._tc(pair[1], vc) if not self.faces_chain else pair[1]*self.scale
                        new_args.append(ast.Tuple(elts=[self._c(nu), self._c(nv)], ctx=ast.Load()))
                    else:
                        new_args.append(self._nxy_wrap(a))
                else:
                    new_args.append(self.visit(a))
            return build(new_args)

        # .translate((x, y, z)) — relative displacement, scale only (no centering)
        if method == "translate":
            if args:
                arg = args[0]
                if isinstance(arg, ast.Tuple) and len(arg.elts) == 3:
                    new_elts = [self._dist(e) for e in arg.elts]
                    return build([ast.Tuple(elts=new_elts, ctx=arg.ctx)]
                                 + [self.visit(a) for a in args[1:]])

        # .transformed(offset=(a,b,c)) — local workplane 3D offset
        if method == "transformed":
            new_kws = []
            for kw in node.keywords:
                if kw.arg == "offset" and isinstance(kw.value, ast.Tuple):
                    new_kws.append(ast.keyword(
                        arg="offset",
                        value=self._transform_local_offset_tuple(kw.value),
                    ))
                else:
                    new_kws.append(self.visit(kw))
            return build([self.visit(a) for a in args], new_kws)

        # .center(du, dv) — relative shift in sketch, scale only
        if method == "center":
            if len(args) >= 2:
                return build([self._dist(args[0]), self._dist(args[1])]
                             + [self.visit(a) for a in args[2:]])

        # Distances / sizes — scale only
        if method in ("extrude", "cutBlind"):
            if args:
                return build([self._dist(args[0])] + [self.visit(a) for a in args[1:]])

        if method == "circle":
            if args:
                return build([self._dist(args[0])] + [self.visit(a) for a in args[1:]])

        if method == "rect":
            if len(args) >= 2:
                return build([self._dist(args[0]), self._dist(args[1])]
                             + [self.visit(a) for a in args[2:]])

        if method in ("fillet", "chamfer"):
            if args:
                return build([self._dist(args[0])] + [self.visit(a) for a in args[1:]])

        if method == "slot2D":
            if len(args) >= 2:
                return build([self._dist(args[0]), self._dist(args[1])]
                             + [self.visit(a) for a in args[2:]])

        if method == "hole":
            if args:
                return build([self._dist(args[0])] + [self.visit(a) for a in args[1:]])

        # .shell(thickness) — wall thickness is a signed distance
        if method == "shell":
            if args:
                return build([self._dist(args[0])] + [self.visit(a) for a in args[1:]])

        # .ellipse(rx, ry) — both radii scaled
        if method == "ellipse":
            if len(args) >= 2:
                return build([self._dist(args[0]), self._dist(args[1])]
                             + [self.visit(a) for a in args[2:]])

        # .tangentArcPoint((u, v)) — endpoint of tangent arc, absolute sketch position
        if method == "tangentArcPoint":
            if args:
                a = args[0]
                if isinstance(a, ast.Tuple):
                    a = self._transform_uv_tuple(a)
                elif isinstance(a, ast.Name):
                    pair = _eval_2tuple_node(a, self.vars_)
                    if pair is not None:
                        uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
                        nu = self._tc(pair[0], uc) if not self.faces_chain else pair[0]*self.scale
                        nv = self._tc(pair[1], vc) if not self.faces_chain else pair[1]*self.scale
                        a = ast.Tuple(elts=[self._c(nu), self._c(nv)], ctx=ast.Load())
                return build([a] + [self.visit(x) for x in args[1:]])

        # .pushPoints([(u,v), ...]) or .pushPoints(pts_var) or .polyline(pts)
        if method in ("pushPoints", "polyline"):
            if len(args) == 1:
                arg = args[0]
                uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)

                def _transform_uv_pair(u, v):
                    # pushPoints/polyline always use sketch-frame coords even after faces_chain
                    return (self._tc(u, uc), self._tc(v, vc))

                # Inline list: pushPoints([(x,y), ...])
                if isinstance(arg, ast.List):
                    new_elts = []
                    for elt in arg.elts:
                        pair = _eval_2tuple_node(elt, self.vars_)
                        if pair is not None:
                            nu, nv = _transform_uv_pair(*pair)
                            new_elts.append(ast.Tuple(
                                elts=[self._c(nu), self._c(nv)], ctx=ast.Load()))
                        else:
                            new_elts.append(self.visit(elt))
                    return build([ast.List(elts=new_elts, ctx=ast.Load())])

                # Variable: pushPoints(centers) where centers is list of tuples
                if isinstance(arg, ast.Name):
                    pts_list = self.vars_.get(arg.id)
                    if isinstance(pts_list, list):
                        new_elts = [
                            ast.Tuple(
                                elts=[self._c(_transform_uv_pair(u, v)[0]),
                                      self._c(_transform_uv_pair(u, v)[1])],
                                ctx=ast.Load())
                            for u, v in pts_list
                        ]
                        return build([ast.List(elts=new_elts, ctx=ast.Load())])

        # .spline(pts) — list of (u, v) sketch control points
        if method == "spline":
            if args:
                arg = args[0]
                uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
                # Inline list of tuples
                if isinstance(arg, ast.List):
                    new_elts = []
                    for elt in arg.elts:
                        pair = _try_eval_2tuple(elt, self.vars_)
                        if pair is not None:
                            nu = self._tc(pair[0], uc) if not self.faces_chain else pair[0]*self.scale
                            nv = self._tc(pair[1], vc) if not self.faces_chain else pair[1]*self.scale
                            new_elts.append(ast.Tuple(elts=[self._c(nu), self._c(nv)], ctx=ast.Load()))
                        else:
                            new_elts.append(self.visit(elt))
                    return build([ast.List(elts=new_elts, ctx=ast.Load())] + [self.visit(a) for a in args[1:]], node.keywords)
                # Named variable holding list of 2-tuples
                if isinstance(arg, ast.Name):
                    pts_list = self.vars_.get(arg.id)
                    if isinstance(pts_list, list):
                        new_elts = [
                            ast.Tuple(
                                elts=[self._c((self._tc(u, uc) if not self.faces_chain else u*self.scale)),
                                      self._c((self._tc(v, vc) if not self.faces_chain else v*self.scale))],
                                ctx=ast.Load())
                            for u, v in pts_list
                        ]
                        return build([ast.List(elts=new_elts, ctx=ast.Load())] + [self.visit(a) for a in args[1:]], node.keywords)

        # .revolve(angle, axisStart, axisEnd) — axis is in LOCAL workplane 3D coords
        # local (a, b, c): a→sketch-u direction, b→sketch-v direction, c→normal (scale only)
        if method == "revolve":
            new_args = [self.visit(args[0])]  # angle: unchanged
            uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
            for axis_arg in args[1:]:
                if isinstance(axis_arg, ast.Tuple) and len(axis_arg.elts) == 3:
                    xs = [_eval_node_static(e, self.vars_) for e in axis_arg.elts]
                    if all(v is not None for v in xs):
                        nu = (xs[0] - uc) * self.scale   # sketch-u component
                        nv = (xs[1] - vc) * self.scale   # sketch-v component
                        nw = xs[2] * self.scale           # normal component (scale only)
                        new_args.append(ast.Tuple(
                            elts=[self._c(nu), self._c(nv), self._c(nw)], ctx=ast.Load()))
                    else:
                        new_args.append(self.visit(axis_arg))
                else:
                    new_args.append(self.visit(axis_arg))
            return build(new_args)

        # .polarArray(radius, startAngle, angle, count) — radius is a distance
        if method == "polarArray":
            if args:
                new_args = [self._dist(args[0])] + [self.visit(a) for a in args[1:]]
                return build(new_args)

        # .rarray(xSpacing, ySpacing, xCount, yCount) — spacings are distances
        if method == "rarray":
            if len(args) >= 2:
                new_args = [self._dist(args[0]), self._dist(args[1])] + [self.visit(a) for a in args[2:]]
                return build(new_args)

        if method == "box":
            # box(x, y, z) — all sizes
            new_args = [self._dist(a) for a in args]
            return build(new_args)

        if method == "cylinder":
            # cylinder(height, radius) — both distances
            new_args = [self._dist(a) for a in args]
            return build(new_args)

        # Default: build new node — do NOT call generic_visit(node) here.
        # generic_visit modifies nodes in-place, which causes double-transformation
        # because new_func_value = self.visit(func.value) already visited func.value,
        # and generic_visit would visit func.value again via node.func.value.
        new_args = [self.visit(a) for a in args]
        new_keywords = [self.visit(kw) for kw in node.keywords]
        return ast.Call(func=new_func, args=new_args, keywords=new_keywords)

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Normalize list-of-2-tuple variable assignments used in for-loop lineTo patterns."""
        target = node.targets[0] if len(node.targets) == 1 else None
        if isinstance(target, ast.Name):
            pts_list = self.vars_.get(target.id)
            if isinstance(pts_list, list) and isinstance(node.value, ast.List):
                uc, vc = _sketch_centers(self.cx, self.cy, self.cz, self.plane)
                new_elts = []
                for elt in node.value.elts:
                    pair = _try_eval_2tuple(elt, self.vars_)
                    if pair is not None:
                        nu = self._tc(pair[0], uc) if not self.faces_chain else pair[0]*self.scale
                        nv = self._tc(pair[1], vc) if not self.faces_chain else pair[1]*self.scale
                        new_elts.append(ast.Tuple(elts=[self._c(nu), self._c(nv)], ctx=ast.Load()))
                    else:
                        new_elts.append(self.visit(elt))
                new_value = ast.List(elts=new_elts, ctx=ast.Load())
                return ast.Assign(
                    targets=node.targets,
                    value=new_value,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                )
        return self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_cq_source(source: str, cx: float, cy: float, cz: float,
                         scale: float) -> str:
    """Transform CQ source string to produce geometry in normalized coordinates."""
    tree = ast.parse(source)
    vars_ = _collect_vars(tree)
    transformer = _CQNormalizer(cx, cy, cz, scale, vars_)
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


def normalize_cq_file(py_path: str, step_path: str,
                       out_path: Optional[str] = None) -> str:
    """
    Normalize a CQ .py file using norm params from step_path.

    Returns the transformed source.  If out_path is given, writes it.
    """
    cx, cy, cz, scale = get_norm_params(step_path)
    source = Path(py_path).read_text()
    norm_source = normalize_cq_source(source, cx, cy, cz, scale)
    if out_path:
        Path(out_path).write_text(norm_source)
    return norm_source


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse, sys
    p = argparse.ArgumentParser()
    p.add_argument("--py", required=True)
    p.add_argument("--step", required=True, help="GT or gen STEP to extract norm params")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    result = normalize_cq_file(args.py, args.step, args.out)
    if not args.out:
        print(result)
