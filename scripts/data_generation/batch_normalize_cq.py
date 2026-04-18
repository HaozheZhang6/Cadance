"""
Batch-normalize CadQuery code for all verified stems.

For each row in verified_parts.csv with cq_code_path + gt_step_path:
  1. Get norm params from gt_step_path (bbox center + scale)
  2. Transform cq_code_path → <stem_fs>/<base>/verified_<run>/cq_norm.py
  3. Execute cq_norm.py → norm STEP → IoU vs gt_norm_step_path
  4. If IoU ≥ 0.95: write norm_cq_code_path to CSV immediately

Output path is ALWAYS in stem-centric FS, never alongside source cq.py.

Usage:
  uv run python3 batch_normalize_cq.py [--limit N] [--offset N] [--validate] [--missing-only]
"""

import argparse
import fcntl
import os
import sys
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]
STEM_FS  = ROOT / "data/data_generation/generated_data/fusion360"
VERIFIED_CSV = ROOT / "data/data_generation/verified_parts.csv"

sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


def _strip_suffix(stem: str) -> str:
    for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
        if stem.endswith(sfx):
            return stem[: -len(sfx)]
    return stem


def _norm_output_path(stem: str, pipeline_run: str) -> Path:
    """Always write cq_norm.py into stem-centric FS, verified_<run>/ folder."""
    base = _strip_suffix(stem)
    run  = (pipeline_run or "unknown").strip()
    return STEM_FS / base / f"verified_{run}" / "cq_norm.py"


_OCP_HASHCODE_FIX = """
import OCP.TopoDS as _tds
if not hasattr(_tds.TopoDS_Shape, "HashCode"):
    _tds.TopoDS_Shape.HashCode = lambda self, upper=2147483647: self.wrapped.HashCode(upper) if hasattr(self, "wrapped") else id(self) % upper
import cadquery as _cq, math as _math
_orig_radiusArc = _cq.Workplane.radiusArc
def _safe_radiusArc(self, endPoint, radius, forConstruction=False):
    from cadquery import Vector
    start = self._findFromPoint(useLocalCoords=True)
    end = Vector(endPoint)
    length = end.sub(start).Length / 2.0
    if length > 0 and abs(radius) < length and abs(radius) > length * (1 - 1e-6):
        radius = _math.copysign(length * (1 + 1e-9), radius)
    return _orig_radiusArc(self, endPoint, radius, forConstruction)
_cq.Workplane.radiusArc = _safe_radiusArc
"""


def _run_py(py_path: str, out_step: str, timeout: int = 60) -> tuple[bool, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = "/workspace/.local/lib"
    code = Path(py_path).read_text()
    code = code.replace('"output.step"', f'"{out_step}"')
    code = code.replace("'output.step'", f'"{out_step}"')
    code = _OCP_HASHCODE_FIX + code
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_py = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp_py],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        if r.returncode != 0:
            return False, r.stderr[-500:]
        if not os.path.isfile(out_step):
            return False, "no output STEP"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(tmp_py):
            os.unlink(tmp_py)


def _iou_normalized(gt_step: str, gen_step: str) -> float:
    """trimesh+manifold3d IoU (paper standard). Both shapes independently normalized."""
    import io
    import cadquery as cq
    import numpy as np
    import trimesh

    def load_and_mesh(path):
        shape = cq.importers.importStep(str(path))
        bb = shape.val().BoundingBox()
        cx = (bb.xmin + bb.xmax) / 2
        cy = (bb.ymin + bb.ymax) / 2
        cz = (bb.zmin + bb.zmax) / 2
        longest = max(bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
        if longest < 1e-12:
            raise ValueError("Degenerate")
        from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        t = gp_Trsf()
        t.SetTranslation(gp_Vec(-cx, -cy, -cz))
        s = gp_Trsf()
        s.SetScale(gp_Pnt(0, 0, 0), 1.0 / longest)
        ts = gp_Trsf()
        ts.Multiply(s)
        ts.Multiply(t)
        norm = cq.Shape(BRepBuilderAPI_Transform(shape.val().wrapped, ts, True).Shape())
        verts, faces = norm.tessellate(0.001, 0.1)
        m = trimesh.Trimesh([(v.x, v.y, v.z) for v in verts], faces)
        buf = trimesh.exchange.stl.export_stl(m)
        return trimesh.load(io.BytesIO(buf), file_type="stl", force="mesh")

    gt_m = load_and_mesh(gt_step)
    gen_m = load_and_mesh(gen_step)

    import manifold3d as m3d

    def to_manifold(mesh):
        return m3d.Manifold(m3d.Mesh(
            vert_properties=np.array(mesh.vertices, dtype=np.float32),
            tri_verts=np.array(mesh.faces, dtype=np.uint32),
        ))

    gt_mani = to_manifold(gt_m)
    gen_mani = to_manifold(gen_m)
    vi = m3d.Manifold.batch_boolean([gt_mani, gen_mani], m3d.OpType.Intersect).volume()
    vu = m3d.Manifold.batch_boolean([gt_mani, gen_mani], m3d.OpType.Add).volume()
    if vu < 1e-12:
        return 0.0
    return max(0.0, min(1.0, vi / vu))


_CSV_LOCK = str(VERIFIED_CSV) + ".lock"


def _write_one(orig_idx: int, norm_cq_path: str, norm_iou: float) -> None:
    """Write norm_cq_code_path + norm_iou + sft_ready to CSV immediately (file-locked)."""
    with open(_CSV_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            df = pd.read_csv(VERIFIED_CSV)
            for col in ("norm_cq_code_path", "norm_iou", "sft_ready"):
                if col not in df.columns:
                    df[col] = ""
            df["sft_ready"] = df["sft_ready"].astype(object)
            df.at[orig_idx, "norm_cq_code_path"] = norm_cq_path
            df.at[orig_idx, "norm_iou"] = round(norm_iou, 4)
            gt_norm = str(df.at[orig_idx, "gt_norm_step_path"] or "")
            df.at[orig_idx, "sft_ready"] = "true" if (gt_norm and norm_cq_path and norm_iou >= 0.99) else "false"
            df.to_csv(VERIFIED_CSV, index=False)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def process_one(orig_idx: int, r: pd.Series, validate: bool, repair_iou: bool = False) -> dict:
    stem     = str(r["stem"])
    gt_step  = str(r.get("gt_step_path") or r.get("raw_step_path") or "")
    cq_path  = str(r.get("cq_code_path") or "")
    run      = str(r.get("pipeline_run") or r.get("source") or "unknown")

    if not gt_step or not (ROOT / gt_step).is_file():
        return {"stem": stem, "status": "skip_no_gt_step"}

    gt_step_abs = str(ROOT / gt_step)

    # repair_iou mode: cq_norm.py already exists, skip normalization step
    if repair_iou:
        existing = str(r.get("norm_cq_code_path") or "")
        if not existing or not (ROOT / existing).is_file():
            return {"stem": stem, "status": "skip_no_norm_py"}
        norm_py = ROOT / existing
        rel = existing
    else:
        if not cq_path or not (ROOT / cq_path).is_file():
            return {"stem": stem, "status": "skip_no_cq"}
        cq_abs = str(ROOT / cq_path)
        norm_py = _norm_output_path(stem, run)
        norm_py.parent.mkdir(parents=True, exist_ok=True)
        try:
            from normalize_cq_code import normalize_cq_file
            normalize_cq_file(cq_abs, gt_step_abs, str(norm_py))
        except Exception as e:
            return {"stem": stem, "status": "norm_failed", "error": str(e)[:200]}
        rel = str(norm_py.relative_to(ROOT))

    if not validate:
        _write_one(orig_idx, rel, 0.0)
        return {"stem": stem, "status": "ok_no_validate", "norm_cq_code_path": rel}

    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
        out_step = f.name
    try:
        ok, err = _run_py(str(norm_py), out_step)
        if not ok:
            return {"stem": stem, "status": "exec_failed", "error": err}

        iou = _iou_normalized(gt_step_abs, out_step)
        if iou >= 0.99:
            _write_one(orig_idx, rel, iou)
            return {"stem": stem, "status": "ok", "iou": round(iou, 4),
                    "norm_cq_code_path": rel}
        else:
            if repair_iou:
                # Update CSV: write actual iou so sft_ready becomes "false"
                _write_one(orig_idx, rel, iou)
            else:
                norm_py.unlink(missing_ok=True)
            return {"stem": stem, "status": "low_iou", "iou": round(iou, 4)}
    except Exception as e:
        return {"stem": stem, "status": "validate_error", "error": str(e)[:200]}
    finally:
        if os.path.exists(out_step):
            os.unlink(out_step)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit",        type=int, default=0)
    ap.add_argument("--offset",       type=int, default=0)
    ap.add_argument("--validate",     action="store_true",
                    help="Execute norm .py and check IoU ≥ 0.95")
    ap.add_argument("--missing-only", action="store_true",
                    help="Skip stems that already have norm_cq_code_path")
    ap.add_argument("--repair-iou",   action="store_true",
                    help="Re-validate stems with norm_cq_code_path filled but norm_iou missing")
    args = ap.parse_args()

    df   = pd.read_csv(VERIFIED_CSV)
    rows = df.copy()

    if args.repair_iou:
        # Re-validate all stems that have norm_cq_code_path (recompute norm_iou)
        has_path = rows["norm_cq_code_path"].notna() & (rows["norm_cq_code_path"] != "")
        rows = rows[has_path]
        args.validate = True  # always validate in repair mode
    elif args.missing_only and "norm_cq_code_path" in df.columns:
        rows = rows[rows["norm_cq_code_path"].isna() | (rows["norm_cq_code_path"] == "")]

    if args.offset:
        rows = rows.iloc[args.offset:]
    if args.limit:
        rows = rows.iloc[:args.limit]

    total = len(rows)
    mode = "repair-iou" if args.repair_iou else f"validate={args.validate}"
    print(f"Processing {total} stems ({mode})")

    stats = {"ok": 0, "ok_no_validate": 0, "skip": 0, "fail": 0, "low_iou": 0}

    for i, (orig_idx, r) in enumerate(rows.iterrows(), 1):
        result = process_one(orig_idx, r, args.validate, repair_iou=args.repair_iou)
        status = result["status"]

        if status.startswith("skip"):
            stats["skip"] += 1
        elif status in ("norm_failed", "exec_failed", "validate_error"):
            stats["fail"] += 1
            print(f"  [{i}/{total}] FAIL {result['stem']}: {status} — {result.get('error','')[:120]}")
        elif status == "low_iou":
            stats["low_iou"] += 1
            print(f"  [{i}/{total}] LOW_IoU {result['stem']}: {result.get('iou','?')}")
        elif status == "ok":
            stats["ok"] += 1
        elif status == "ok_no_validate":
            stats["ok_no_validate"] += 1

        if i % 100 == 0:
            print(f"[{i}/{total}] ok={stats['ok']+stats['ok_no_validate']} "
                  f"fail={stats['fail']} skip={stats['skip']} low_iou={stats['low_iou']}")

    print(f"\nDone: {stats}")


if __name__ == "__main__":
    main()
