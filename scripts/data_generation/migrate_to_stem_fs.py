"""
Migrate CAD data to stem-centric filesystem.

Target structure:
  data/data_generation/generated_data/fusion360/<base_stem>/
  ├── gt/
  │   ├── gt.step
  │   ├── gt.json
  │   └── views/composite.png, view_0~3.png
  ├── <run_name>/                    (non-verified run)
  │   ├── cq.py
  │   ├── gen.step
  │   ├── checkpoint.json            (single record extracted from run's checkpoint.jsonl)
  │   └── views/composite.png, view_0~3.png
  └── verified_<run_name>/           (verified/manually_fixed run)
      ├── cq.py
      ├── cq_norm.py                 (if exists)
      ├── gen.step
      ├── gen_norm.step              (if exists)
      ├── checkpoint.json
      └── views/composite.png, view_0~3.png

Usage:
  # Dry run — generates migration_manifest.csv, no file copies
  uv run python3 scripts/data_generation/migrate_to_stem_fs.py --dry-run

  # Actual migration (old files untouched)
  uv run python3 scripts/data_generation/migrate_to_stem_fs.py

  # Limit to N stems (for testing)
  uv run python3 scripts/data_generation/migrate_to_stem_fs.py --dry-run --limit 10
"""

import argparse
import csv
import glob
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "data_generation"
DEST = DATA / "generated_data" / "fusion360"
MANIFEST_PATH = DATA / "migration_manifest.csv"

MANIFEST_FIELDS = [
    "base_stem", "stem", "pipeline_run", "status",
    "file_type", "old_path", "new_path", "src_exists",
]

VERIFIED_STATUSES = {"verified", "manually_fixed"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _s(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return "" if s in ("nan", "None", "") else s


def _strip_suffix(stem: str) -> str:
    """Return base stem (remove _claude_fixed, _copy_gt, _manual_fix)."""
    for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
        if stem.endswith(sfx):
            return stem[: -len(sfx)]
    return stem


def _run_dir_name(pipeline_run: str, status: str) -> str:
    """Folder name under base_stem for this run."""
    if status in VERIFIED_STATUSES:
        return f"verified_{pipeline_run}"
    return pipeline_run


def _find_gt_step(base_stem: str, gt_step_path: str) -> str | None:
    """Return best GT STEP path: explicit path first, then glob extrude_tools."""
    if gt_step_path and Path(gt_step_path).exists():
        return gt_step_path
    pattern = str(
        DATA / "open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools"
        / f"{base_stem}_*.step"
    )
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def _find_gt_json(base_stem: str, gt_json_path: str) -> str | None:
    p = gt_json_path and Path(gt_json_path)
    if p and p.exists():
        return gt_json_path
    candidate = DATA / "open_source/fusion360_gallery/raw/r1.0.1/reconstruction" / f"{base_stem}.json"
    return str(candidate) if candidate.exists() else None


def _find_gen_views(stem: str, pipeline_run: str, gen_views_norm_dir: str) -> Path | None:
    """Return gen views dir if it has composite.png."""
    candidates = []
    if gen_views_norm_dir:
        candidates.append(Path(gen_views_norm_dir))
    if pipeline_run:
        candidates.append(DATA / "views_gen" / pipeline_run / stem)
    candidates.append(DATA / "views_gen" / stem)
    for p in candidates:
        if (p / "composite.png").exists():
            return p
    return None


def _to_rel(p: Path) -> str:
    """Return path relative to ROOT, handling both absolute and relative inputs."""
    if p.is_absolute():
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)
    return str(p)


def _copy_views(src_dir: Path, dst_dir: Path, dry_run: bool) -> list[dict]:
    """Copy composite.png + view_0~3.png from src_dir to dst_dir/views/."""
    # Resolve relative paths against ROOT
    if not src_dir.is_absolute():
        src_dir = ROOT / src_dir
    entries = []
    for fname in ["composite.png", "view_0.png", "view_1.png", "view_2.png", "view_3.png"]:
        src = src_dir / fname
        dst = dst_dir / "views" / fname
        entries.append({
            "file_type": f"views/{fname}",
            "old_path": _to_rel(src),
            "new_path": _to_rel(dst),
            "src_exists": src.exists(),
        })
        if src.exists() and not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return entries


def _copy_file(src: str | Path | None, dst: Path, file_type: str, dry_run: bool) -> dict:
    if src:
        src_p = Path(src) if Path(src).is_absolute() else ROOT / src
        old_path = str(src_p.relative_to(ROOT))
    else:
        src_p = None
        old_path = ""
    exists = bool(src_p and src_p.exists())
    entry = {
        "file_type": file_type,
        "old_path": old_path,
        "new_path": _to_rel(dst),
        "src_exists": exists,
    }
    if exists and not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_p, dst)
    return entry


# ── checkpoint cache ──────────────────────────────────────────────────────────

_cp_cache: dict[str, dict[str, dict]] = {}  # run → {stem: record}


def _get_checkpoint_record(pipeline_run: str, stem: str) -> dict | None:
    if pipeline_run not in _cp_cache:
        cp_path = DATA / "codex_validation" / pipeline_run / "checkpoint.jsonl"
        records: dict[str, dict] = {}
        if cp_path.exists():
            with open(cp_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        r = json.loads(line)
                        s = r.get("stem", "")
                        if s:
                            records[s] = r
        _cp_cache[pipeline_run] = records
    return _cp_cache[pipeline_run].get(stem)


# ── per-stem GT copy (done once per base_stem) ────────────────────────────────

_gt_done: set[str] = set()


def _copy_gt(base_stem: str, gt_step_path: str, gt_json_path: str,
             gt_views_dir: str, dry_run: bool) -> list[dict]:
    if base_stem in _gt_done:
        return []
    _gt_done.add(base_stem)

    gt_dir = DEST / base_stem / "gt"
    entries = []

    # gt.step
    step_src = _find_gt_step(base_stem, gt_step_path)
    entries.append(_copy_file(step_src, gt_dir / "gt.step", "gt/gt.step", dry_run))

    # gt.json
    json_src = _find_gt_json(base_stem, gt_json_path)
    entries.append(_copy_file(json_src, gt_dir / "gt.json", "gt/gt.json", dry_run))

    # GT views
    gt_views_src = None
    if gt_views_dir:
        p = Path(gt_views_dir)
        if (p / "composite.png").exists():
            gt_views_src = p
    if gt_views_src is None:
        p = DATA / "views" / base_stem
        if (p / "composite.png").exists():
            gt_views_src = p
    if gt_views_src:
        entries += _copy_views(gt_views_src, gt_dir, dry_run)

    return entries


# ── per-run copy ──────────────────────────────────────────────────────────────

def _copy_run(
    stem: str, base_stem: str, pipeline_run: str, status: str,
    cq_code_path: str, gen_step_path: str,
    norm_cq_code_path: str, gen_views_norm_dir: str,
    dry_run: bool,
) -> list[dict]:
    run_dir_name = _run_dir_name(pipeline_run, status)
    run_dir = DEST / base_stem / run_dir_name
    entries = []

    # cq.py
    entries.append(_copy_file(cq_code_path or None, run_dir / "cq.py", "cq.py", dry_run))

    # gen.step
    entries.append(_copy_file(gen_step_path or None, run_dir / "gen.step", "gen.step", dry_run))

    # cq_norm.py (verified only)
    if norm_cq_code_path:
        entries.append(_copy_file(norm_cq_code_path, run_dir / "cq_norm.py", "cq_norm.py", dry_run))

    # checkpoint.json (single extracted record)
    cp_rec = _get_checkpoint_record(pipeline_run, stem)
    cp_dst = run_dir / "checkpoint.json"
    cp_src_path = DATA / "codex_validation" / pipeline_run / "checkpoint.jsonl"
    entries.append({
        "file_type": "checkpoint.json",
        "old_path": _to_rel(cp_src_path) if cp_src_path.exists() else "",
        "new_path": _to_rel(cp_dst),
        "src_exists": cp_rec is not None,
    })
    if cp_rec is not None and not dry_run:
        cp_dst.parent.mkdir(parents=True, exist_ok=True)
        with open(cp_dst, "w") as f:
            json.dump(cp_rec, f, indent=2)

    # gen views
    gen_views_src = _find_gen_views(stem, pipeline_run, gen_views_norm_dir)
    if gen_views_src:
        entries += _copy_views(gen_views_src, run_dir, dry_run)

    return entries


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="limit to N base_stems (for testing)")
    args = ap.parse_args()

    import pandas as pd

    pdf = pd.read_csv(DATA / "parts.csv")
    vdf = pd.read_csv(DATA / "verified_parts.csv")

    # Build verified lookup: stem → verified row
    v_lookup: dict[str, dict] = {}
    for _, vr in vdf.iterrows():
        v_lookup[vr["stem"]] = vr.to_dict()

    # Build gt_views_norm_dir lookup per base_stem (from verified_parts)
    gt_views_lookup: dict[str, str] = {}
    for _, vr in vdf.iterrows():
        bs = _strip_suffix(str(vr["stem"]))
        if not gt_views_lookup.get(bs):
            gv = _s(vr.get("gt_views_norm_dir", ""))
            if gv:
                gt_views_lookup[bs] = gv

    manifest: list[dict] = []
    processed_base_stems: set[str] = set()
    done = 0

    for _, row in pdf.iterrows():
        stem = str(row["stem"])
        base_stem = _strip_suffix(str(row.get("base_stem") or stem))
        pipeline_run = _s(row.get("pipeline_run", ""))
        status = _s(row.get("status", ""))

        if not pipeline_run:
            continue

        # Limit by unique base_stems
        if args.limit:
            if base_stem not in processed_base_stems and len(processed_base_stems) >= args.limit:
                continue
            processed_base_stems.add(base_stem)

        # Get paths
        gt_step_path = _s(row.get("gt_step_path", ""))
        cq_code_path = _s(row.get("cq_code_path", ""))
        gen_step_path = _s(row.get("gen_step_path", ""))

        # Pull extra fields from verified_parts if available
        vr = v_lookup.get(stem, {})
        gt_json_path = _s(vr.get("gt_json_path", ""))
        norm_cq_code_path = _s(vr.get("norm_cq_code_path", ""))
        gen_views_norm_dir = _s(vr.get("gen_views_norm_dir", ""))
        gt_views_norm_dir = gt_views_lookup.get(base_stem, "")

        # GT files (once per base_stem)
        gt_entries = _copy_gt(base_stem, gt_step_path, gt_json_path, gt_views_norm_dir, args.dry_run)
        for e in gt_entries:
            manifest.append({"base_stem": base_stem, "stem": base_stem, "pipeline_run": "gt",
                              "status": "gt", **e})

        # Run files
        run_entries = _copy_run(
            stem=stem,
            base_stem=base_stem,
            pipeline_run=pipeline_run,
            status=status,
            cq_code_path=cq_code_path,
            gen_step_path=gen_step_path,
            norm_cq_code_path=norm_cq_code_path,
            gen_views_norm_dir=gen_views_norm_dir,
            dry_run=args.dry_run,
        )
        for e in run_entries:
            manifest.append({"base_stem": base_stem, "stem": stem, "pipeline_run": pipeline_run,
                              "status": status, **e})

        done += 1
        if done % 500 == 0:
            print(f"  processed {done} rows...")

    # Write manifest
    with open(MANIFEST_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(manifest)

    mode = "DRY RUN" if args.dry_run else "ACTUAL"
    print(f"\n[{mode}] processed {done} rows, {len(_gt_done)} base_stems")
    print(f"manifest: {MANIFEST_PATH} ({len(manifest)} entries)")

    # Summary stats
    missing = sum(1 for e in manifest if not e["src_exists"] and e["old_path"])
    copied = sum(1 for e in manifest if e["src_exists"])
    print(f"  src_exists=True: {copied}  src_exists=False: {missing}")


if __name__ == "__main__":
    main()
