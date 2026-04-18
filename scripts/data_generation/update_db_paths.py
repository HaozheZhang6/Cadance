"""
Update verified_pairs.jsonl + parts.csv paths using migration_manifest.csv.

Replaces all old_path → new_path for path fields in both files, then rebuilds CSVs.

Usage:
  uv run python3 scripts/data_generation/update_db_paths.py [--dry-run]
"""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "data_generation"
MANIFEST_PATH = DATA / "migration_manifest.csv"
VERIFIED_JSONL = DATA / "verified" / "verified_pairs.jsonl"
PARTS_CSV = DATA / "parts.csv"

# Fields that contain file paths in verified_parts / JSONL
VERIFIED_PATH_FIELDS = [
    "gt_step_path", "gt_norm_step_path", "gt_json_path", "ops_program_path",
    "gen_step_path", "cq_code_path", "norm_cq_code_path",
    "gt_views_norm_dir", "gen_views_norm_dir", "bad_cq_path",
]

# Fields that contain file paths in parts.csv
PARTS_PATH_FIELDS = [
    "gt_step_path", "cq_code_path", "gen_step_path",
]


def _build_path_map(manifest_path: Path) -> dict[str, str]:
    """old_path → new_path, only for entries where src_exists=True."""
    mapping: dict[str, str] = {}
    with open(manifest_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["src_exists"] == "True" and row["old_path"] and row["new_path"]:
                mapping[row["old_path"]] = row["new_path"]
    return mapping


def _remap(val: str, path_map: dict[str, str]) -> str:
    """Remap a single path value if it appears in the map."""
    if not val or val in ("nan", "None"):
        return val
    return path_map.get(val, val)


def update_jsonl(path_map: dict[str, str], dry_run: bool) -> tuple[int, int]:
    """Update verified_pairs.jsonl. Returns (records_total, records_changed)."""
    records = []
    with open(VERIFIED_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    changed = 0
    for r in records:
        record_changed = False
        for field in VERIFIED_PATH_FIELDS:
            old = r.get(field, "")
            new = _remap(old, path_map)
            if new != old:
                r[field] = new
                record_changed = True
        if record_changed:
            changed += 1

    if not dry_run:
        with open(VERIFIED_JSONL, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    return len(records), changed


def update_parts_csv(path_map: dict[str, str], dry_run: bool) -> tuple[int, int]:
    """Update parts.csv path fields."""
    rows = []
    with open(PARTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    changed = 0
    for row in rows:
        row_changed = False
        for field in PARTS_PATH_FIELDS:
            if field not in row:
                continue
            old = row[field]
            new = _remap(old, path_map)
            if new != old:
                row[field] = new
                row_changed = True
        if row_changed:
            changed += 1

    if not dry_run:
        with open(PARTS_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    return len(rows), changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("Loading manifest...")
    path_map = _build_path_map(MANIFEST_PATH)
    print(f"  {len(path_map)} path mappings loaded")

    print("Updating verified_pairs.jsonl...")
    total, changed = update_jsonl(path_map, args.dry_run)
    print(f"  {changed}/{total} records updated")

    print("Updating parts.csv...")
    total, changed = update_parts_csv(path_map, args.dry_run)
    print(f"  {changed}/{total} rows updated")

    if not args.dry_run:
        print("Rebuilding CSVs via db.py...")
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
        import db
        db.build_all_csvs()

    mode = "DRY RUN" if args.dry_run else "DONE"
    print(f"\n[{mode}]")


if __name__ == "__main__":
    main()
