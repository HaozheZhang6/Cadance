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
    for s in old["params_json"].fillna(""):
        if not s:
            continue
        try:
            p = json.loads(s)
            p.pop("base_plane", None)
            old_hashes.add(_hash(p))
        except Exception:  # noqa: BLE001
            pass
    print(f"old unique param hashes: {len(old_hashes)}")

    # Per-family collision count
    coll_by_fam: dict[str, int] = defaultdict(int)
    new_by_fam: dict[str, int] = defaultdict(int)
    for fam, s in zip(new["family"].fillna(""), new["params_json"].fillna("")):
        new_by_fam[fam] += 1
        if not s:
            continue
        try:
            p = json.loads(s)
            p.pop("base_plane", None)
            if _hash(p) in old_hashes:
                coll_by_fam[fam] += 1
        except Exception:  # noqa: BLE001
            pass

    total_coll = sum(coll_by_fam.values())
    pct = 100 * total_coll / len(new)
    print(f"\nTotal collisions: {total_coll} / {len(new)} new ({pct:.2f}%)")
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
