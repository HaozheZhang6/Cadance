"""Score a CAD edit benchmark run.

Reads the run's results.jsonl and pairs' orig/gt STEP (local path or HF bytes),
computes:
  - iou_orig_gt   : baseline similarity (how close is orig to gt already)
  - iou_gen_gt    : final similarity after edit
  - norm_improve  : clip((iou_gen_gt - iou_orig_gt) / (1 - iou_orig_gt), 0, 1)
                    0 = no improvement (or made it worse), 1 = perfect match

When iou_orig_gt > 0.99 the pair is degenerate (matches
filter_iou_degenerate.py threshold); skip from norm_improve aggregation if so.

Usage (zero-setup, read STEP bytes from HF):
    python -m bench.edit_gen.score_edit --model gpt-4o

Usage (local bench-dir):
    python -m bench.edit_gen.score_edit --model gpt-4o --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import mean

from bench.metrics import compute_iou

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCH = ROOT / "data" / "data_generation" / "bench_edit"
DEGEN_THRESH = 0.99


def _write_step_bytes(buf: bytes, tmpdir: Path, name: str) -> Path:
    p = tmpdir / f"{name}.step"
    p.write_bytes(buf)
    return p


def score(
    bench_dir: Path | None,
    model: str,
    hf_repo: str | None = None,
    hf_split: str = "test",
    run_root: Path | None = None,
) -> dict:
    tmpdir_ctx: tempfile.TemporaryDirectory | None = None
    if hf_repo:
        from bench.dataloader import load_hf

        rows = load_hf(hf_repo, hf_split)
        tmpdir_ctx = tempfile.TemporaryDirectory()
        tmpdir = Path(tmpdir_ctx.name)
        pairs: dict = {}
        for r in rows:
            rid = r["record_id"]
            gt_path = _write_step_bytes(r["gt_step"], tmpdir, f"{rid}_gt")
            pairs[rid] = {**r, "_gt_step_abs": str(gt_path)}
        run_base = run_root or (ROOT / "results" / "edit_code")
    else:
        assert bench_dir is not None
        pairs = {
            r["record_id"]: r
            for r in (
                json.loads(ln)
                for ln in (bench_dir / "pairs.jsonl").read_text().splitlines()
                if ln
            )
        }
        run_base = run_root or (ROOT / "results" / "edit_code")
    run_dir = run_base / model.replace(":", "_").replace("/", "_")
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"no run results at {results_path}")

    results = [json.loads(ln) for ln in results_path.read_text().splitlines() if ln]
    gen_step_dir = run_dir / "steps"
    scored_path = run_dir / "scored.jsonl"
    fh = scored_path.open("w")

    # Prefer cached `iou_orig_gt` written by filter_iou_degenerate into
    # pairs.jsonl; fall back to recomputing for older datasets.
    orig_iou_cache: dict[tuple, tuple[float, str | None]] = {}

    def _orig_iou(pair: dict) -> tuple[float, str | None]:
        if "iou_orig_gt" in pair:
            return float(pair["iou_orig_gt"]), None
        if "iou" in pair:
            return float(pair["iou"]), None
        k = (pair["family"], pair["difficulty"], pair.get("axis",""), pair.get("pct_delta",0))
        if k not in orig_iou_cache:
            if hf_repo:
                orig_path = _write_step_bytes(
                    pair["orig_step"],
                    Path(tmpdir_ctx.name),
                    f"{pair['record_id']}_orig",
                )
                orig_iou_cache[k] = compute_iou(str(orig_path), pair["_gt_step_abs"])
            else:
                orig_iou_cache[k] = compute_iou(
                    str(bench_dir / pair["orig_step_path"]),
                    str(bench_dir / pair["gt_step_path"]),
                )
        return orig_iou_cache[k]

    def _gt_step(pair: dict) -> str:
        return (
            pair["_gt_step_abs"] if hf_repo else str(bench_dir / pair["gt_step_path"])
        )

    per_level: dict[str, list[float]] = defaultdict(list)
    per_difficulty: dict[str, list[float]] = defaultdict(list)
    per_family: dict[str, list[float]] = defaultdict(list)
    exec_rate_by_level: dict[str, list[int]] = defaultdict(list)
    gen_ious: list[float] = []
    all_norm: list[float] = []
    degen_skipped = 0
    n_exec_ok = 0
    n_total = len(results)

    for res in results:
        rid = res["record_id"]
        pair = pairs.get(rid)
        if not pair:
            continue
        level = res.get("level", res.get("edit_type", "n/a"))
        exec_rate_by_level[level].append(1 if res["exec_ok"] else 0)

        row: dict = {
            "record_id": rid,
            "family": res["family"],
            "difficulty": res["difficulty"],
            "level": level,
            "exec_ok": res["exec_ok"],
        }

        if not res["exec_ok"]:
            # Failed to exec → counted as norm_improve = 0 (no improvement)
            row.update({"iou_gen_gt": None, "iou_orig_gt": None, "norm_improve": 0.0})
            fh.write(json.dumps(row) + "\n")
            per_level[level].append(0.0)
            per_difficulty[res["difficulty"]].append(0.0)
            per_family[res["family"]].append(0.0)
            all_norm.append(0.0)
            continue

        n_exec_ok += 1
        gen_step = gen_step_dir / f"{rid}.step"
        iou_og, _ = _orig_iou(pair)
        iou_gg, iou_err = compute_iou(_gt_step(pair), str(gen_step))
        gen_ious.append(iou_gg)

        if iou_og > DEGEN_THRESH:
            degen_skipped += 1
            row.update(
                {
                    "iou_orig_gt": round(iou_og, 4),
                    "iou_gen_gt": round(iou_gg, 4),
                    "norm_improve": None,
                    "note": "degenerate (orig ~= gt)",
                }
            )
            fh.write(json.dumps(row) + "\n")
            continue

        norm = max(0.0, min(1.0, (iou_gg - iou_og) / (1.0 - iou_og)))
        row.update(
            {
                "iou_orig_gt": round(iou_og, 4),
                "iou_gen_gt": round(iou_gg, 4),
                "norm_improve": round(norm, 4),
                "iou_err": iou_err,
            }
        )
        fh.write(json.dumps(row) + "\n")

        per_level[level].append(norm)
        per_difficulty[res["difficulty"]].append(norm)
        per_family[res["family"]].append(norm)
        all_norm.append(norm)

    fh.close()

    summary = {
        "model": model,
        "n_total": n_total,
        "exec_rate": round(n_exec_ok / max(n_total, 1), 4),
        "norm_improve_mean": round(mean(all_norm), 4) if all_norm else None,
        "gen_iou_mean": round(mean(gen_ious), 4) if gen_ious else None,
        "degenerate_skipped": degen_skipped,
        "per_level": {
            lv: {
                "n": len(v),
                "norm_improve_mean": round(mean(v), 4) if v else None,
                "exec_rate": round(
                    sum(exec_rate_by_level[lv]) / max(len(exec_rate_by_level[lv]), 1),
                    4,
                ),
            }
            for lv, v in per_level.items()
        },
        "per_difficulty": {
            d: {"n": len(v), "norm_improve_mean": round(mean(v), 4) if v else None}
            for d, v in per_difficulty.items()
        },
        "per_family": {
            fam: {"n": len(v), "norm_improve_mean": round(mean(v), 4) if v else None}
            for fam, v in per_family.items()
        },
    }
    (run_dir / "score_summary.json").write_text(json.dumps(summary, indent=2))
    # Trim per_family for stdout
    terse = {k: v for k, v in summary.items() if k != "per_family"}
    print(json.dumps(terse, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hf-repo",
        type=str,
        default="BenchCAD/cad_bench_edit",
        help="HF dataset repo (default). Set empty to use --bench-dir.",
    )
    ap.add_argument("--split", type=str, default="test")
    ap.add_argument("--bench-dir", type=str, default="")
    ap.add_argument("--model", type=str, default="gpt-4o")
    ap.add_argument(
        "--run-root",
        type=str,
        default="",
        help="Directory containing <model>/results.jsonl (default matches run_edit_code.py)",
    )
    args = ap.parse_args()
    bench_dir = Path(args.bench_dir) if args.bench_dir else None
    hf_repo = args.hf_repo if not bench_dir else None
    run_root = Path(args.run_root) if args.run_root else None
    score(
        bench_dir,
        args.model,
        hf_repo=hf_repo,
        hf_split=args.split,
        run_root=run_root,
    )


if __name__ == "__main__":
    main()
