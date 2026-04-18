#!/usr/bin/env python
"""Generate synthetic CadQuery training pairs with diverse operations.

Produces (params_json, cq_code, gt_step) triplets covering ops absent
from the Fusion360 extrude-only dataset: revolve, fillet, chamfer, loft,
shell, polar_array, sweep.

Outputs into data/data_generation/codex_validation/run_synthetic_diverse/ and appends
passing pairs to data/data_generation/verified/verified_pairs.jsonl.

Usage:
    uv run python scripts/data_generation/generate_synth_diverse.py
    uv run python scripts/data_generation/generate_synth_diverse.py --n 50 --ops revolve fillet
    uv run python scripts/data_generation/generate_synth_diverse.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

_LD = "/workspace/.local/lib"
_cur = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur}".strip(":")

OUT_DIR = REPO_ROOT / "data/data_generation/codex_validation/run_synthetic_diverse"
VERIFIED_PAIRS = REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl"
RUN_NAME = "run_synthetic_diverse"

rng = random.Random()


# ── helpers ──────────────────────────────────────────────────────────────────

def _r(lo, hi, dp=1):
    """Random float in [lo,hi] rounded to dp decimal places."""
    return round(rng.uniform(lo, hi), dp)


def _ri(lo, hi):
    return rng.randint(lo, hi)


def _execute(code: str, out_step: Path, timeout: int = 30) -> tuple[bool, str | None]:
    """Execute CadQuery code, return (ok, error)."""
    # Inject hashcode fix
    fix = (
        "try:\n"
        "    from cadquery.occ_impl.shapes import Shape as _S\n"
        "    if not getattr(_S,'_hcp',False):\n"
        "        _oh=_S.hashCode\n"
        "        def _nh(self):\n"
        "            try: return _oh(self)\n"
        "            except (AttributeError,TypeError): return id(self.wrapped)\n"
        "        _S.hashCode=_nh; _S._hcp=True\n"
        "except Exception: pass\n"
    )
    patched = fix + code.replace("'output.step'", repr(str(out_step))).replace(
        '"output.step"', repr(str(out_step))
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(patched)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return False, r.stderr.strip()[:300]
        if not out_step.exists():
            return False, "no STEP produced"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        Path(tmp).unlink(missing_ok=True)


def _append_pair(rec: dict) -> None:
    VERIFIED_PAIRS.parent.mkdir(parents=True, exist_ok=True)
    with VERIFIED_PAIRS.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


# ── generators ───────────────────────────────────────────────────────────────

def gen_revolve_ring() -> tuple[dict, str]:
    """Hollow ring: rectangular cross-section revolved 360°."""
    inner_r = _r(8, 40)
    wall = _r(4, 20)
    outer_r = round(inner_r + wall, 1)
    h = _r(4, 30)
    params = {"op": "revolve_ring", "inner_r_mm": inner_r, "outer_r_mm": outer_r, "height_mm": h}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XZ')\n"
        f"    .moveTo({inner_r}, 0).lineTo({outer_r}, 0)\n"
        f"    .lineTo({outer_r}, {h}).lineTo({inner_r}, {h}).close()\n"
        f"    .revolve(360, (0, 0, 0), (0, 1, 0))\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_revolve_solid_cylinder() -> tuple[dict, str]:
    """Solid cylinder via revolve (alternative to extrude+circle)."""
    r = _r(5, 50)
    h = _r(5, 80)
    params = {"op": "revolve_cylinder", "radius_mm": r, "height_mm": h}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XZ')\n"
        f"    .moveTo(0, 0).lineTo({r}, 0)\n"
        f"    .lineTo({r}, {h}).lineTo(0, {h}).close()\n"
        f"    .revolve(360, (0, 0, 0), (0, 1, 0))\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_revolve_partial() -> tuple[dict, str]:
    """Partial revolve (sector/arc solid)."""
    r = _r(10, 50)
    h = _r(4, 20)
    angle = _ri(60, 300)
    params = {"op": "revolve_partial", "radius_mm": r, "height_mm": h, "angle_deg": angle}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XZ')\n"
        f"    .moveTo(0, 0).lineTo({r}, 0)\n"
        f"    .lineTo({r}, {h}).lineTo(0, {h}).close()\n"
        f"    .revolve({angle}, (0, 0, 0), (0, 1, 0))\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_extrude_fillet_vertical() -> tuple[dict, str]:
    """Rectangular block with fillets on vertical (Z) edges."""
    w, d, h = _r(20, 80), _r(15, 60), _r(10, 50)
    r = round(min(w, d) * _r(0.05, 0.25), 1)
    params = {"op": "extrude_fillet_vertical", "w_mm": w, "d_mm": d, "h_mm": h, "fillet_r_mm": r}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .edges('|Z').fillet({r})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_extrude_fillet_all() -> tuple[dict, str]:
    """Block with all edges filleted."""
    w, d, h = _r(20, 80), _r(15, 60), _r(10, 50)
    r = round(min(w, d, h) * _r(0.05, 0.18), 1)
    params = {"op": "extrude_fillet_all", "w_mm": w, "d_mm": d, "h_mm": h, "fillet_r_mm": r}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .edges().fillet({r})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_extrude_fillet_top() -> tuple[dict, str]:
    """Block with top face edges filleted."""
    w, d, h = _r(20, 80), _r(15, 60), _r(10, 50)
    r = round(min(w, d) * _r(0.05, 0.22), 1)
    params = {"op": "extrude_fillet_top", "w_mm": w, "d_mm": d, "h_mm": h, "fillet_r_mm": r}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .edges('>Z').fillet({r})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_cylinder_fillet() -> tuple[dict, str]:
    """Cylinder with top/bottom edge fillets."""
    r = _r(8, 40)
    h = _r(10, 60)
    fr = round(min(r, h) * _r(0.05, 0.2), 1)
    params = {"op": "cylinder_fillet", "radius_mm": r, "height_mm": h, "fillet_r_mm": fr}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').circle({r}).extrude({h})\n"
        f"    .edges().fillet({fr})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_extrude_chamfer() -> tuple[dict, str]:
    """Block with chamfered edges."""
    w, d, h = _r(20, 80), _r(15, 60), _r(10, 50)
    c = round(min(w, d, h) * _r(0.04, 0.15), 1)
    sel = rng.choice(["|Z", ">Z", "<Z"])
    params = {"op": "extrude_chamfer", "w_mm": w, "d_mm": d, "h_mm": h, "chamfer_mm": c, "sel": sel}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .edges('{sel}').chamfer({c})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_shell_box() -> tuple[dict, str]:
    """Hollow box via shell (open on top)."""
    w, d, h = _r(30, 100), _r(25, 80), _r(20, 60)
    t = _r(2, min(w, d, h) * 0.15)
    t = round(t, 1)
    params = {"op": "shell_box", "w_mm": w, "d_mm": d, "h_mm": h, "wall_t_mm": t}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .faces('>Z').shell(-{t})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_shell_cylinder() -> tuple[dict, str]:
    """Hollow cylinder (cup) via shell."""
    r = _r(15, 50)
    h = _r(20, 80)
    t = round(min(r * 0.15, 5), 1)
    params = {"op": "shell_cylinder", "radius_mm": r, "height_mm": h, "wall_t_mm": t}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').circle({r}).extrude({h})\n"
        f"    .faces('>Z').shell(-{t})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_loft_circle_to_rect() -> tuple[dict, str]:
    """Loft from circle (bottom) to rectangle (top)."""
    r = _r(10, 35)
    w, d = _r(30, 80), _r(20, 60)
    h = _r(15, 60)
    params = {"op": "loft_circle_rect", "circle_r_mm": r, "rect_w_mm": w, "rect_d_mm": d, "height_mm": h}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY')\n"
        f"    .circle({r})\n"
        f"    .workplane(offset={h})\n"
        f"    .rect({w}, {d})\n"
        f"    .loft()\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_loft_two_circles() -> tuple[dict, str]:
    """Loft between two circles of different radii (frustum-like)."""
    r1 = _r(10, 40)
    r2 = _r(5, r1 * 0.9)
    h = _r(15, 60)
    params = {"op": "loft_two_circles", "bottom_r_mm": r1, "top_r_mm": r2, "height_mm": h}
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY')\n"
        f"    .circle({r1})\n"
        f"    .workplane(offset={h})\n"
        f"    .circle({r2})\n"
        f"    .loft()\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_polar_array_holes() -> tuple[dict, str]:
    """Circular disc with polar array of through-holes."""
    disc_r = _r(25, 60)
    disc_h = _r(4, 20)
    n_holes = _ri(3, 8)
    hole_r_max = disc_r * 0.25
    hole_r = round(rng.uniform(2, hole_r_max), 1)
    bolt_r = round(disc_r * _r(0.5, 0.75), 1)
    params = {
        "op": "polar_array_holes",
        "disc_r_mm": disc_r, "disc_h_mm": disc_h,
        "n_holes": n_holes, "hole_d_mm": hole_r * 2, "bolt_circle_r_mm": bolt_r,
    }
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').circle({disc_r}).extrude({disc_h})\n"
        f"    .faces('>Z').workplane()\n"
        f"    .polarArray({bolt_r}, 0, 360, {n_holes})\n"
        f"    .hole({hole_r * 2})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_polar_array_bosses() -> tuple[dict, str]:
    """Base plate with polar array of extruded bosses."""
    base_r = _r(30, 70)
    base_h = _r(5, 15)
    n = _ri(3, 6)
    boss_r = round(base_r * _r(0.08, 0.18), 1)
    bolt_r = round(base_r * _r(0.5, 0.75), 1)
    boss_h = _r(4, 15)
    params = {
        "op": "polar_array_bosses",
        "base_r_mm": base_r, "base_h_mm": base_h,
        "n_bosses": n, "boss_r_mm": boss_r, "boss_h_mm": boss_h,
        "bolt_circle_r_mm": bolt_r,
    }
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').circle({base_r}).extrude({base_h})\n"
        f"    .faces('>Z').workplane()\n"
        f"    .polarArray({bolt_r}, 0, 360, {n})\n"
        f"    .circle({boss_r}).extrude({boss_h})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_rect_array_holes() -> tuple[dict, str]:
    """Rectangular plate with grid of holes."""
    w, d = _r(60, 150), _r(40, 100)
    h = _r(5, 20)
    nx, ny = _ri(2, 5), _ri(2, 4)
    xs = round(w / (nx + 1), 1)
    ys = round(d / (ny + 1), 1)
    hole_d = round(min(xs, ys) * _r(0.2, 0.45), 1)
    params = {
        "op": "rect_array_holes",
        "w_mm": w, "d_mm": d, "h_mm": h,
        "nx": nx, "ny": ny, "hole_d_mm": hole_d,
        "xs_mm": xs, "ys_mm": ys,
    }
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .faces('>Z').workplane()\n"
        f"    .rarray({xs}, {ys}, {nx}, {ny})\n"
        f"    .hole({hole_d})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_extrude_cut_fillet() -> tuple[dict, str]:
    """Block with cylindrical cutout, then fillet on remaining edges."""
    w, d, h = _r(40, 100), _r(30, 80), _r(15, 50)
    cut_r = round(min(w, d) * _r(0.1, 0.3), 1)
    fr = round(min(w, d) * _r(0.03, 0.1), 1)
    params = {
        "op": "extrude_cut_fillet",
        "w_mm": w, "d_mm": d, "h_mm": h,
        "cut_r_mm": cut_r, "fillet_r_mm": fr,
    }
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XY').rect({w}, {d}).extrude({h})\n"
        f"    .faces('>Z').workplane().hole({cut_r * 2})\n"
        f"    .edges('|Z').fillet({fr})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


def gen_revolve_fillet() -> tuple[dict, str]:
    """Ring with fillets on inner/outer edges."""
    inner_r = _r(10, 35)
    wall = _r(5, 20)
    outer_r = round(inner_r + wall, 1)
    h = _r(6, 25)
    fr = round(min(wall, h) * _r(0.1, 0.25), 1)
    params = {
        "op": "revolve_fillet",
        "inner_r_mm": inner_r, "outer_r_mm": outer_r,
        "height_mm": h, "fillet_r_mm": fr,
    }
    code = (
        "import cadquery as cq\n"
        f"result = (\n"
        f"    cq.Workplane('XZ')\n"
        f"    .moveTo({inner_r}, 0).lineTo({outer_r}, 0)\n"
        f"    .lineTo({outer_r}, {h}).lineTo({inner_r}, {h}).close()\n"
        f"    .revolve(360, (0, 0, 0), (0, 1, 0))\n"
        f"    .edges().fillet({fr})\n"
        f")\n"
        "result.val().exportStep('output.step')\n"
    )
    return params, code


# ── registry ─────────────────────────────────────────────────────────────────

GENERATORS: dict[str, list] = {
    "revolve":      [gen_revolve_ring, gen_revolve_solid_cylinder, gen_revolve_partial],
    "fillet":       [gen_extrude_fillet_vertical, gen_extrude_fillet_all,
                     gen_extrude_fillet_top, gen_cylinder_fillet],
    "chamfer":      [gen_extrude_chamfer],
    "shell":        [gen_shell_box, gen_shell_cylinder],
    "loft":         [gen_loft_circle_to_rect, gen_loft_two_circles],
    "polar_array":  [gen_polar_array_holes, gen_polar_array_bosses],
    "rect_array":   [gen_rect_array_holes],
    "combo":        [gen_extrude_cut_fillet, gen_revolve_fillet],
}

ALL_OPS = list(GENERATORS)


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=60,
                        help="Examples per op category (default 60)")
    parser.add_argument("--ops", nargs="+", default=ALL_OPS,
                        choices=ALL_OPS, metavar="OP",
                        help="Op categories to generate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate code but don't execute or save")
    parser.add_argument("--no-harvest", action="store_true",
                        help="Don't append to verified_pairs.jsonl")
    args = parser.parse_args()

    rng.seed(args.seed)

    step_dir = OUT_DIR / "generated_step"
    cq_dir = OUT_DIR / "cadquery"
    step_dir.mkdir(parents=True, exist_ok=True)
    cq_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_ok = total_fail = 0

    for op_name in args.ops:
        gens = GENERATORS[op_name]
        ok = fail = 0
        idx = 0
        attempts = 0
        print(f"\n[{op_name}] targeting {args.n} passing examples")

        while ok < args.n and attempts < args.n * 8:
            attempts += 1
            gen_fn = gens[idx % len(gens)]
            idx += 1

            try:
                params, code = gen_fn()
            except Exception as e:
                print(f"  gen error: {e}")
                fail += 1
                continue

            stem = f"synth_{op_name}_{ok:04d}_s{args.seed}"

            if args.dry_run:
                print(f"  DRY {stem}: {params}")
                ok += 1
                continue

            out_step = step_dir / f"{stem}.step"
            cq_file = cq_dir / f"{stem}.py"
            cq_file.write_text(code, encoding="utf-8")

            success, err = _execute(code, out_step)
            if not success:
                print(f"  FAIL {stem}: {(err or '')[:80]}")
                fail += 1
                cq_file.unlink(missing_ok=True)
                continue

            print(f"  OK   {stem}: {params}")
            ok += 1

            if not args.no_harvest:
                record = {
                    "stem": stem,
                    "base_stem": stem,
                    "raw_step_path": None,
                    "ops_json_path": None,
                    "gen_step_path": _rel(out_step),
                    "cq_code_path": _rel(cq_file),
                    "views_raw_dir": None,
                    "views_gen_dir": None,
                    "complexity_class": op_name,
                    "iou": 1.0,
                    "visual_verdict": "SKIP",
                    "visual_reason": "self-generated GT",
                    "verified": True,
                    "source": RUN_NAME,
                    "timestamp": now,
                    "params": params,
                }
                _append_pair(record)

        total_ok += ok
        total_fail += fail
        print(f"  → {op_name}: {ok} ok, {fail} fail")

    print(f"\nDONE: {total_ok} pairs generated, {total_fail} failed")
    vp_count = sum(1 for _ in VERIFIED_PAIRS.open()) if VERIFIED_PAIRS.exists() else 0
    print(f"verified_pairs.jsonl: {vp_count} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
