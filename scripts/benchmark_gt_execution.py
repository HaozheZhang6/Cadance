#!/usr/bin/env python3
"""Fast benchmark: execute ground-truth CadQuery code from data/benchmark/ JSONs.

For each sample: executes generated_cadquery_code, saves STEP + 4 screenshots
(isometric, front, top, right_side), compares geometry to stored GT values.

Usage:
    uv run python scripts/benchmark_gt_execution.py
    uv run python scripts/benchmark_gt_execution.py --samples 10
    uv run python scripts/benchmark_gt_execution.py --samples 0   # all 100
    uv run python scripts/benchmark_gt_execution.py --out data/my_bench_run
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Project root on sys.path so src imports resolve
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _build_gateway():
    from src.tools.gateway import SubprocessCadQueryBackend, ToolGateway

    gateway = ToolGateway()
    backend = SubprocessCadQueryBackend()
    if not backend.is_available():
        print("[error] CadQuery subprocess backend not available.")
        print("        Run: cd tools/cadquery && uv sync")
        sys.exit(1)
    gateway.register("cadquery", backend)
    return gateway


def _geometry_diff(got: dict, want: dict) -> dict:
    """Return pct diffs for numeric keys present in both dicts."""
    diffs = {}
    for key in ("volume", "face_count", "edge_count", "vertex_count", "solid_count"):
        g = got.get(key)
        w = want.get(key)
        if g is None or w is None:
            continue
        if w == 0:
            diffs[key] = None
        else:
            diffs[key] = round(abs(g - w) / abs(w) * 100, 2)
    return diffs


def _render_views(step_path: Path, output_dir: Path, gateway) -> dict[str, Path]:
    """Render 4 standard views. Returns {view_name: png_path}."""
    from src.cad.intent_decomposition.utils.visualization import (
        render_step_to_images_with_fallback,
    )

    return render_step_to_images_with_fallback(
        step_path=step_path,
        output_dir=output_dir,
        gateway=gateway,
        generate_png=True,
        use_3d_fallback=True,
    )


def _run_one(
    sample_path: Path,
    run_dir: Path,
    gateway,
) -> dict:
    data = json.loads(sample_path.read_text())
    name = data.get("name", sample_path.stem)
    code = data.get("generated_cadquery_code", "")
    gt_geom = data.get("geometry_properties", {})

    sample_dir = run_dir / name
    sample_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "name": name,
        "source": sample_path.name,
        "success": False,
        "error": None,
        "geometry_got": {},
        "geometry_gt": gt_geom,
        "geometry_diff_pct": {},
        "screenshots": {},
        "step_path": None,
        "elapsed_s": 0.0,
    }

    if not code:
        result["error"] = "no generated_cadquery_code in JSON"
        return result

    t0 = time.time()
    exec_result = gateway.execute("cadquery", code, timeout_seconds=60.0)
    result["elapsed_s"] = round(time.time() - t0, 2)

    if not exec_result.success:
        result["error"] = exec_result.error_message or "execution failed"
        return result

    # Move STEP to run dir
    step_src = exec_result.step_path
    if step_src and Path(step_src).exists():
        dest_step = sample_dir / f"{name}.step"
        shutil.move(step_src, dest_step)
        result["step_path"] = str(dest_step)

        # Render 4 views
        screenshots_dir = sample_dir / "screenshots"
        view_paths = _render_views(dest_step, screenshots_dir, gateway)
        result["screenshots"] = {k: str(v) for k, v in view_paths.items()}
    else:
        result["error"] = "execution succeeded but no STEP produced"
        return result

    result["success"] = True
    result["geometry_got"] = exec_result.geometry_props or {}
    result["geometry_diff_pct"] = _geometry_diff(
        result["geometry_got"], gt_geom
    )
    return result


def _print_row(r: dict) -> None:
    status = "PASS" if r["success"] else "FAIL"
    elapsed = r["elapsed_s"]
    vol_diff = r["geometry_diff_pct"].get("volume")
    face_diff = r["geometry_diff_pct"].get("face_count")
    shots = len(r["screenshots"])
    vol_str = f"{vol_diff:6.1f}%" if vol_diff is not None else "   N/A "
    face_str = f"{face_diff:5.1f}%" if face_diff is not None else "  N/A "
    err = f" [{r['error']}]" if r["error"] else ""
    print(
        f"  [{status}] {r['name'][:40]:<40}  "
        f"{elapsed:5.1f}s  vol_err={vol_str}  face_err={face_str}  "
        f"shots={shots}{err}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark GT code execution")
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of samples to run (0 = all).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sample selection.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory (default: data/benchmark_runs/<timestamp>).",
    )
    args = parser.parse_args()

    bench_dir = _ROOT / "data" / "benchmark"
    all_jsons = sorted(bench_dir.glob("*.json"))
    if not all_jsons:
        print(f"[error] No JSONs in {bench_dir}")
        return 1

    if args.samples > 0:
        random.seed(args.seed)
        samples = random.sample(all_jsons, min(args.samples, len(all_jsons)))
        samples = sorted(samples)
    else:
        samples = all_jsons

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.out) if args.out else _ROOT / "data" / "benchmark_runs" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"Benchmark GT Execution  —  {len(samples)} samples  →  {run_dir}")
    print(f"{'='*70}")

    gateway = _build_gateway()

    results = []
    for i, p in enumerate(samples, 1):
        print(f"\n[{i}/{len(samples)}] {p.stem}")
        r = _run_one(p, run_dir, gateway)
        results.append(r)
        _print_row(r)

    # Summary
    passed = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    total = len(results)
    pass_rate = len(passed) / total * 100 if total else 0

    vol_errs = [
        r["geometry_diff_pct"]["volume"]
        for r in passed
        if r["geometry_diff_pct"].get("volume") is not None
    ]
    mean_vol_err = sum(vol_errs) / len(vol_errs) if vol_errs else None

    face_errs = [
        r["geometry_diff_pct"]["face_count"]
        for r in passed
        if r["geometry_diff_pct"].get("face_count") is not None
    ]
    mean_face_err = sum(face_errs) / len(face_errs) if face_errs else None

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Total:     {total}")
    print(f"  Pass:      {len(passed)}  ({pass_rate:.1f}%)")
    print(f"  Fail:      {len(failed)}")
    if mean_vol_err is not None:
        print(f"  Mean vol err:   {mean_vol_err:.2f}%")
    if mean_face_err is not None:
        print(f"  Mean face err:  {mean_face_err:.2f}%")
    if failed:
        print("\n  Failed samples:")
        for r in failed:
            print(f"    {r['name']}: {r['error']}")

    # Save JSON report
    report_path = run_dir / "report.json"
    report = {
        "timestamp": ts,
        "total": total,
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate_pct": round(pass_rate, 2),
        "mean_volume_err_pct": round(mean_vol_err, 2) if mean_vol_err is not None else None,
        "mean_face_count_err_pct": round(mean_face_err, 2) if mean_face_err is not None else None,
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")
    print(f"  Artifacts: {run_dir}/")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
