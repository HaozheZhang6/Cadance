"""Score a CAD edit benchmark run.

Reads pairs.jsonl (paths to orig/gt STEP) and runs/<model>/results.jsonl, computes:
  - iou_orig_gt   : baseline similarity (how close is orig to gt already)
  - iou_gen_gt    : final similarity after edit
  - norm_improve  : clip((iou_gen_gt - iou_orig_gt) / (1 - iou_orig_gt), 0, 1)
                    0 = no improvement (or made it worse), 1 = perfect match

When iou_orig_gt > 0.99 the pair is degenerate (matches
filter_iou_degenerate.py threshold); skip from norm_improve aggregation if so.

Usage:
    python -m bench.edit_gen.score_edit --model gpt-4o
    python -m bench.edit_gen.score_edit --model gpt-4o --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from bench.metrics import compute_iou

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCH = ROOT / "data" / "data_generation" / "bench_edit"
DEGEN_THRESH = 0.99


def score(bench_dir: Path, model: str) -> dict:
    pairs = {
        r["record_id"]: r
        for r in (
            json.loads(ln)
            for ln in (bench_dir / "pairs.jsonl").read_text().splitlines()
            if ln
        )
    }
    run_dir = bench_dir / "runs" / model.replace(":", "_").replace("/", "_")
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"no run results at {results_path}")

    results = [json.loads(ln) for ln in results_path.read_text().splitlines() if ln]
    gen_step_dir = run_dir / "gen_step"
    scored_path = run_dir / "scored.jsonl"
    fh = scored_path.open("w")

    # Prefer cached `iou_orig_gt` written by filter_iou_degenerate into
    # pairs.jsonl; fall back to recomputing for older datasets.
    orig_iou_cache: dict[tuple, tuple[float, str | None]] = {}

    def _orig_iou(pair: dict) -> tuple[float, str | None]:
        if "iou_orig_gt" in pair:
            return float(pair["iou_orig_gt"]), None
        k = (pair["family"], pair["difficulty"], pair["axis"], pair["pct_delta"])
        if k not in orig_iou_cache:
            orig_iou_cache[k] = compute_iou(
                str(bench_dir / pair["orig_step_path"]),
                str(bench_dir / pair["gt_step_path"]),
            )
        return orig_iou_cache[k]

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
        level = res["level"]
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
        iou_gg, iou_err = compute_iou(
            str(bench_dir / pair["gt_step_path"]), str(gen_step)
        )
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
    ap.add_argument("--bench-dir", type=str, default=str(DEFAULT_BENCH))
    ap.add_argument("--model", type=str, default="gpt-4o")
    args = ap.parse_args()
    score(Path(args.bench_dir), args.model)


if __name__ == "__main__":
    main()
