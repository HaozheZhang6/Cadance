"""
Compute Chamfer Distance (CD) between GT and generated STEP files.

Usage:
    uv run python3 scripts/data_generation/compute_cd.py \
        --pool-checkpoint data/data_generation/codex_validation/run_v4_n1000_openai/run_v4_n1000_openai/checkpoint.jsonl \
        --verified-pairs data/data_generation/verified/verified_pairs.jsonl \
        --gen-dir data/data_generation/codex_validation/run_v4_n1000_openai/run_v4_n1000_openai/generated_step \
        --sample 300 \
        --output /tmp/cd_results.csv

For each stem in the pool: computes CD for B0 (raw gen) and B2 (best verified).
If a stem is not in verified_pairs, B2 falls back to B0 gen.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW_GT_PATTERNS = [
    "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction/{stem}.step",
    "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools/{stem}_*.step",
]


def find_gt(stem: str) -> str | None:
    for pat in RAW_GT_PATTERNS:
        p = pat.format(stem=stem)
        if "*" in p:
            ms = list(Path(".").glob(p.lstrip("/")))
            if ms:
                return str(ms[0])
        elif Path(p).exists():
            return p
    return None


def pts_from_step(path: str | Path, n: int = 2048) -> np.ndarray | None:
    try:
        import cadquery as cq  # noqa: PLC0415

        s = cq.importers.importStep(str(path)).val()
        if s.Volume() <= 0:
            return None
        pts = np.array([[v.x, v.y, v.z] for v in s.tessellate(0.1)[0]])
        if len(pts) < 3:
            return None
        idx = np.random.choice(len(pts), min(n, len(pts)), replace=False)
        return pts[idx]
    except Exception:
        return None


def chamfer_distance(a: np.ndarray, b: np.ndarray) -> float | None:
    if a is None or b is None:
        return None
    from scipy.spatial import cKDTree  # noqa: PLC0415

    t1, t2 = cKDTree(a), cKDTree(b)
    return float((t2.query(a)[0].mean() + t1.query(b)[0].mean()) / 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool-checkpoint", required=True)
    parser.add_argument("--verified-pairs", required=True)
    parser.add_argument("--gen-dir", required=True)
    parser.add_argument("--sample", type=int, default=300)
    parser.add_argument("--output", default="/tmp/cd_results.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    np.random.seed(args.seed)

    pool = pd.read_json(args.pool_checkpoint, lines=True)
    done = pool[pool["stage"] == "done"] if "stage" in pool.columns else pool
    vp = pd.read_json(args.verified_pairs, lines=True)
    vp["base_stem"] = vp["stem"].str.replace("_claude_fixed", "", regex=False)
    gen_dir = Path(args.gen_dir)

    sample = done.sample(min(args.sample, len(done)), random_state=args.seed)
    stems = sample["stem"].tolist()
    done_idx = done.set_index("stem")

    rows = []
    for i, stem in enumerate(stems):
        gt_path = find_gt(stem)
        b0_gen = gen_dir / f"{stem}.step"
        if not gt_path or not b0_gen.exists():
            continue

        vp_match = vp[vp["base_stem"] == stem]
        b2_gen_path = vp_match["gen_step_path"].iloc[0] if len(vp_match) > 0 else None

        gt_pts = pts_from_step(gt_path)
        b0_pts = pts_from_step(b0_gen)
        b2_pts = pts_from_step(b2_gen_path) if b2_gen_path else b0_pts

        b0_iou = float(done_idx.loc[stem, "iou"]) if stem in done_idx.index else 0.0
        b2_iou = float(vp_match["iou"].max()) if len(vp_match) > 0 else b0_iou

        rows.append(
            {
                "stem": stem,
                "b0_iou": b0_iou,
                "b2_iou": b2_iou,
                "b0_cd": chamfer_distance(gt_pts, b0_pts),
                "b2_cd": chamfer_distance(gt_pts, b2_pts),
                "in_vp": len(vp_match) > 0,
            }
        )
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(stems)}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.output, index=False)

    valid = df[df["b0_cd"].notna() & df["b2_cd"].notna()]
    acc = df[df["in_vp"]]
    print(f"\n=== CD Results (n={len(df)}, accepted={df['in_vp'].sum()}) ===")
    print(f"B0: mean_iou={df['b0_iou'].mean():.4f}, mean_cd={valid['b0_cd'].mean():.2f}mm")
    print(f"B2: mean_iou={df['b2_iou'].mean():.4f}, mean_cd={valid['b2_cd'].mean():.2f}mm")
    print(f"B0 CD on accepted: {acc['b0_cd'].mean():.2f}mm")
    print(f"B2 CD on accepted: {acc['b2_cd'].mean():.2f}mm")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
