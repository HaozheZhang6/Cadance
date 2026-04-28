"""Post-hoc check: do any new data_arg_180k_* params match existing cad_bench params?

Reads `synth_parts.csv` rows, splits by pipeline_run prefix:
  - existing = NOT data_arg_180k_*
  - new      = data_arg_180k_*

Hashes each row's params_json (sort_keys=True). Reports overlap count by family.

Run after Phase 1 completes. If overlap > 0.5%, consider re-rolling new samples
with shifted seeds.
"""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CSV = ROOT / "data" / "data_generation" / "synth_parts.csv"


def _hash(params: dict) -> str:
    return hashlib.md5(
        json.dumps(params, sort_keys=True, default=str).encode()
    ).hexdigest()


def main() -> None:
    if not CSV.exists():
        sys.exit(f"missing {CSV}")
    df = pd.read_csv(CSV)
    df = df[df["status"] == "accepted"]

    is_new = df["pipeline_run"].fillna("").str.startswith("data_arg_180k_")
    old = df[~is_new]
    new = df[is_new]
    print(f"existing accepted: {len(old)} rows, new 180k: {len(new)} rows")
    if len(new) == 0:
        sys.exit("No new 180k rows yet — run Phase 1 first.")

    old_hashes: set[str] = set()
    old_skipped = 0
    for s in old["params_json"].fillna(""):
        if not s:
            continue
        try:
            p = json.loads(s)
            p.pop("base_plane", None)
            old_hashes.add(_hash(p))
        except (json.JSONDecodeError, ValueError):
            old_skipped += 1
    print(
        f"old unique param hashes: {len(old_hashes)} (skipped unparseable: {old_skipped})"
    )

    # Per-family collision count
    coll_by_fam: dict[str, int] = defaultdict(int)
    new_by_fam: dict[str, int] = defaultdict(int)
    new_parsed = 0
    new_skipped = 0
    for fam, s in zip(new["family"].fillna(""), new["params_json"].fillna("")):
        new_by_fam[fam] += 1
        if not s:
            continue
        try:
            p = json.loads(s)
            p.pop("base_plane", None)
            new_parsed += 1
            if _hash(p) in old_hashes:
                coll_by_fam[fam] += 1
        except (json.JSONDecodeError, ValueError):
            new_skipped += 1

    total_coll = sum(coll_by_fam.values())
    denom = max(1, new_parsed)
    pct = 100 * total_coll / denom
    print(
        f"\nTotal collisions: {total_coll} / {new_parsed} parsed new "
        f"({pct:.2f}%); skipped unparseable new: {new_skipped}"
    )
    if total_coll == 0:
        print("✓ Zero overlap with existing cad_bench")
    else:
        print("\nPer-family collisions (>0):")
        for fam in sorted(coll_by_fam, key=lambda f: -coll_by_fam[f]):
            n_coll = coll_by_fam[fam]
            n_new = new_by_fam[fam]
            print(f"  {fam:30s} {n_coll:5d}/{n_new:5d}  ({100 * n_coll / n_new:.1f}%)")


if __name__ == "__main__":
    main()
