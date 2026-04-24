"""MechEval staged test run (img → CadQuery code) with on-disk input cache.

Steps:
  1. fetch   — stream N HF samples → save composite.png + meta.json under bench/test/data/<stem>/
  2. render  — verify cached PNGs exist
  3. eval    — call VLM (via registry adapter) per cached sample, exec, score

Memory-safe: streams HF, never holds full dataset in RAM. Eval results land in
`results/img2cq_test/<model>/` (dedup by stem across runs).

Usage:
    python bench/test/run_test.py --model gpt-4o --limit 10
    python bench/test/run_test.py --step fetch --limit 50 --seed 42
    python bench/test/run_test.py --step eval --model gpt-4o
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / "data"
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")

sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


# ── Step 1: Fetch ─────────────────────────────────────────────────────────────


def step_fetch(
    repo: str,
    split: str,
    limit: int,
    token: str | None,
    seed: int = 0,
) -> list[Path]:
    """Sample (limit, seed) → save composite.png + meta.json. Returns meta paths."""
    from datasets import load_dataset

    from bench.sampling import sample_rows

    DATA.mkdir(parents=True, exist_ok=True)
    print(f"\n[1/3] FETCH  {repo}  split={split}  limit={limit}  seed={seed}")

    ds = load_dataset(repo, split=split, token=token)
    rows_meta = [{k: row[k] for k in ("stem", "family")} for row in ds]
    sampled = sample_rows(rows_meta, limit, seed)
    sampled_stems = [r["stem"] for r in sampled]
    stem_to_idx = {r["stem"]: i for i, r in enumerate(rows_meta)}

    saved, skipped = [], 0
    for stem in sampled_stems:
        sample_dir = DATA / stem
        meta_path = sample_dir / "meta.json"
        if meta_path.exists():
            saved.append(meta_path)
            skipped += 1
            continue
        sample_dir.mkdir(parents=True, exist_ok=True)
        row = ds[stem_to_idx[stem]]
        img = row["composite_png"]
        img.save(sample_dir / "composite.png")
        img.close()
        del img
        meta = {k: v for k, v in row.items() if k != "composite_png"}
        meta_path.write_text(json.dumps(meta, indent=2))
        saved.append(meta_path)
        print(f"  saved {stem}")

    print(f"  fetch done: {len(saved)} samples ({skipped} already cached)")
    return saved


# ── Step 2: Verify renders ────────────────────────────────────────────────────


def step_render(meta_paths: list[Path]) -> list[Path]:
    print(f"\n[2/3] RENDER  verify {len(meta_paths)} local images")
    ok = []
    for mp in meta_paths:
        img_path = mp.parent / "composite.png"
        if not img_path.exists():
            print(
                f"  MISSING {mp.parent.name}/composite.png — re-run with --step fetch"
            )
            sys.exit(1)
        ok.append(mp)
    print(f"  all {len(ok)} images present")
    return ok


# ── Step 3: Eval ──────────────────────────────────────────────────────────────

_PREAMBLE = """
import cadquery as cq
try:
    import OCP.TopoDS as _td
    for _cls in (_td.TopoDS_Shape, _td.TopoDS_Face, _td.TopoDS_Edge, _td.TopoDS_Vertex,
                 _td.TopoDS_Wire, _td.TopoDS_Shell, _td.TopoDS_Solid,
                 _td.TopoDS_Compound, _td.TopoDS_CompSolid):
        if not hasattr(_cls, 'HashCode'):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
except Exception:
    pass
show_object = lambda *a, **kw: None
"""
_SUFFIX = """
import sys as _sys
try:
    cq.exporters.export(result, _sys.argv[1])
except Exception as _e:
    raise RuntimeError(f"export failed: {_e}")
"""


def _exec_cq(code: str, timeout: int = 120) -> tuple[str | None, str | None]:
    lines = [
        ln
        for ln in code.splitlines()
        if ln.strip() not in ("import cadquery as cq", "import cadquery")
    ]
    script = _PREAMBLE + "\n".join(lines) + _SUFFIX
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
        out = f.name
    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    try:
        r = subprocess.run(
            [sys.executable, "-c", script, out],
            env=env,
            timeout=timeout,
            capture_output=True,
            cwd=tempfile.gettempdir(),
        )
        if r.returncode != 0:
            return None, r.stderr.decode(errors="replace")[-400:]
        if not Path(out).exists() or Path(out).stat().st_size < 100:
            return None, "step missing or empty"
        return out, None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)


def _call_vlm_disk(model: str, img_path: Path) -> tuple[str | None, str | None]:
    """Read image from disk, send to registry adapter."""
    from PIL import Image

    from bench.models import call_vlm

    img = Image.open(img_path)
    try:
        return call_vlm(model, img)
    finally:
        img.close()


def _render_step(step_path: str, out_png: Path) -> bool:
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
        from render_normalized_views import render_step_normalized

        paths = render_step_normalized(step_path, str(out_png.parent))
        src = Path(paths["composite"])
        if src != out_png:
            src.replace(out_png)
        return True
    except Exception:
        return False


def step_eval(
    meta_paths: list[Path],
    model: str,
    save_code: bool,
    save_render: bool,
    rot_invariant: int = 0,
) -> list[dict]:
    from bench.metrics import (
        compute_chamfer,
        compute_iou,
        compute_rotation_invariant_iou,
        extract_features,
        feature_f1,
    )
    from bench.results import ResultsDir

    rd = ResultsDir(task="img2cq_test", model=model)
    done = rd.done_keys("stem")
    todo = [mp for mp in meta_paths if mp.parent.name not in done]
    print(
        f"\n[3/3] EVAL  model={model}  total={len(meta_paths)}  done={len(done)}  todo={len(todo)}"
    )
    print(f"  Results dir: {rd.root}")

    results: list[dict] = []
    with rd:
        for i, mp in enumerate(todo):
            meta = json.loads(mp.read_text())
            stem = meta["stem"]
            img_path = mp.parent / "composite.png"
            gt_features = (
                json.loads(meta["feature_tags"])
                if isinstance(meta["feature_tags"], str)
                else meta["feature_tags"]
            )

            res = {
                "stem": stem,
                "family": meta["family"],
                "difficulty": meta["difficulty"],
                "base_plane": meta["base_plane"],
                "model": model,
                "exec_ok": 0,
                "iou": 0.0,
                "chamfer": float("inf"),
                "feature_f1": 0.0,
                "detail_score": 0.0,
                "gt_features": gt_features,
                "gen_features": {},
                "error": None,
            }

            t0 = time.time()
            gen_code, err = _call_vlm_disk(model, img_path)
            res["vlm_latency_s"] = round(time.time() - t0, 2)

            if not gen_code:
                res["error"] = f"vlm_fail: {err}"
                rd.append(res)
                results.append(res)
                print(f"  [{i + 1}/{len(todo)}] {stem}  VLM FAIL")
                continue

            if save_code:
                rd.save_code(stem, gen_code)

            gen_step, exec_err = _exec_cq(gen_code)
            gen_feats = extract_features(gen_code)
            res["gen_features"] = gen_feats
            res["feature_f1"] = round(feature_f1(gen_feats, gt_features), 4)

            if not gen_step:
                res["error"] = f"exec_fail: {exec_err}"
                res["detail_score"] = round(0.6 * res["feature_f1"], 4)
                rd.append(res)
                results.append(res)
                print(
                    f"  [{i + 1}/{len(todo)}] {stem}  EXEC FAIL  f1={res['feature_f1']:.3f}"
                )
                continue

            res["exec_ok"] = 1

            gt_step, gt_err = _exec_cq(meta["gt_code"])
            if not gt_step:
                res["error"] = f"gt_exec_fail: {gt_err}"
                res["detail_score"] = round(0.6 * res["feature_f1"], 4)
                Path(gen_step).unlink(missing_ok=True)
                rd.append(res)
                results.append(res)
                print(f"  [{i + 1}/{len(todo)}] {stem}  GT FAIL")
                continue

            iou, _ = compute_iou(gt_step, gen_step)
            cd, _ = compute_chamfer(gt_step, gen_step)
            res["iou"] = round(iou, 4)
            res["chamfer"] = round(cd, 6) if cd != float("inf") else float("inf")
            if rot_invariant in (6, 24):
                rot_iou, rot_idx, _ = compute_rotation_invariant_iou(
                    gt_step, gen_step, n_orientations=rot_invariant
                )
                res["iou_rot"] = round(rot_iou, 4)
                res["iou_rot_idx"] = rot_idx
                score_iou = max(iou, rot_iou)
            else:
                score_iou = iou
            res["detail_score"] = round(0.4 * score_iou + 0.6 * res["feature_f1"], 4)

            if save_render:
                render_dir = rd.renders / stem
                render_dir.mkdir(parents=True, exist_ok=True)
                _render_step(gen_step, render_dir / "gen_render.png")

            Path(gen_step).unlink(missing_ok=True)
            Path(gt_step).unlink(missing_ok=True)

            rd.append(res)
            results.append(res)
            print(
                f"  [{i + 1}/{len(todo)}] {stem}  "
                f"exec=1  iou={iou:.3f}  f1={res['feature_f1']:.3f}  "
                f"detail={res['detail_score']:.3f}"
            )

    # Return full pool for the summary
    with open(rd.results_path) as f:
        return [json.loads(line) for line in f if line.strip()]


# ── Summary ───────────────────────────────────────────────────────────────────


def print_summary(results: list[dict]) -> None:
    if not results:
        return
    total = len(results)
    exec_ok = [r for r in results if r["exec_ok"]]
    ious = [r["iou"] for r in exec_ok]
    f1s = [r["feature_f1"] for r in results]
    details = [r["detail_score"] for r in results]

    print(f"\n{'=' * 50}")
    print(f"  N={total}  model={results[0].get('model', '?')}")
    print(f"  Exec%   : {len(exec_ok) / total * 100:.1f}%")
    print(f"  IoU     : {sum(ious) / len(ious):.3f}" if ious else "  IoU     : —")
    print(f"  Feat-F1 : {sum(f1s) / len(f1s):.3f}")
    print(f"  Detail↑ : {sum(details) / len(details):.3f}")
    print(f"{'=' * 50}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="MechEval staged test run")
    ap.add_argument("--repo", default="BenchCAD/cad_bench")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--model", default=None, help="required for --step eval/all")
    ap.add_argument("--step", choices=["fetch", "render", "eval", "all"], default="all")
    ap.add_argument("--save-code", action="store_true")
    ap.add_argument("--save-render", action="store_true")
    ap.add_argument(
        "--rot-invariant",
        type=int,
        default=0,
        choices=[0, 6, 24],
        help="0=off, 6=face-up only, 24=full cube group",
    )
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )

    if args.step in ("eval", "all") and not args.model:
        sys.exit("--model required for eval/all step")

    if args.step in ("fetch", "all"):
        meta_paths = step_fetch(
            args.repo, args.split, args.limit, token, seed=args.seed
        )
    else:
        meta_paths = sorted(DATA.glob("*/meta.json"))[: args.limit]
        if not meta_paths:
            sys.exit("No local data found. Run with --step fetch first.")

    if args.step in ("render", "eval", "all"):
        meta_paths = step_render(meta_paths)

    if args.step in ("eval", "all"):
        results = step_eval(
            meta_paths,
            args.model,
            args.save_code,
            args.save_render,
            rot_invariant=args.rot_invariant,
        )
        print_summary(results)


if __name__ == "__main__":
    main()
