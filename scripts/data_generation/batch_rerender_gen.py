"""
Batch re-render gen STEP files → stem-centric FS, update gen_views_norm_dir in CSV.

Targets stems where gen_views_norm_dir points to legacy archive paths.
Output: data/data_generation/generated_data/fusion360/<stem>/verified_<run>/views/

Usage:
  uv run python3 scripts/data_generation/batch_rerender_gen.py [--limit N] [--dry-run]
  uv run python3 scripts/data_generation/batch_rerender_gen.py --all  # re-render all stems
"""

import argparse
import fcntl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))

import pandas as pd

STEM_FS = ROOT / "data/data_generation/generated_data/fusion360"
VERIFIED_CSV = ROOT / "data/data_generation/verified_parts.csv"
_CSV_LOCK = str(VERIFIED_CSV) + ".lock"


def _s(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return "" if s in ("nan", "None", "") else s


def _strip_suffix(stem: str) -> str:
    for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
        if stem.endswith(sfx):
            return stem[: -len(sfx)]
    return stem


def _views_dir(stem: str, run: str) -> Path:
    """Stem-centric views dir: generated_data/fusion360/<base>/verified_<run>/views."""
    base = _strip_suffix(stem)
    run_folder = f"verified_{run}" if run else "verified"
    return STEM_FS / base / run_folder / "views"


def render_stem(gen_step: str, out_dir: Path) -> tuple[str | None, str | None]:
    from render_normalized_views import render_step_normalized
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        paths = render_step_normalized(gen_step, str(out_dir))
        return paths["composite"], None
    except Exception as e:
        return None, str(e)


def _update_csv(stem: str, new_views_dir: str) -> None:
    with open(_CSV_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            df = pd.read_csv(VERIFIED_CSV)
            mask = df["stem"] == stem
            if mask.any():
                df.at[df[mask].index[0], "gen_views_norm_dir"] = new_views_dir
            df.to_csv(VERIFIED_CSV, index=False)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="Re-render all stems (default: only archive paths)")
    args = ap.parse_args()

    vdf = pd.read_csv(VERIFIED_CSV)
    has_gen = vdf["gen_step_path"].notna() & (vdf["gen_step_path"] != "")

    if args.all:
        rows = vdf[has_gen].copy()
    else:
        # Only stems with archive gen_views paths
        archive_mask = vdf["gen_views_norm_dir"].str.contains("archive", na=False)
        rows = vdf[has_gen & archive_mask].copy()

    if args.limit:
        rows = rows.iloc[: args.limit]

    print(f"Targets: {len(rows)} stems  (dry={args.dry_run})")

    done = skipped = failed = 0
    for _, row in rows.iterrows():
        stem = row["stem"]
        gen_step = _s(row.get("gen_step_path"))
        run = _s(row.get("pipeline_run")) or "unknown"

        if not gen_step or not (ROOT / gen_step).exists():
            skipped += 1
            continue

        out_dir = _views_dir(stem, run)
        composite = out_dir / "composite.png"

        if args.dry_run:
            print(f"[dry] {stem} → {composite}")
            done += 1
            continue

        # Skip if already rendered there
        if composite.exists():
            rel = str(out_dir.relative_to(ROOT))
            _update_csv(stem, rel)
            skipped += 1
            continue

        comp_path, err = render_stem(str(ROOT / gen_step), out_dir)
        if err:
            print(f"FAIL {stem}: {err[:120]}")
            failed += 1
        else:
            rel = str(out_dir.relative_to(ROOT))
            _update_csv(stem, rel)
            done += 1
            if done % 50 == 0:
                print(f"  done={done} failed={failed} skipped={skipped}")

    print(f"\nDone: rendered={done} failed={failed} skipped={skipped}")


if __name__ == "__main__":
    main()
