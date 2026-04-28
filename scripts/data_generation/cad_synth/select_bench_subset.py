"""Select ~1200 stem subset from BenchCAD/cad_bench for benchmark eval.

Strategy: tiered per-family sampling × stratified by difficulty × furthest-point
sampling within (family, difficulty) cells for intra-cell diversity.

Tier weights (per family):
  HEAVY (rich parametric space): 25 — gears, sprockets, springs, impellers
  LIGHT (low parametric variety): 6 — washers, pins, keys, rivets
  STANDARD: 11 — everything else
  Tiny families (<weight available): take all

Within each (family, diff) cell:
  - Build feature vector: [bbox_x, bbox_y, bbox_z, n_ops, feature_count] (z-normalized)
  - Furthest-point sample to maximize spread

Output:
  data/data_generation/bench_subset_1200.json — list of stems + metadata
  data/data_generation/bench_subset_1200_report.txt — distribution stats

Usage:
  uv run python3 scripts/data_generation/cad_synth/select_bench_subset.py \
      --target 1200 --seed 42
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "data_generation"


HEAVY = {
    "spur_gear",
    "helical_gear",
    "bevel_gear",
    "sprocket",
    "double_simplex_sprocket",
    "worm_screw",
    "impeller",
    "propeller",
    "coil_spring",
    "torsion_spring",
    "bellows",
}
LIGHT = {
    "spacer_ring",
    "circlip",
    "dowel_pin",
    "taper_pin",
    "cotter_pin",
    "parallel_key",
    "rivet",
    "grommet",
    "washer",
}
W_HEAVY, W_STANDARD, W_LIGHT = 18, 9, 6  # plan A: /3 → per-diff 6/3/2

RARE_OP_TARGET = 25  # min count per op in subset; top-up if below

# Per-family overrides — weight + plane whitelist (None = all planes).
FAMILY_OVERRIDES: dict[str, dict] = {
    "ball_knob": {"weight": 9},
    "battery_holder": {"planes": ["XY"]},
}


def family_weight(fam: str) -> int:
    if fam in FAMILY_OVERRIDES and "weight" in FAMILY_OVERRIDES[fam]:
        return FAMILY_OVERRIDES[fam]["weight"]
    if fam in HEAVY:
        return W_HEAVY
    if fam in LIGHT:
        return W_LIGHT
    return W_STANDARD


def family_plane_filter(fam: str) -> set | None:
    p = FAMILY_OVERRIDES.get(fam, {}).get("planes")
    return set(p) if p else None


def furthest_point_sample(feats: np.ndarray, k: int, rng: np.random.Generator) -> list:
    """Pick k indices spread maximally in feature space."""
    n = len(feats)
    if k >= n:
        return list(range(n))
    z = (feats - feats.mean(axis=0)) / (feats.std(axis=0) + 1e-9)
    chosen = [int(rng.integers(n))]
    dists = np.linalg.norm(z - z[chosen[0]], axis=1)
    while len(chosen) < k:
        nxt = int(np.argmax(dists))
        chosen.append(nxt)
        new_d = np.linalg.norm(z - z[nxt], axis=1)
        dists = np.minimum(dists, new_d)
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1200, help="approx total target")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(OUT / "bench_subset_1200.json"))
    ap.add_argument("--report", default=str(OUT / "bench_subset_1200_report.txt"))
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    print("Loading BenchCAD/cad_bench ...")
    from datasets import load_dataset

    ds = load_dataset("BenchCAD/cad_bench", split="test")
    print(f"  {len(ds)} rows, {len(set(ds['family']))} families")

    # Index by family + difficulty.
    by_cell: dict[tuple, list[int]] = defaultdict(list)
    for i, r in enumerate(ds):
        by_cell[(r["family"], r["difficulty"])].append(i)

    families = sorted({k[0] for k in by_cell})
    chosen_idx = []
    fam_taken = Counter()
    rationale = {}

    def _fps_pick(cell_indices: list, k: int) -> list:
        """Furthest-point sample k indices from cell_indices."""
        if k >= len(cell_indices):
            return list(cell_indices)
        feats = []
        for ci in cell_indices:
            r = ds[ci]
            feats.append(
                [
                    len(json.loads(r.get("ops_used", "[]") or "[]")),
                    int(r.get("feature_count", 0) or 0),
                    hash(r["stem"]) % 100,
                ]
            )
        feats = np.array(feats, dtype=np.float64)
        picks = furthest_point_sample(feats, k, rng)
        return [cell_indices[p] for p in picks]

    for fam in families:
        target = family_weight(fam)
        per_diff = max(1, target // 3)  # ~equal split easy/medium/hard
        plane_whitelist = family_plane_filter(fam)
        for diff in ("easy", "medium", "hard"):
            cell = by_cell.get((fam, diff), [])
            if not cell:
                continue
            # Sub-stratify by base_plane so XY doesn't dominate.
            by_plane: dict[str, list[int]] = defaultdict(list)
            for ci in cell:
                p = ds[ci].get("base_plane", "XY")
                if plane_whitelist and p not in plane_whitelist:
                    continue
                by_plane[p].append(ci)
            planes = list(by_plane.keys())
            n_planes = len(planes)
            if n_planes == 0:
                continue
            # Distribute per_diff across planes; residual goes to largest plane.
            base_quota = per_diff // n_planes
            residual = per_diff - base_quota * n_planes
            planes_by_size = sorted(planes, key=lambda p: -len(by_plane[p]))

            picked_in_cell = 0
            picks_total = []
            for pl in planes_by_size:
                quota = base_quota + (1 if residual > 0 else 0)
                if residual > 0:
                    residual -= 1
                quota = min(quota, len(by_plane[pl]))
                if quota <= 0:
                    continue
                picks_total.extend(_fps_pick(by_plane[pl], quota))
                picked_in_cell += quota

            chosen_idx.extend(picks_total)
            fam_taken[fam] += picked_in_cell
            rationale[f"{fam}/{diff}"] = {
                "available": len(cell),
                "picked": picked_in_cell,
                "by_plane": {
                    pl: len([1 for ci in picks_total if ds[ci].get("base_plane") == pl])
                    for pl in planes
                },
            }

    # Rare-op top-up: any op with <RARE_OP_TARGET in subset → pull more samples
    # from unselected pool that contain that op (max +per-op cap so it doesn't
    # explode the total). Caps each op at RARE_OP_TARGET.
    chosen_set = set(chosen_idx)
    op_counter = Counter()
    for i in chosen_idx:
        for op in json.loads(ds[i].get("ops_used", "[]") or "[]"):
            op_counter[op] += 1

    # Index unselected by op for fast lookup.
    op_to_idx: dict[str, list[int]] = defaultdict(list)
    for i in range(len(ds)):
        if i in chosen_set:
            continue
        for op in json.loads(ds[i].get("ops_used", "[]") or "[]"):
            op_to_idx[op].append(i)

    # Per-family extra cap: don't let topup blow one family >MAX_TOPUP_PER_FAM.
    MAX_TOPUP_PER_FAM = 6
    fam_extra = Counter()
    topup = []
    for op, cnt in sorted(op_counter.items(), key=lambda x: x[1]):
        if cnt >= RARE_OP_TARGET:
            continue
        need = RARE_OP_TARGET - cnt
        candidates = [i for i in op_to_idx.get(op, []) if i not in chosen_set]
        if not candidates:
            continue
        rng.shuffle(candidates)
        for ci in candidates:
            fam = ds[ci]["family"]
            # Explicit-weight families are capped at their declared weight —
            # topup never exceeds it (e.g. ball_knob hard-capped at 9).
            if fam in FAMILY_OVERRIDES and "weight" in FAMILY_OVERRIDES[fam]:
                continue
            if fam_extra[fam] >= MAX_TOPUP_PER_FAM:
                continue
            chosen_set.add(ci)
            topup.append(ci)
            fam_extra[fam] += 1
            op_counter[op] += 1
            for o in json.loads(ds[ci].get("ops_used", "[]") or "[]"):
                if o != op:
                    op_counter[o] += 1
            if op_counter[op] >= RARE_OP_TARGET:
                break

    chosen_idx.extend(topup)
    print(f"  rare-op top-up added {len(topup)} samples")

    # Output.
    chosen_stems = [ds[i]["stem"] for i in chosen_idx]
    chosen_families = Counter(ds[i]["family"] for i in chosen_idx)
    chosen_diffs = Counter(ds[i]["difficulty"] for i in chosen_idx)

    # Op coverage check.
    op_counter = Counter()
    for i in chosen_idx:
        for op in json.loads(ds[i].get("ops_used", "[]") or "[]"):
            op_counter[op] += 1

    Path(args.out).write_text(
        json.dumps(
            {
                "target": args.target,
                "actual": len(chosen_idx),
                "seed": args.seed,
                "tier_weights": {
                    "HEAVY": W_HEAVY,
                    "STANDARD": W_STANDARD,
                    "LIGHT": W_LIGHT,
                },
                "heavy_families": sorted(HEAVY),
                "light_families": sorted(LIGHT),
                "stems": chosen_stems,
                "by_family": dict(chosen_families.most_common()),
                "by_difficulty": dict(chosen_diffs),
                "op_coverage": dict(op_counter.most_common()),
                "rationale": rationale,
            },
            indent=2,
            default=str,
        )
    )

    # Report.
    lines = [
        f"BenchCAD subset selection — target={args.target}, actual={len(chosen_idx)}",
        f"seed={args.seed}",
        f"\n=== By family ({len(chosen_families)} families) ===",
    ]
    for f, c in chosen_families.most_common():
        tier = "HEAVY" if f in HEAVY else ("LIGHT" if f in LIGHT else "STD")
        lines.append(f"  [{tier:5s}] {f:32s} {c}")
    lines.append("\n=== By difficulty ===")
    for d, c in chosen_diffs.most_common():
        lines.append(f"  {d:8s} {c}")
    lines.append(f"\n=== Op coverage (top 30 of {len(op_counter)}) ===")
    for op, c in op_counter.most_common(30):
        lines.append(f"  {op:25s} {c}")
    rare_ops = [(op, c) for op, c in op_counter.items() if c < 30]
    if rare_ops:
        lines.append("\n=== Rare ops (<30 in subset) ===")
        for op, c in sorted(rare_ops, key=lambda x: x[1]):
            lines.append(f"  {op:25s} {c}")
    Path(args.report).write_text("\n".join(lines))

    print(f"\n✓ Selected {len(chosen_idx)} stems")
    print(
        f"  by family: {len(chosen_families)} families, top 3: {chosen_families.most_common(3)}"
    )
    print(f"  by diff: {dict(chosen_diffs)}")
    print(f"  op coverage: {len(op_counter)} unique ops")
    print(f"  output: {args.out}")
    print(f"  report: {args.report}")


if __name__ == "__main__":
    sys.exit(main() or 0)
