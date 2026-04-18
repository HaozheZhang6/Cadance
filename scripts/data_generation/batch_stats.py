"""
Per-batch statistics for codex_validation checkpoint files.

Computes: n_total, n_done, exec_fail, IoU=0 rate, geom_fail rate,
pass rate, mean_iou_all, mean_iou_passed.

Usage:
    uv run python3 scripts/data_generation/batch_stats.py
    uv run python3 scripts/data_generation/batch_stats.py --pool run_v4_n1000_openai \
        --verified-pairs data/data_generation/verified/verified_pairs.jsonl
"""

import argparse
import glob
from pathlib import Path

import pandas as pd


def batch_summary(ckpt_path: str) -> dict:
    df = pd.read_json(ckpt_path, lines=True)
    if "iou" not in df.columns:
        return {}
    n_total = len(df)
    done = df[df["stage"] == "done"] if "stage" in df.columns else df
    n_done = len(done)
    n_codegen = n_total - n_done

    n_iou0 = int((done["iou"] == 0).sum())
    n_geom = int(((done["iou"] > 0) & (done["iou"] < 0.99)).sum())
    n_pass = int((done["iou"] >= 0.99).sum())

    providers = done["provider"].value_counts().to_dict() if "provider" in done.columns else {}

    return {
        "run": ckpt_path.split("/")[3],
        "n_total": n_total,
        "n_done": n_done,
        "n_codegen_fail": n_codegen,
        "n_iou0": n_iou0,
        "n_geom_fail": n_geom,
        "n_pass": n_pass,
        "exec_fail_pct": f"{n_codegen/n_total:.1%}",
        "iou0_pct": f"{n_iou0/n_total:.1%}",
        "geom_fail_pct": f"{n_geom/n_total:.1%}",
        "pass_pct": f"{n_pass/n_total:.1%}",
        "mean_iou_done": f"{done['iou'].mean():.4f}" if n_done else "—",
        "mean_iou_passed": f"{done[done['iou']>=0.99]['iou'].mean():.6f}" if n_pass else "—",
        "providers": str(providers),
    }


def pool_comparison(pool_ckpt: str, vp_path: str) -> None:
    """B0/B1/B2 breakdown on a fixed pool from a single-provider checkpoint."""
    pool = pd.read_json(pool_ckpt, lines=True)
    done = pool[pool["stage"] == "done"] if "stage" in pool.columns else pool
    done = done.set_index("stem")

    vp = pd.read_json(vp_path, lines=True)
    vp["base_stem"] = vp["stem"].str.replace("_claude_fixed", "", regex=False)
    vp_pool = vp[vp["base_stem"].isin(set(done.index))]
    vp_auto = vp_pool[vp_pool["source"] != "claude_manual_fix"]

    n = len(done)
    b0_pass = int((done["iou"] >= 0.99).sum())
    b1_pass = len(vp_auto)
    b2_pass = len(vp_pool)
    manual = len(vp_pool) - len(vp_auto)

    print(f"\n=== Pool comparison (n={n} done stems) ===")
    print(f"{'Method':<20} {'Pass':>6} {'Pass%':>7} {'Mean IoU (all)':>15}")
    # B0
    mean_b0 = done["iou"].mean()
    print(f"{'B0 Direct':<20} {b0_pass:>6} {b0_pass/n:>7.1%} {mean_b0:>15.4f}")
    # B1: for each stem, best of done_iou or auto-vp
    iou_b1 = []
    iou_b2 = []
    for stem in done.index:
        b0_iou = float(done.loc[stem, "iou"])
        a = vp_auto[vp_auto["base_stem"] == stem]
        b = vp_pool[vp_pool["base_stem"] == stem]
        iou_b1.append(float(a["iou"].max()) if len(a) else b0_iou)
        iou_b2.append(float(b["iou"].max()) if len(b) else b0_iou)
    import numpy as np  # noqa: PLC0415
    mean_b1 = float(np.mean(iou_b1))
    mean_b2 = float(np.mean(iou_b2))
    print(f"{'B1 Re-Act (auto)':<20} {b1_pass:>6} {b1_pass/n:>7.1%} {mean_b1:>15.4f}")
    print(f"{'B2 CADLoop (ours)':<20} {b2_pass:>6} {b2_pass/n:>7.1%} {mean_b2:>15.4f}")
    print(f"\nManual cases: {manual} ({manual/b2_pass:.1%} of B2 accepted)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default=None, help="Run name to use for B0/B1/B2 pool comparison")
    parser.add_argument(
        "--verified-pairs",
        default="data/data_generation/verified/verified_pairs.jsonl",
    )
    args = parser.parse_args()

    # All batch summaries
    rows = []
    for ckpt in sorted(glob.glob("data/data_generation/codex_validation/**/*.jsonl", recursive=True)):
        if "checkpoint" not in ckpt:
            continue
        row = batch_summary(ckpt)
        if row:
            rows.append(row)

    df = pd.DataFrame(rows)
    if len(df):
        cols = ["run", "n_total", "n_done", "exec_fail_pct", "iou0_pct", "geom_fail_pct", "pass_pct", "mean_iou_done", "mean_iou_passed"]
        print(df[cols].to_string(index=False))

    # Pool comparison
    if args.pool:
        pool_ckpts = glob.glob(f"data/data_generation/codex_validation/{args.pool}/**/*.jsonl", recursive=True)
        pool_ckpts = [p for p in pool_ckpts if "checkpoint" in p]
        if pool_ckpts:
            pool_comparison(pool_ckpts[0], args.verified_pairs)
        else:
            print(f"No checkpoint found for {args.pool}")


if __name__ == "__main__":
    main()
