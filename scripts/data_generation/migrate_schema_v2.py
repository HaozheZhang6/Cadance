"""
Schema migration v2: stem-centric field rename.

Renames/restructures fields in verified_parts.csv, verified_pairs.jsonl, parts.csv.

Old → New mapping (verified_parts / JSONL):
  raw_step_path   → gt_step_path
  norm_step_path  → gt_norm_step_path
  ops_json_path   → gt_json_path
  views_raw_dir   → DELETE (was duplicate of views_gen_dir)
  views_gen_dir   → gt_views_norm_dir
  source          → pipeline_run
  source_stem     → fix_source_stem

New empty fields added:
  data_source         (fusion360 | deepcad | synthetic)
  attempt_id          (link to parts.csv attempt_id)
  model               (model used for generation)
  provider            (openai | anthropic | glm)
  gen_views_norm_dir  (views_gen/<pipeline_run>/<stem>/)

Old → New mapping (parts.csv):
  raw_step_path   → gt_step_path
  raw_step_exists → gt_step_exists
  views_raw_exists → gt_views_norm_exists
  views_gen_exists → gen_views_norm_exists
  run             → pipeline_run

Run: uv run python3 scripts/data_generation/migrate_schema_v2.py
"""

import csv
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "data_generation"

VERIFIED_CSV  = DATA / "verified_parts.csv"
VERIFIED_JSONL = DATA / "verified" / "verified_pairs.jsonl"
PARTS_CSV     = DATA / "parts.csv"


# ── field rename maps ──────────────────────────────────────────────────────────

VERIFIED_RENAME = {
    "raw_step_path":  "gt_step_path",
    "norm_step_path": "gt_norm_step_path",
    "ops_json_path":  "gt_json_path",
    "views_gen_dir":  "gt_views_norm_dir",
    "source":         "pipeline_run",
    "source_stem":    "fix_source_stem",
}
VERIFIED_DELETE = {"views_raw_dir"}  # duplicate of views_gen_dir

NEW_VERIFIED_FIELDS_ORDER = [
    "stem",
    "data_source",          # NEW: fusion360 | deepcad | synthetic
    "gt_step_path",         # was raw_step_path
    "gt_norm_step_path",    # was norm_step_path
    "gt_json_path",         # was ops_json_path
    "ops_program_path",
    "gen_step_path",
    "cq_code_path",
    "norm_cq_code_path",
    "iou",
    "verified",
    "gt_views_norm_dir",    # was views_gen_dir (both pointed to views/<stem>/)
    "gen_views_norm_dir",   # NEW: views_gen/<pipeline_run>/<stem>/
    "pipeline_run",         # was source
    "attempt_id",           # NEW: link to parts.csv
    "model",                # NEW: generation model
    "provider",             # NEW: openai | anthropic | glm
    "timestamp",
    "visual_verdict",
    "visual_reason",
    "complexity_class",
    "note",
    "fix_source_stem",      # was source_stem
    "bad_cq_path",
]

PARTS_RENAME = {
    "raw_step_path":   "gt_step_path",
    "raw_step_exists": "gt_step_exists",
    "views_raw_exists": "gt_views_norm_exists",
    "views_gen_exists": "gen_views_norm_exists",
    "run":             "pipeline_run",
}

NEW_PARTS_FIELDS_ORDER = [
    "attempt_id",
    "stem",
    "base_stem",
    "pipeline_run",         # was run
    "status",
    "iou",
    "gt_vol",
    "provider",
    "model",                # NEW: pulled from ops/report
    "complexity",
    "gt_step_exists",       # was raw_step_exists
    "cq_code_exists",
    "gen_step_exists",
    "gt_views_norm_exists", # was views_raw_exists
    "gen_views_norm_exists",# was views_gen_exists
    "gt_step_path",         # was raw_step_path
    "cq_code_path",
    "gen_step_path",
    "fix_attempts",
    "fix_note",
    "retry_reason",
    "failure_code",
    "fixed_stem",
    "updated_at",
]


# ── helpers ────────────────────────────────────────────────────────────────────

def _infer_data_source(stem: str) -> str:
    if stem.startswith("synth_"):
        return "synthetic"
    if re.match(r"^\d{5,}", stem):
        return "fusion360"
    return ""


def _migrate_verified_row(row: dict) -> dict:
    out = {}
    for old, val in row.items():
        if old in VERIFIED_DELETE:
            continue
        new = VERIFIED_RENAME.get(old, old)
        out[new] = val

    # Fill new fields with defaults if missing
    if "data_source" not in out:
        out["data_source"] = _infer_data_source(out.get("stem", ""))
    for f in ("gen_views_norm_dir", "attempt_id", "model", "provider"):
        if f not in out:
            out[f] = ""

    return {f: out.get(f, "") for f in NEW_VERIFIED_FIELDS_ORDER}


def _migrate_parts_row(row: dict) -> dict:
    out = {}
    for old, val in row.items():
        new = PARTS_RENAME.get(old, old)
        out[new] = val
    if "model" not in out:
        out["model"] = ""
    return {f: out.get(f, "") for f in NEW_PARTS_FIELDS_ORDER}


# ── migrate verified_parts.csv ────────────────────────────────────────────────

def migrate_verified_csv():
    csv.field_size_limit(10 * 1024 * 1024)
    with open(VERIFIED_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    # Check if already migrated
    if rows and "pipeline_run" in rows[0]:
        print("verified_parts.csv already migrated — skipping")
        return

    migrated = [_migrate_verified_row(r) for r in rows]

    with open(VERIFIED_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NEW_VERIFIED_FIELDS_ORDER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(migrated)

    print(f"verified_parts.csv migrated: {len(migrated)} rows")


# ── migrate verified_pairs.jsonl ──────────────────────────────────────────────

def migrate_jsonl():
    if not VERIFIED_JSONL.exists():
        print("verified_pairs.jsonl not found — skipping")
        return

    records = []
    with open(VERIFIED_JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # Check if already migrated
    if records and "pipeline_run" in records[0]:
        print("verified_pairs.jsonl already migrated — skipping")
        return

    migrated = [_migrate_verified_row(r) for r in records]

    with open(VERIFIED_JSONL, "w") as f:
        for r in migrated:
            f.write(json.dumps(r) + "\n")

    print(f"verified_pairs.jsonl migrated: {len(migrated)} records")


# ── migrate parts.csv ─────────────────────────────────────────────────────────

def migrate_parts_csv():
    csv.field_size_limit(10 * 1024 * 1024)
    with open(PARTS_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    # Check if already migrated
    if rows and "pipeline_run" in rows[0]:
        print("parts.csv already migrated — skipping")
        return

    migrated = [_migrate_parts_row(r) for r in rows]

    with open(PARTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NEW_PARTS_FIELDS_ORDER, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(migrated)

    print(f"parts.csv migrated: {len(migrated)} rows")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Migrating schema to v2 (stem-centric field names)...")
    migrate_verified_csv()
    migrate_jsonl()
    migrate_parts_csv()
    print("Done.")
