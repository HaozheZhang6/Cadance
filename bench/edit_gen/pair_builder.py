"""Generate CAD edit benchmark pairs.

Per family: 1 easy root + 1 hard root × 3 axes × 1 delta × 2 levels (L1/L2)
            ≈ 12 records/family × 106 ≈ 1272 records.
Delta strategy: small (2-5%) + pre-selected safe direction, per axis.
Output: pairs.jsonl, codes/<rid>_{orig,gt}.py, steps/<rid>_{orig,gt}.step,
        pair_stats.json.

Usage:
    python -m bench.edit_gen.pair_builder
    python -m bench.edit_gen.pair_builder --families pillow_block,hex_nut
    python -m bench.edit_gen.pair_builder --out data/data_generation/bench_edit
"""

import argparse
import json
import traceback
from collections import defaultdict
from pathlib import Path

import numpy as np

from bench.edit_gen.edit_axes import EDIT_AXES, check_axis_constraints
from scripts.data_generation.cad_synth.pipeline.builder import (
    build_from_program,
    render_program_to_code,
)
from scripts.data_generation.cad_synth.pipeline.registry import get_family

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "data_generation" / "bench_edit"
DIFFICULTIES = ["easy", "hard"]  # one root per difficulty
LEVELS = ["L1", "L2"]


def perturb_params(p0: dict, axis: dict) -> dict:
    """Apply pct delta to one param; return new dict."""
    p1 = dict(p0)
    v0 = p0[axis["param"]]
    pct = axis["pct"]
    v1 = v0 * (1 + pct / 100.0)
    # Round to 4 decimal places (user-specified precision for L1 instructions)
    p1[axis["param"]] = round(v1, 4)
    return p1


def render_and_build(fam, params: dict):
    """Return (code_text, wp) or (None, None) on failure."""
    try:
        prog = fam.make_program(params)
    except Exception:
        return None, None
    try:
        code = render_program_to_code(prog, include_params_hint=True)
    except Exception:
        return None, None
    try:
        wp = build_from_program(prog)
    except Exception:
        return None, None
    return code, wp


def bbox_vol(wp) -> float:
    try:
        bb = wp.val().BoundingBox()
        return max(bb.xlen, 1e-9) * max(bb.ylen, 1e-9) * max(bb.zlen, 1e-9)
    except Exception:
        return 0.0


def bbox_dims(wp) -> tuple[float, float, float]:
    try:
        bb = wp.val().BoundingBox()
        return bb.xlen, bb.ylen, bb.zlen
    except Exception:
        return 0.0, 0.0, 0.0


def sanity_ok(wp0, wp1, stats: dict) -> bool:
    """Post-build geometric sanity: GT must not collapse or explode vs orig."""
    v0 = bbox_vol(wp0)
    v1 = bbox_vol(wp1)
    if v1 < 1e-6:
        stats["sanity_fail_gt_empty"] += 1
        return False
    dims1 = bbox_dims(wp1)
    if min(dims1) < 0.05:  # ~degenerate
        stats["sanity_fail_degenerate"] += 1
        return False
    if v0 > 1e-6:
        ratio = v1 / v0
        if ratio < 0.3 or ratio > 3.0:
            stats["sanity_fail_volume_ratio"] += 1
            return False
    return True


def export_step(wp, path: Path):
    import cadquery as cq

    cq.exporters.export(wp, str(path), exportType=cq.exporters.ExportTypes.STEP)


def make_instructions(axis: dict, orig_value: float, target_value: float) -> dict:
    """Build L1 and L2 instruction text. 4-decimal precision per user spec."""
    pct = axis["pct"]
    sign = "+" if pct > 0 else ""
    unit = axis["unit"]
    human = axis["human"]
    # Trailing zeros stripped but keep up to 4 decimals.
    target_str = f"{target_value:.4f}".rstrip("0").rstrip(".")
    return {
        "L1": f"Set the {human} to {target_str} {unit}.",
        "L2": f"Change the {human} by {sign}{pct}%.",
    }


def build_pairs(
    families: list[str],
    out_dir: Path,
    seed: int = 42,
    render: bool = False,
) -> dict:
    """Main entry: generate pairs for given families, write files, return stats."""
    out_dir.mkdir(parents=True, exist_ok=True)
    codes_dir = out_dir / "codes"
    steps_dir = out_dir / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)
    pairs_path = out_dir / "pairs.jsonl"

    rng = np.random.default_rng(seed)
    stats = defaultdict(int)
    per_family_per_axis: dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    records = []
    # Incremental flush: write pairs and stats after each family so crashes
    # (e.g. OCCT C-level failures) don't lose prior progress.
    pairs_fh = pairs_path.open("w")
    stats_path = out_dir / "pair_stats.json"

    def _flush_all():
        pairs_fh.flush()
        stats_snapshot = {
            "total_records": len(records),
            "filter_counts": dict(stats),
            "per_family_per_axis": {
                fam: {k: dict(v) for k, v in axes.items()}
                for fam, axes in per_family_per_axis.items()
            },
        }
        stats_path.write_text(json.dumps(stats_snapshot, indent=2))

    for fam_name in families:
        if fam_name not in EDIT_AXES:
            stats["family_no_axes"] += 1
            continue
        try:
            fam = get_family(fam_name)
        except Exception as e:
            stats["family_load_fail"] += 1
            stats[f"_err_load_{fam_name}"] = str(e)[:120]
            continue
        axes = EDIT_AXES[fam_name]
        for diff in DIFFICULTIES:
            # Sample one root until validate_params passes (max 10 retries)
            p0 = None
            for _ in range(10):
                try:
                    candidate = fam.sample_params(diff, rng)
                except Exception:
                    continue
                if fam.validate_params(candidate):
                    p0 = candidate
                    break
            if p0 is None:
                stats["root_sample_fail"] += 1
                continue

            code0, wp0 = render_and_build(fam, p0)
            if code0 is None or wp0 is None:
                stats["root_build_fail"] += 1
                continue

            root_id = f"{fam_name}_{diff}_r0"
            orig_code_path = codes_dir / f"{root_id}_orig.py"
            orig_step_path = steps_dir / f"{root_id}_orig.step"
            orig_code_path.write_text(code0)
            try:
                export_step(wp0, orig_step_path)
            except Exception as e:
                stats["root_step_export_fail"] += 1
                stats[f"_err_root_step_{fam_name}"] = str(e)[:120]
                continue

            for axis in axes:
                key = axis["param"]
                per_family_per_axis[fam_name][key]["attempted"] += 1
                if key not in p0:
                    # param only present in some variants (e.g. bearing_retainer_cap
                    # disc vs ear); skip for this root
                    per_family_per_axis[fam_name][key]["skip_not_in_root"] += 1
                    stats["skip_axis_not_in_root"] += 1
                    continue
                p1 = perturb_params(p0, axis)
                if not fam.validate_params(p1):
                    per_family_per_axis[fam_name][key]["fail_validate"] += 1
                    stats["filter_validate_params"] += 1
                    continue
                if not check_axis_constraints(p1, axis):
                    per_family_per_axis[fam_name][key]["fail_constraint"] += 1
                    stats["filter_axis_constraint"] += 1
                    continue

                code1, wp1 = render_and_build(fam, p1)
                if code1 is None or wp1 is None:
                    per_family_per_axis[fam_name][key]["fail_build"] += 1
                    stats["filter_gt_build"] += 1
                    continue

                if not sanity_ok(wp0, wp1, stats):
                    per_family_per_axis[fam_name][key]["fail_sanity"] += 1
                    continue

                rid_stem = f"{fam_name}_{diff}_r0_{key}_pct{axis['pct']:+d}"
                gt_code_path = codes_dir / f"{rid_stem}_gt.py"
                gt_step_path = steps_dir / f"{rid_stem}_gt.step"
                gt_code_path.write_text(code1)
                try:
                    export_step(wp1, gt_step_path)
                except Exception:
                    per_family_per_axis[fam_name][key]["fail_step_export"] += 1
                    stats["filter_gt_step_export"] += 1
                    continue

                per_family_per_axis[fam_name][key]["ok"] += 1
                orig_value = p0[key]
                target_value = p1[key]
                instrs = make_instructions(axis, orig_value, target_value)
                for level in LEVELS:
                    rid = f"{rid_stem}_{level}"
                    rec = {
                        "record_id": rid,
                        "family": fam_name,
                        "difficulty": diff,
                        "axis": key,
                        "level": level,
                        "pct_delta": axis["pct"],
                        "orig_value": orig_value,
                        "target_value": target_value,
                        "unit": axis["unit"],
                        "human_name": axis["human"],
                        "instruction": instrs[level],
                        "original_code_path": str(orig_code_path.relative_to(out_dir)),
                        "gt_code_path": str(gt_code_path.relative_to(out_dir)),
                        "orig_step_path": str(orig_step_path.relative_to(out_dir)),
                        "gt_step_path": str(gt_step_path.relative_to(out_dir)),
                        "orig_params": p0,
                        "target_params": p1,
                    }
                    records.append(rec)
                    pairs_fh.write(json.dumps(rec) + "\n")
                    stats[f"emit_{level}"] += 1
        # Flush after each family completes
        _flush_all()

    pairs_fh.close()

    # Final pair_stats.json
    stats_out = {
        "total_records": len(records),
        "filter_counts": dict(stats),
        "per_family_per_axis": {
            fam: {k: dict(v) for k, v in axes.items()}
            for fam, axes in per_family_per_axis.items()
        },
    }
    (out_dir / "pair_stats.json").write_text(json.dumps(stats_out, indent=2))
    return stats_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--families",
        type=str,
        default=None,
        help="Comma-separated family subset; default = all in EDIT_AXES",
    )
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--exclude",
        type=str,
        default=None,
        help="Comma-separated families to skip (applied after --families)",
    )
    args = ap.parse_args()
    if args.families:
        fams = [f.strip() for f in args.families.split(",") if f.strip()]
    else:
        fams = list(EDIT_AXES.keys())
    if args.exclude:
        excl = {f.strip() for f in args.exclude.split(",") if f.strip()}
        fams = [f for f in fams if f not in excl]
    out_dir = Path(args.out)
    try:
        stats = build_pairs(fams, out_dir, seed=args.seed)
        print(f"Wrote {stats['total_records']} records to {out_dir/'pairs.jsonl'}")
        print(f"Filter counts: {stats['filter_counts']}")
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
