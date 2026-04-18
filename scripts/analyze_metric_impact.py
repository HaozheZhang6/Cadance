#!/usr/bin/env python3
"""Analyze impact of switching from binary to continuous IoU metric.

This script simulates the greedy optimizer behavior with different metrics
using existing trace data - NO LLM calls needed.

Usage:
    uv run python scripts/analyze_metric_impact.py
"""

import json
from dataclasses import dataclass
from pathlib import Path

# Paths
TRACES_DIR = Path("eval_traces/cad/intent_decomposition")
BASELINE_TRACES = TRACES_DIR / "baseline_train"
CHECKPOINT_DIR = Path("data/dspy_optimized/latest")


@dataclass
class TestResult:
    test_id: str
    level: int
    iou_score: float
    passed: bool  # IoU >= 0.9


def load_baseline_traces() -> dict[str, TestResult]:
    """Load all baseline traces with IoU scores."""
    results = {}

    for trace_file in BASELINE_TRACES.glob("L*.json"):
        with open(trace_file) as f:
            data = json.load(f)

        test_id = data.get("test_id", trace_file.stem)
        comparison = data.get("comparison") or {}
        iou_score = comparison.get("iou_score") or 0.0
        passed = comparison.get("iou_pass", False)
        level = int(test_id.split("_")[0][1:]) if "_" in test_id else 1

        results[test_id] = TestResult(
            test_id=test_id,
            level=level,
            iou_score=iou_score if iou_score is not None else 0.0,
            passed=passed,
        )

    return results


def load_train_dev_split() -> tuple[list[str], list[str]]:
    """Load the train/dev split from the optimization checkpoint."""
    training_data_path = CHECKPOINT_DIR / "training_data.json"

    with open(training_data_path) as f:
        data = json.load(f)

    return data["train_ids"], data["dev_ids"]


def simulate_greedy_binary(
    baseline: dict[str, TestResult],
    train_ids: list[str],
    dev_ids: list[str],
    max_demos: int = 8,
    patience: int = 5,
) -> tuple[list[str], list[dict]]:
    """Simulate greedy with BINARY success rate (original behavior).

    Note: This is a SIMULATION - in reality, adding demos changes LLM output.
    Here we just show what the baseline scores would produce if demos had no effect.
    """
    # Sort by curriculum: lowest IoU first, then lowest level
    train_results = [(tid, baseline[tid]) for tid in train_ids if tid in baseline]
    train_results.sort(key=lambda x: (x[1].iou_score, x[1].level, x[0]))

    # Compute baseline holdout success rate
    dev_results = [baseline[tid] for tid in dev_ids if tid in baseline]
    baseline_success = sum(1 for r in dev_results if r.passed) / len(dev_results)

    print("\n=== BINARY METRIC (Original) ===")
    print(
        f"Baseline holdout success rate: {baseline_success:.1%} ({sum(1 for r in dev_results if r.passed)}/{len(dev_results)})"
    )
    print(f"Each test = {100 / len(dev_results):.1f}% of metric")

    # Greedy would try to improve this, but with no actual effect from demos...
    # This shows why 0 demos were selected: the baseline is already at a local max

    return [], [{"baseline_score": baseline_success}]


def simulate_greedy_iou(
    baseline: dict[str, TestResult],
    train_ids: list[str],
    dev_ids: list[str],
    max_demos: int = 8,
    patience: int = 5,
) -> tuple[list[str], list[dict]]:
    """Simulate greedy with CONTINUOUS average IoU metric.

    Note: This is a SIMULATION to show metric sensitivity.
    """
    # Sort by curriculum: lowest IoU first, then lowest level
    train_results = [(tid, baseline[tid]) for tid in train_ids if tid in baseline]
    train_results.sort(key=lambda x: (x[1].iou_score, x[1].level, x[0]))

    # Compute baseline holdout average IoU
    dev_results = [baseline[tid] for tid in dev_ids if tid in baseline]
    baseline_avg_iou = sum(r.iou_score for r in dev_results) / len(dev_results)

    print("\n=== CONTINUOUS IoU METRIC (Proposed) ===")
    print(f"Baseline holdout average IoU: {baseline_avg_iou:.4f}")
    print(f"Min IoU in holdout: {min(r.iou_score for r in dev_results):.4f}")
    print(f"Max IoU in holdout: {max(r.iou_score for r in dev_results):.4f}")

    return [], [{"baseline_avg_iou": baseline_avg_iou}]


def analyze_metric_sensitivity():
    """Main analysis function."""
    print("=" * 60)
    print("METRIC SENSITIVITY ANALYSIS")
    print("=" * 60)

    # Load data
    baseline = load_baseline_traces()
    train_ids, dev_ids = load_train_dev_split()

    print(f"\nLoaded {len(baseline)} baseline traces")
    print(f"Train: {len(train_ids)}, Dev: {len(dev_ids)}")

    # Show detailed IoU breakdown for dev set
    dev_results = [baseline[tid] for tid in dev_ids if tid in baseline]

    print("\n=== HOLDOUT SET IoU DISTRIBUTION ===")
    print(f"{'Test ID':<10} {'Level':<6} {'IoU':>8} {'Pass':>6}")
    print("-" * 35)

    for tid in sorted(dev_ids):
        if tid in baseline:
            r = baseline[tid]
            print(
                f"{r.test_id:<10} L{r.level:<5} {r.iou_score:>8.4f} {'✓' if r.passed else '✗':>6}"
            )

    # Summary stats
    passing = [r for r in dev_results if r.passed]
    failing = [r for r in dev_results if not r.passed]

    print("\n=== SUMMARY ===")
    print(f"Passing tests (IoU >= 0.9): {len(passing)}/{len(dev_results)}")
    print(
        f"  Average IoU of passing: {sum(r.iou_score for r in passing) / len(passing):.4f}"
        if passing
        else "  N/A"
    )
    print(f"Failing tests (IoU < 0.9): {len(failing)}/{len(dev_results)}")
    print(
        f"  Average IoU of failing: {sum(r.iou_score for r in failing) / len(failing):.4f}"
        if failing
        else "  N/A"
    )

    # Compare metrics
    simulate_greedy_binary(baseline, train_ids, dev_ids)
    simulate_greedy_iou(baseline, train_ids, dev_ids)

    # Key insight
    print("\n=== KEY INSIGHT ===")
    avg_iou = sum(r.iou_score for r in dev_results) / len(dev_results)
    success_rate = sum(1 for r in dev_results if r.passed) / len(dev_results)

    print(f"Binary success rate: {success_rate:.1%}")
    print(f"Average IoU:         {avg_iou:.4f}")

    if failing:
        print(
            f"\nThe {len(failing)} failing tests have average IoU = {sum(r.iou_score for r in failing) / len(failing):.4f}"
        )
        print("These are partially correct but below threshold.")
        print("\nWith BINARY metric:")
        print(
            "  - A test improving from 0.45→0.89 IoU shows NO metric change (still fails)"
        )
        print(
            "  - A test improving from 0.89→0.91 IoU shows +4% metric change (now passes)"
        )
        print("\nWith CONTINUOUS IoU metric:")
        print("  - A test improving from 0.45→0.89 IoU shows +0.0176 metric change")
        print("  - A test improving from 0.89→0.91 IoU shows +0.0008 metric change")
        print("\n→ Continuous metric rewards partial improvements!")

    # Show train set curriculum ordering
    print("\n=== TRAIN SET CURRICULUM ORDER ===")
    print("(Lowest IoU first = hardest cases, lowest level = simpler concepts)")
    print(f"{'Rank':<5} {'Test ID':<10} {'Level':<6} {'IoU':>8}")
    print("-" * 35)

    train_results = [(tid, baseline[tid]) for tid in train_ids if tid in baseline]
    train_results.sort(key=lambda x: (x[1].iou_score, x[1].level, x[0]))

    for i, (_tid, r) in enumerate(train_results[:10], 1):
        print(f"{i:<5} {r.test_id:<10} L{r.level:<5} {r.iou_score:>8.4f}")

    print("...")


if __name__ == "__main__":
    analyze_metric_sensitivity()
