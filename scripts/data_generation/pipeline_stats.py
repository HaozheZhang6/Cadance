#!/usr/bin/env python
"""Print aggregated pipeline statistics across all validation runs.

Reads all data/data_generation/codex_validation/*/validation_report.json files and
data/data_generation/verified/verified_pairs.jsonl, then prints a summary.

Usage:
  uv run python scripts/data_generation/pipeline_stats.py
  uv run python scripts/data_generation/pipeline_stats.py --md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "data/codex_validation"
VERIFIED_JSONL = REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl"


def _load_all_runs() -> list[dict]:
    runs = []
    for report_path in sorted(RUNS_DIR.glob("*/validation_report.json")):
        try:
            r = json.loads(report_path.read_text(encoding="utf-8"))
            r["_run_dir"] = report_path.parent.name
            runs.append(r)
        except Exception:
            pass
    return runs


def _load_verified_pairs() -> list[dict]:
    if not VERIFIED_JSONL.exists():
        return []
    pairs = []
    for line in VERIFIED_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                pairs.append(json.loads(line))
            except Exception:
                pass
    return pairs


def _classify_from_error(err: str) -> str:
    """Classify error string (for old records without error_type field)."""
    if not err:
        return "unknown"
    e = err.lower()
    if "exit=1" in e or "oauth" in e or "unauthorized" in e:
        return "codex_auth_error"
    if "model" in e and ("not found" in e or "does not exist" in e):
        return "model_not_found"
    if "rate limit" in e or "429" in e:
        return "rate_limit"
    if "timeout" in e or "timed out" in e:
        return "timeout"
    return "other"


def print_stats(md: bool = False) -> None:
    runs = _load_all_runs()
    pairs = _load_verified_pairs()

    # Global totals
    total_tested = 0
    total_executed = 0
    total_iou_pass = 0
    total_verified = 0

    # By model/provider
    by_model: dict[str, dict] = defaultdict(
        lambda: {
            "total": 0,
            "executed": 0,
            "iou_pass": 0,
            "verified": 0,
            "errors": defaultdict(int),
            "runs": 0,
        }
    )

    for run in runs:
        model = run.get("model", "unknown")
        provider = run.get("provider", "unknown")
        key = f"{model}/{provider}" if provider != "unknown" else model
        stats = by_model[key]
        stats["runs"] += 1
        results = run.get("results", [])
        for r in results:
            total_tested += 1
            stats["total"] += 1
            if r.get("stage") == "done":
                total_executed += 1
                stats["executed"] += 1
                if r.get("iou_pass"):
                    total_iou_pass += 1
                    stats["iou_pass"] += 1
                if r.get("ok"):
                    total_verified += 1
                    stats["verified"] += 1
            else:
                err_type = r.get("error_type") or _classify_from_error(
                    r.get("error", "")
                )
                stats["errors"][err_type] += 1

    # Verified pairs breakdown
    by_complexity: dict[str, int] = defaultdict(int)
    by_run: dict[str, int] = defaultdict(int)
    for p in pairs:
        by_complexity[p.get("complexity_class", "unknown")] += 1
        by_run[p.get("run", "unknown")] += 1

    if md:
        _print_md(
            runs,
            pairs,
            by_model,
            total_tested,
            total_executed,
            total_iou_pass,
            total_verified,
            by_complexity,
            by_run,
        )
    else:
        _print_text(
            runs,
            pairs,
            by_model,
            total_tested,
            total_executed,
            total_iou_pass,
            total_verified,
            by_complexity,
            by_run,
        )


def _print_text(
    runs,
    pairs,
    by_model,
    total_tested,
    total_executed,
    total_iou_pass,
    total_verified,
    by_complexity,
    by_run,
):
    print(f"\n{'='*60}")
    print("PIPELINE STATS — ALL RUNS")
    print(f"{'='*60}")
    print(f"  Runs loaded      : {len(runs)}")
    print(f"  Parts tested     : {total_tested}")
    print(f"  CQ executed      : {total_executed}")
    print(
        f"  IoU >= 0.9       : {total_iou_pass} ({total_iou_pass/max(total_tested,1)*100:.1f}%)"
    )
    print(
        f"  Verified         : {total_verified} ({total_verified/max(total_tested,1)*100:.1f}%)"
    )
    print(f"\nVerified pairs in verified_pairs.jsonl: {len(pairs)}")
    if by_complexity:
        print("  By complexity:", dict(by_complexity))
    print("\nBy model/provider:")
    for key, s in sorted(by_model.items()):
        pct = s["iou_pass"] / max(s["total"], 1) * 100
        exec_pct = s["executed"] / max(s["total"], 1) * 100
        print(f"  {key}")
        print(
            f"    total={s['total']}  exec={s['executed']}({exec_pct:.0f}%)  iou_pass={s['iou_pass']}({pct:.0f}%)  verified={s['verified']}"
        )
        if s["errors"]:
            print(f"    errors: {dict(s['errors'])}")
    print()


def _print_md(
    runs,
    pairs,
    by_model,
    total_tested,
    total_executed,
    total_iou_pass,
    total_verified,
    by_complexity,
    by_run,
):
    lines = ["# Pipeline Stats — All Runs\n"]
    lines.append("## Global Totals\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Runs loaded | {len(runs)} |")
    lines.append(f"| Parts tested | {total_tested} |")
    lines.append(f"| CQ executed | {total_executed} |")
    lines.append(
        f"| IoU >= 0.9 | {total_iou_pass} ({total_iou_pass/max(total_tested,1)*100:.1f}%) |"
    )
    lines.append(
        f"| Verified | {total_verified} ({total_verified/max(total_tested,1)*100:.1f}%) |"
    )
    lines.append(f"| verified_pairs.jsonl | {len(pairs)} |")
    lines.append("")
    lines.append("## By Model / Provider\n")
    lines.append(
        "| Model/Provider | Runs | Tested | Executed | IoU Pass | Verified | Top Error |"
    )
    lines.append(
        "|----------------|------|--------|----------|----------|----------|-----------|"
    )
    for key, s in sorted(by_model.items()):
        pct = f"{s['iou_pass']/max(s['total'],1)*100:.0f}%"
        top_err = (
            max(s["errors"], key=s["errors"].get, default="—") if s["errors"] else "—"
        )
        lines.append(
            f"| {key} | {s['runs']} | {s['total']} | {s['executed']} | {s['iou_pass']} ({pct}) | {s['verified']} | {top_err} |"
        )
    lines.append("")
    if by_complexity:
        lines.append("## Verified Pairs by Complexity\n")
        lines.append("| Complexity | Count |")
        lines.append("|------------|-------|")
        for c, n in sorted(by_complexity.items()):
            lines.append(f"| {c} | {n} |")
        lines.append("")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", action="store_true", help="Output markdown table")
    args = parser.parse_args()
    print_stats(md=args.md)


if __name__ == "__main__":
    main()
