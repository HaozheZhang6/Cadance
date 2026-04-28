"""Random-stem IoU24 baseline: pair each target with another model gen."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bench.eval import exec_cq  # noqa: E402
from bench.metrics import compute_iou, compute_rotation_invariant_iou  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-results", required=True)
    ap.add_argument("--n-targets", type=int, default=30)
    ap.add_argument("--pairs-per-target", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-orientations", type=int, default=24, help="6 or 24")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.model_results).read_text().splitlines()
        if line.strip()
    ][-args.n_targets :]

    print(f"Loaded {len(rows)} rows from {args.model_results}")
    rng = random.Random(args.seed)

    # exec gt + gen STEP per stem (cache)
    print("Executing gt codes ...")
    from datasets import load_dataset

    ds = load_dataset("BenchCAD/cad_bench", split="test").to_pandas()
    gt_lookup = {r["stem"]: r["gt_code"] for _, r in ds.iterrows()}

    gt_steps: dict[str, str] = {}
    gen_steps: dict[str, str] = {}
    for r in rows:
        stem = r["stem"]
        gt_code = gt_lookup.get(stem)
        if not gt_code:
            print(f"  miss gt {stem}")
            continue
        p, e = exec_cq(gt_code)
        if p:
            gt_steps[stem] = p
            print(f"  gt OK {stem}", flush=True)
        else:
            print(f"  gt fail {stem}: {(e or '')[:100]}", flush=True)

    print(f"  gt OK: {len(gt_steps)}/{len(rows)}")

    # exec gen codes (only those exec_ok originally)
    print("Re-executing gen codes ...")
    for r in rows:
        if not r.get("exec_ok"):
            continue
        stem = r["stem"]
        p, e = exec_cq(r["gen_code"])
        if p:
            gen_steps[stem] = p
            print(f"  gen OK {stem}", flush=True)
    print(f"  gen OK: {len(gen_steps)}", flush=True)

    # build pair table
    valid_targets = [s for s in gt_steps if s in {r["stem"] for r in rows}]
    valid_gens = list(gen_steps.keys())

    print(
        f"Computing baseline IoU24: {len(valid_targets)} targets × {args.pairs_per_target} random gens each"
    )
    out = []
    for tgt in valid_targets:
        candidates = [g for g in valid_gens if g != tgt]
        if not candidates:
            continue
        picked = rng.sample(candidates, min(args.pairs_per_target, len(candidates)))
        for src in picked:
            iou, _ = compute_iou(gt_steps[tgt], gen_steps[src])
            iou_rot, idx, _ = compute_rotation_invariant_iou(
                gt_steps[tgt], gen_steps[src], n_orientations=args.n_orientations
            )
            row = {"target": tgt, "source": src, "iou": iou, "iou_rot": iou_rot}
            out.append(row)
            print(
                f"  tgt={tgt[:40]:40s} <- src={src[:40]:40s}  iou={iou:.3f}  iou_rot{args.n_orientations}={iou_rot:.3f}",
                flush=True,
            )

    iou_mean = sum(r["iou"] for r in out) / len(out) if out else 0.0
    iou_rot_mean = sum(r["iou_rot"] for r in out) / len(out) if out else 0.0
    print(
        f"\n=== baseline (cross-stem same-model) | n_pairs={len(out)} | n_rot={args.n_orientations} ===\n"
        f"  IoU       mean={iou_mean:.3f}\n"
        f"  IoU_rot   mean={iou_rot_mean:.3f}",
        flush=True,
    )

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {"pairs": out, "iou": iou_mean, "iou_rot": iou_rot_mean}, indent=2
            )
        )
        print(f"saved → {args.out}")


if __name__ == "__main__":
    main()
