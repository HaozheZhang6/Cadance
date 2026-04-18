"""Summary report generation after a batch run."""

import json
from collections import Counter
from pathlib import Path


def build_report(results: list[dict]) -> dict:
    """Build a summary report dict from per-sample result dicts.

    Each result dict has: status, family, difficulty, reject_stage,
    reject_reason, ops_used, feature_tags.
    """
    total = len(results)
    accepted = [r for r in results if r["status"] == "accepted"]
    rejected = [r for r in results if r["status"] == "rejected"]

    reject_reasons = Counter()
    reject_stages = Counter()
    for r in rejected:
        reject_reasons[r.get("reject_reason", "unknown")] += 1
        reject_stages[r.get("reject_stage", "unknown")] += 1

    family_hist = Counter(r["family"] for r in results)
    diff_hist = Counter(r["difficulty"] for r in results)

    # Accepted-only histograms
    family_accepted = Counter(r["family"] for r in accepted)
    diff_accepted = Counter(r["difficulty"] for r in accepted)

    # Op coverage
    op_counter = Counter()
    for r in accepted:
        for op in r.get("ops_used", []):
            op_counter[op] += 1

    # Feature tags
    tag_counter = Counter()
    for r in accepted:
        for k, v in r.get("feature_tags", {}).items():
            if v:
                tag_counter[k] += 1

    return {
        "requested": total,
        "accepted": len(accepted),
        "rejected": len(rejected),
        "accept_rate": round(len(accepted) / max(total, 1) * 100, 1),
        "reject_reasons": dict(reject_reasons.most_common()),
        "reject_stages": dict(reject_stages.most_common()),
        "family_requested": dict(family_hist),
        "family_accepted": dict(family_accepted),
        "difficulty_requested": dict(diff_hist),
        "difficulty_accepted": dict(diff_accepted),
        "op_coverage": dict(op_counter.most_common()),
        "feature_tags": dict(tag_counter.most_common()),
    }


def write_report(report: dict, path: str | Path):
    """Write report dict to JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
