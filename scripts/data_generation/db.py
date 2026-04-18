"""Data management helpers for CAD data pipeline.

Source-of-truth files (CSV only — JSONL is archived):
  verified_parts.csv  - primary verified dataset; a row is SFT-ready only when
                        BOTH gt_norm_step_path AND norm_cq_code_path are filled
  parts.csv           - full stem registry from all pipeline runs (running log)
  master.csv          - one row per base_stem; per-stem status overview
  operations.csv      - one row per codegen operation
  runs.csv            - batch run registry

Verified definition (strict):
  iou >= 0.99          vs raw GT STEP         → cq_code_path / gen_step_path
  gt_norm_step_path    normalized GT STEP      → bbox → [-0.5, 0.5]³
  norm_cq_code_path    normalized CQ code      → produces geometry aligned to norm GT
  norm_iou >= 0.95     vs normalized GT STEP   → sft_ready = true
"""

import csv
import datetime
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # repo root
DATA = ROOT / "data" / "data_generation"

VERIFIED_JSONL = DATA / "verified" / "verified_pairs.jsonl"   # archived — do not write
VERIFIED_CSV = DATA / "verified_parts.csv"
PARTS_CSV    = DATA / "parts.csv"
MASTER_CSV   = DATA / "master.csv"
OPS_CSV      = DATA / "operations.csv"
RUNS_CSV     = DATA / "runs.csv"
RETRY_REASONS_CSV = DATA / "retry_reasons.csv"
CV_ARCHIVE   = DATA / "codex_validation_archive"   # old run outputs

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

VERIFIED_FIELDS = [
    "stem",
    "data_source",          # fusion360 | deepcad | synthetic
    "gt_step_path",         # GT STEP (raw, from open_source)
    "gt_norm_step_path",    # GT STEP normalized (bbox→[-0.5,0.5]³)
    "gt_json_path",         # F360 reconstruction JSON / ops JSON
    "ops_program_path",     # descriptive ops program JSON (cut_hole/add_extrude format)
    "gen_step_path",
    "cq_code_path",
    "norm_cq_code_path",    # AST-normalized CQ code (coords → [-0.5,0.5]³)
    "iou",                  # IoU vs raw GT STEP (must be ≥ 0.99)
    "norm_iou",             # IoU of norm_cq output vs gt_norm_step (must be ≥ 0.95)
    "sft_ready",            # true iff gt_norm_step_path + norm_cq_code_path filled + norm_iou≥0.95
    "verified",
    "gt_views_norm_dir",    # normalized GT render dir (268×268)
    "gen_views_norm_dir",   # normalized gen render dir (268×268)
    "pipeline_run",         # pipeline/run that produced this record
    "attempt_id",           # links to parts.csv attempt_id
    "model",                # model used for generation
    "provider",             # openai | anthropic | glm
    "timestamp",
    "visual_verdict",
    "visual_reason",
    "complexity_class",
    "note",
    "fix_source_stem",      # original failed attempt stem; empty for first-try successes
    "bad_cq_path",          # round-1 bad code path for react correction pairs
]

MASTER_FIELDS = [
    "base_stem",
    "data_source",          # fusion360 | deepcad | synthetic
    "gt_step_path",
    "gt_norm_step_path",
    "best_iou",             # best IoU across all runs
    "norm_iou",             # IoU of normalized CQ vs normalized GT
    "status",               # verified | manually_fixed | near_miss | failed | unprocessed
    "sft_ready",            # true iff both norm fields filled + norm_iou≥0.95
    "cq_code_path",
    "norm_cq_code_path",
    "pipeline_run",
    "failure_code",
    "retry_reason",
    "attempt_count",
]

PARTS_FIELDS = [
    "attempt_id",
    "stem",
    "base_stem",
    "pipeline_run",
    "status",
    "iou",
    "gt_vol",
    "provider",
    "model",
    "complexity",
    "gt_step_exists",
    "cq_code_exists",
    "gen_step_exists",
    "gt_views_norm_exists",
    "gen_views_norm_exists",
    "gt_step_path",
    "cq_code_path",
    "gen_step_path",
    "fix_attempts",
    "fix_note",
    "retry_reason",
    "failure_code",  # error classification (dim_error/local_feat, wrong_primitive, …)
    "fixed_stem",    # stem of the verified fix for this attempt, if one exists
    "updated_at",
]

OPS_FIELDS = [
    "op_id",
    "stem",
    "run",
    "op_type",
    "provider",
    "model",
    "result",
    "iou",
    "error_msg",
    "created_at",
]

RUNS_FIELDS = [
    "run",
    "offset",
    "total",
    "passed",
    "near_miss",
    "failed",
    "pass_rate",
    "providers",
    "status",
    "created_at",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    csv.field_size_limit(10 * 1024 * 1024)  # 10 MB — parts.csv has large code fields
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _exists(rel_path) -> str:
    """Return 'true'/'false' string for CSV."""
    if not rel_path or (isinstance(rel_path, float)):
        return "false"
    s = str(rel_path).strip()
    if not s or s == "nan":
        return "false"
    return "true" if (ROOT / s).exists() else "false"


_SIDECAR_COLS = ["stem", "retry_reason", "failure_code", "fixed_stem"]


def _load_sidecar() -> "pd.DataFrame":
    import pandas as pd

    if RETRY_REASONS_CSV.exists():
        rr = pd.read_csv(RETRY_REASONS_CSV)
        for col in _SIDECAR_COLS:
            if col not in rr.columns:
                rr[col] = ""
        return rr[_SIDECAR_COLS].copy()
    return pd.DataFrame(columns=_SIDECAR_COLS)


def _save_sidecar(rr: "pd.DataFrame") -> None:
    RETRY_REASONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    rr[_SIDECAR_COLS].to_csv(RETRY_REASONS_CSV, index=False)


def _save_retry_reason(stem: str, reason: str) -> None:
    _save_annotations(stem, retry_reason=reason)


def _save_annotations(stem: str, **kwargs) -> None:
    """Persist manually-set per-stem annotations to retry_reasons.csv sidecar.

    Supported kwargs: retry_reason, failure_code, fixed_stem.
    Pass value=None to leave existing value unchanged.
    Pass retry_reason="" to remove the stem row if all fields are empty.
    """
    import pandas as pd

    rr = _load_sidecar()
    mask = rr["stem"] == stem
    if mask.any():
        idx = rr.index[mask][0]
        for k, v in kwargs.items():
            if k in _SIDECAR_COLS and v is not None:
                rr.at[idx, k] = v
        # remove row only if retry_reason explicitly cleared and others are empty
        row = rr.loc[idx]
        if not any(str(row[c]) for c in _SIDECAR_COLS[1:] if str(row[c])):
            rr = rr[~mask]
    else:
        new_row: dict = {"stem": stem}
        for col in _SIDECAR_COLS[1:]:
            new_row[col] = kwargs.get(col) or ""
        if any(new_row[c] for c in _SIDECAR_COLS[1:]):
            rr = pd.concat([rr, pd.DataFrame([new_row])], ignore_index=True)
    _save_sidecar(rr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def append_verified(record: dict) -> None:
    """Append one record to verified_parts.csv (source of truth — CSV only).

    Automatically sets sft_ready based on norm fields.
    If record contains 'fix_source_stem', also sets fixed_stem on the source
    attempt in parts.csv so the error→fix pair is bidirectionally linked.
    """
    # Compute sft_ready
    has_norm_gt = bool(record.get("gt_norm_step_path", ""))
    has_norm_cq = bool(record.get("norm_cq_code_path", ""))
    norm_iou_val = float(record.get("norm_iou") or 0)
    record["sft_ready"] = "true" if (has_norm_gt and has_norm_cq and norm_iou_val >= 0.95) else "false"

    # Write to CSV
    VERIFIED_CSV.parent.mkdir(parents=True, exist_ok=True)
    file_exists = VERIFIED_CSV.exists()
    with open(VERIFIED_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VERIFIED_FIELDS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)

    # Sync parts.csv row for the verified stem
    stem = record.get("stem", "")
    if stem:
        update_part_status(
            stem=stem,
            status="verified" if record.get("verified") else "failed",
            iou=record.get("iou"),
        )

    # Link source attempt → this fix (bidirectional)
    source_stem = record.get("fix_source_stem", "") or record.get("source_stem", "")
    if source_stem:
        update_part_status(source_stem, status=None, fixed_stem=stem)


def update_part_status(
    stem: str,
    status: str | None,
    iou: float | None = None,
    fix_note: str | None = None,
    retry_reason: str | None = None,
    failure_code: str | None = None,
    fixed_stem: str | None = None,
) -> None:
    """Update parts.csv row for a stem.

    Pass status=None to update only other fields without touching status.
    """
    rows = _read_csv(PARTS_CSV)
    found = False
    for row in rows:
        if row["stem"] == stem:
            if status is not None:
                row["status"] = status
            if iou is not None:
                row["iou"] = str(round(iou, 6))
            if fix_note is not None:
                row["fix_note"] = fix_note
                row["fix_attempts"] = str(int(row.get("fix_attempts") or 0) + 1)
            if retry_reason is not None:
                row["retry_reason"] = retry_reason
            if failure_code is not None:
                row["failure_code"] = failure_code
            if fixed_stem is not None:
                row["fixed_stem"] = fixed_stem
            row["updated_at"] = _now()
            found = True
            break

    annotations: dict = {}
    if retry_reason is not None:
        annotations["retry_reason"] = retry_reason
    if failure_code is not None:
        annotations["failure_code"] = failure_code
    if fixed_stem is not None:
        annotations["fixed_stem"] = fixed_stem
    if annotations:
        _save_annotations(stem, **annotations)

    if not found:
        rows.append(
            {
                "attempt_id": str(uuid.uuid4()),
                "stem": stem,
                "base_stem": stem,
                "pipeline_run": "",
                "status": status or "",
                "iou": str(round(iou, 6)) if iou is not None else "",
                "gt_vol": "",
                "provider": "",
                "model": "",
                "complexity": "",
                "gt_step_exists": "",
                "cq_code_exists": "",
                "gen_step_exists": "",
                "gt_views_norm_exists": "",
                "gen_views_norm_exists": "",
                "gt_step_path": "",
                "cq_code_path": "",
                "gen_step_path": "",
                "fix_attempts": "0",
                "fix_note": fix_note or "",
                "retry_reason": retry_reason or "",
                "failure_code": failure_code or "",
                "fixed_stem": fixed_stem or "",
                "updated_at": _now(),
            }
        )
    _write_csv(PARTS_CSV, PARTS_FIELDS, rows)


def log_operation(
    stem: str,
    run: str,
    op_type: str,
    provider: str,
    result: str,
    iou: float | None = None,
    error: str | None = None,
    model: str = "",
) -> None:
    """Append one row to operations.csv."""
    OPS_CSV.parent.mkdir(parents=True, exist_ok=True)
    file_exists = OPS_CSV.exists()
    with open(OPS_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OPS_FIELDS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "op_id": str(uuid.uuid4())[:8],
                "stem": stem,
                "run": run,
                "op_type": op_type,
                "provider": provider,
                "model": model,
                "result": result,
                "iou": str(round(iou, 6)) if iou is not None else "",
                "error_msg": error or "",
                "created_at": _now(),
            }
        )


def get_pending_fixes(min_iou: float = 0.75, max_iou: float = 0.99) -> list[dict]:
    """Return near_miss rows from parts.csv sorted by iou desc."""
    rows = _read_csv(PARTS_CSV)
    result = []
    for row in rows:
        if row.get("status") != "near_miss":
            continue
        try:
            iou = float(row["iou"])
        except (ValueError, KeyError):
            continue
        if min_iou <= iou < max_iou:
            result.append(row)
    result.sort(key=lambda r: float(r.get("iou") or 0), reverse=True)
    return result


def summary() -> dict:
    """Return {total, verified, near_miss, failed, manually_fixed} counts."""
    rows = _read_csv(PARTS_CSV)
    counts = {
        "total": len(rows),
        "verified": 0,
        "near_miss": 0,
        "failed": 0,
        "manually_fixed": 0,
        "no_gt": 0,
        "codegen_fail": 0,
    }
    for row in rows:
        s = row.get("status", "")
        if s in counts:
            counts[s] += 1
    return counts


# ---------------------------------------------------------------------------
# CSV build helpers (called by build_csvs.py)
# ---------------------------------------------------------------------------


def _checkpoint_runs() -> list[str]:
    """Return run dirs that have a checkpoint.jsonl (from archive)."""
    if not CV_ARCHIVE.exists():
        return []
    return [
        d.name
        for d in sorted(CV_ARCHIVE.iterdir())
        if d.is_dir() and (d / "checkpoint.jsonl").exists()
    ]


def _infer_offset(run: str) -> int:
    """Infer mesh offset from run name."""
    import re

    m = re.search(r"v(\d+)_n\d+", run)
    if m:
        v = int(m.group(1))
        # v2→0, v3→1000, v4→2000 (v45 maps to 2000), v5→2000, v6→3000, v7→4000, v8→5000
        mapping = {2: 0, 3: 1000, 4: 2000, 5: 2000, 6: 3000, 7: 4000, 8: 5000}
        return mapping.get(v, 0)
    if "retry_v2" in run:
        return 0
    if "retry_v3" in run:
        return 1000
    if "retry_v45" in run or "retry_v4" in run or "retry_v5" in run:
        return 2000
    if "retry_v6" in run:
        return 3000
    return 0


def _checkpoint_status(rec: dict, verified_stems: set) -> str:
    stage = rec.get("stage", "")
    iou = rec.get("iou")
    stem = rec.get("stem", "")

    if stage == "skip_gt_step":
        return "no_gt"
    if stage == "done" and iou is None:
        return "codegen_fail"
    if iou is None:
        return "failed"
    # Check if this stem or its _claude_fixed variant is verified
    fixed_stem = stem + "_claude_fixed"
    if stem in verified_stems or fixed_stem in verified_stems:
        if "_claude_fixed" in stem or fixed_stem in verified_stems:
            return "manually_fixed"
        return "verified"
    if iou >= 0.99:
        return "verified"
    if 0.75 <= iou < 0.99:
        return "near_miss"
    return "failed"


def _build_master() -> None:
    """Build master.csv — one row per base_stem, current status overview."""
    import pandas as pd

    vdf = pd.read_csv(VERIFIED_CSV) if VERIFIED_CSV.exists() else pd.DataFrame(columns=VERIFIED_FIELDS)
    pdf = pd.read_csv(PARTS_CSV)    if PARTS_CSV.exists()    else pd.DataFrame(columns=PARTS_FIELDS)

    def _base(s: str) -> str:
        for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
            if s.endswith(sfx):
                return s[: -len(sfx)]
        return s

    # Best verified row per base_stem
    if not vdf.empty:
        vdf["_base"] = vdf["stem"].astype(str).apply(_base)
        vdf["_iou_f"] = pd.to_numeric(vdf["iou"], errors="coerce").fillna(-1)
        v_best = vdf.sort_values("_iou_f", ascending=False).groupby("_base").first().reset_index()
    else:
        v_best = pd.DataFrame()

    # Best parts row per base_stem (for status + failure_code + retry_reason)
    if not pdf.empty:
        pdf["_iou_f"] = pd.to_numeric(pdf["iou"], errors="coerce").fillna(-1)
        p_best = pdf.sort_values("_iou_f", ascending=False).groupby("base_stem").first().reset_index()
        p_counts = pdf.groupby("base_stem").size().reset_index(name="attempt_count")
    else:
        p_best = pd.DataFrame()
        p_counts = pd.DataFrame()

    # F360 universe
    F360_RECON = ROOT / "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction"
    f360_set = {p.stem for p in F360_RECON.glob("*.json")} if F360_RECON.exists() else set()

    # All known base_stems
    all_bases: set[str] = set(f360_set)
    if not v_best.empty:
        all_bases |= set(v_best["_base"].astype(str))
    if not p_best.empty:
        all_bases |= set(p_best["base_stem"].astype(str))

    v_idx  = {} if v_best.empty else {r["_base"]: r for _, r in v_best.iterrows()}
    p_idx  = {} if p_best.empty else {r["base_stem"]: r for _, r in p_best.iterrows()}
    cnt_idx = {} if p_counts.empty else dict(zip(p_counts["base_stem"], p_counts["attempt_count"]))

    rows = []
    for base in sorted(all_bases):
        vr = v_idx.get(base, {})
        pr = p_idx.get(base, {})

        def _g(d, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None and str(v) not in ("", "nan"):
                    return str(v)
            return ""

        gt_step  = _g(vr, "gt_step_path") or _g(pr, "gt_step_path")
        gt_norm  = _g(vr, "gt_norm_step_path")
        cq_path  = _g(vr, "cq_code_path")
        norm_cq  = _g(vr, "norm_cq_code_path")
        best_iou = _g(vr, "iou") or _g(pr, "iou")
        norm_iou = _g(vr, "norm_iou")
        sft_rdy  = _g(vr, "sft_ready") or "false"
        run      = _g(vr, "pipeline_run") or _g(pr, "pipeline_run")
        status   = _g(pr, "status") or ("verified" if vr else "unprocessed")
        fc       = _g(pr, "failure_code")
        rr       = _g(pr, "retry_reason")
        data_src = _g(vr, "data_source") or ("fusion360" if base in f360_set else "synthetic")

        rows.append({
            "base_stem":        base,
            "data_source":      data_src,
            "gt_step_path":     gt_step,
            "gt_norm_step_path": gt_norm,
            "best_iou":         best_iou,
            "norm_iou":         norm_iou,
            "status":           status,
            "sft_ready":        sft_rdy,
            "cq_code_path":     cq_path,
            "norm_cq_code_path": norm_cq,
            "pipeline_run":     run,
            "failure_code":     fc,
            "retry_reason":     rr,
            "attempt_count":    str(cnt_idx.get(base, "")),
        })

    _write_csv(MASTER_CSV, MASTER_FIELDS, rows)
    sft_n = sum(1 for r in rows if r["sft_ready"] == "true")
    print(f"master.csv: {len(rows)} rows ({sft_n} sft_ready)")


def build_all_csvs() -> None:
    """Rebuild all derived CSVs from source data."""
    _build_verified_parts()
    _build_parts_and_ops()
    _build_runs()
    _build_master()


def _build_verified_parts() -> None:
    """Ensure verified_parts.csv has all schema columns; sort by timestamp desc.

    CSV is the source of truth — this never rebuilds from JSONL.
    """
    import pandas as pd

    if not VERIFIED_CSV.exists():
        print("verified_parts.csv: missing, nothing to do")
        return
    df = pd.read_csv(VERIFIED_CSV)
    # Add any missing columns introduced by schema updates
    for col in VERIFIED_FIELDS:
        if col not in df.columns:
            df[col] = ""
    # Reorder columns to match schema
    df = df[VERIFIED_FIELDS]
    # Compute sft_ready for all rows
    df["sft_ready"] = (
        df["gt_norm_step_path"].notna() & (df["gt_norm_step_path"] != "") &
        df["norm_cq_code_path"].notna() & (df["norm_cq_code_path"] != "") &
        pd.to_numeric(df["norm_iou"], errors="coerce").fillna(0).ge(0.95)
    ).map({True: "true", False: "false"})
    df = df.sort_values("timestamp", ascending=False, na_position="last")
    df.to_csv(VERIFIED_CSV, index=False)
    sft_n = (df["sft_ready"] == "true").sum()
    print(f"verified_parts.csv: {len(df)} rows ({sft_n} sft_ready)")


def _build_parts_and_ops() -> None:
    """Build parts.csv and operations.csv from all checkpoint.jsonl files.

    parts.csv is a running log — one row per (stem, run) attempt, with a
    deterministic attempt_id = uuid5(NAMESPACE_DNS, "<stem>:<run>").
    """
    # Load verified stems for status classification
    import pandas as pd
    verified_stems: set[str] = set()
    if VERIFIED_CSV.exists():
        _vdf = pd.read_csv(VERIFIED_CSV)
        verified_stems = set(_vdf["stem"].astype(str))

    # All attempt rows (one per checkpoint entry), no dedup
    all_rows: list[dict] = []
    ops_rows: list[dict] = []

    runs = _checkpoint_runs()
    for run in runs:
        cp_path = CV_ARCHIVE / run / "checkpoint.jsonl"
        cp_mtime = datetime.datetime.utcfromtimestamp(cp_path.stat().st_mtime).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        # load report for model/provider
        report_path = CV_ARCHIVE / run / "validation_report.json"
        report: dict = {}
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)

        model = report.get("model", "")
        provider = report.get("provider", "")

        with open(cp_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                stem = rec.get("stem", "")
                if not stem:
                    continue

                iou_val = rec.get("iou")
                iou_f = float(iou_val) if iou_val is not None else -1.0
                status = _checkpoint_status(rec, verified_stems)
                prov = rec.get("provider_used") or rec.get("provider") or provider

                _base = stem.replace("_claude_fixed", "").replace("_copy_gt", "").replace("_manual_fix", "")
                _run_folder = f"verified_{run}" if stem in verified_stems else run
                _gfs = "data/data_generation/generated_data/fusion360"
                cq_path = f"{_gfs}/{_base}/{_run_folder}/cq.py"
                gen_path = f"{_gfs}/{_base}/{_run_folder}/gen.step"
                attempt_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{stem}:{run}"))

                row = {
                    "attempt_id": attempt_id,
                    "stem": stem,
                    "base_stem": stem.replace("_claude_fixed", ""),
                    "pipeline_run": run,
                    "status": status,
                    "iou": str(round(iou_f, 6)) if iou_f >= 0 else "",
                    "gt_vol": str(rec.get("gt_vol", "")),
                    "provider": prov,
                    "model": model,
                    "complexity": rec.get("complexity", ""),
                    "gt_step_exists": "",
                    "cq_code_exists": _exists(cq_path),
                    "gen_step_exists": _exists(gen_path),
                    "gt_views_norm_exists": "",
                    "gen_views_norm_exists": "",
                    "gt_step_path": "",
                    "cq_code_path": cq_path,
                    "gen_step_path": gen_path,
                    "fix_attempts": "0",
                    "fix_note": "",
                    "retry_reason": "",
                    "failure_code": "",
                    "fixed_stem": "",
                    "updated_at": cp_mtime,
                }
                all_rows.append(row)

                # operations log
                if rec.get("stage") == "skip_gt_step":
                    result = "no_gt"
                elif iou_f >= 0.99:
                    result = "verified"
                elif 0.75 <= iou_f < 0.99:
                    result = "near_miss"
                else:
                    result = "fail"

                ops_rows.append(
                    {
                        "op_id": "",  # filled below
                        "stem": stem,
                        "run": run,
                        "op_type": "auto_codegen",
                        "provider": prov,
                        "model": model,
                        "result": result,
                        "iou": str(round(iou_f, 6)) if iou_f >= 0 else "",
                        "error_msg": rec.get("error_type", ""),
                        "created_at": cp_mtime,
                    }
                )

    # Enrich parts with gt_step_path / views from verified_parts.csv
    stem_to_verified: dict[str, dict] = {}
    if VERIFIED_CSV.exists():
        _vdf2 = pd.read_csv(VERIFIED_CSV)
        for _, r in _vdf2.iterrows():
            rd = r.to_dict()
            s = str(rd.get("stem", ""))
            if s:
                stem_to_verified[s] = rd
            bs = s
            for sfx in ("_claude_fixed", "_copy_gt", "_manual_fix"):
                if bs.endswith(sfx):
                    bs = bs[:-len(sfx)]
                    break
            if bs and bs not in stem_to_verified:
                stem_to_verified[bs] = rd

    # Apply verified enrichment to all checkpoint rows
    for row in all_rows:
        stem = row["stem"]
        vr = stem_to_verified.get(stem) or stem_to_verified.get(
            row.get("base_stem", stem), {}
        )
        gt_path = vr.get("gt_step_path", "")
        gt_views = vr.get("gt_views_norm_dir", "")
        gen_views = vr.get("gen_views_norm_dir", "")
        row["gt_step_path"] = gt_path
        row["gt_step_exists"] = _exists(gt_path)
        row["gt_views_norm_exists"] = _exists(gt_views) if gt_views else "false"
        row["gen_views_norm_exists"] = _exists(gen_views) if gen_views else "false"

    # Add stems that are only in verified_pairs (not in any checkpoint)
    cp_stems = {row["stem"] for row in all_rows}
    for stem, vr in stem_to_verified.items():
        if stem in cp_stems:
            continue
        iou_val = vr.get("iou")
        iou_f = float(iou_val) if iou_val is not None else -1.0
        status = _checkpoint_status(
            {"stage": "done", "iou": iou_val, "ok": True, "stem": stem},
            verified_stems,
        )
        gt_path = vr.get("gt_step_path", "")
        cq_path = vr.get("cq_code_path", "")
        gen_path = vr.get("gen_step_path", "")
        gt_views = vr.get("gt_views_norm_dir", "")
        gen_views = vr.get("gen_views_norm_dir", "")
        pipeline_run = vr.get("pipeline_run", "")
        attempt_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{stem}:{pipeline_run}"))
        all_rows.append(
            {
                "attempt_id": attempt_id,
                "stem": stem,
                "base_stem": vr.get("base_stem", stem),
                "pipeline_run": pipeline_run,
                "status": status,
                "iou": str(round(iou_f, 6)) if iou_f >= 0 else "",
                "gt_vol": str(vr.get("gt_vol", "")),
                "provider": vr.get("provider", ""),
                "model": vr.get("model", ""),
                "complexity": vr.get("complexity_class", ""),
                "gt_step_exists": _exists(gt_path),
                "cq_code_exists": _exists(cq_path),
                "gen_step_exists": _exists(gen_path),
                "gt_views_norm_exists": _exists(gt_views) if gt_views else "false",
                "gen_views_norm_exists": _exists(gen_views) if gen_views else "false",
                "gt_step_path": gt_path,
                "cq_code_path": cq_path,
                "gen_step_path": gen_path,
                "fix_attempts": "0",
                "fix_note": "",
                "retry_reason": "",
                "failure_code": "",
                "fixed_stem": "",
                "updated_at": vr.get("timestamp", ""),
            }
        )

    # Sort: stem then run for stable output
    all_rows.sort(key=lambda r: (r["stem"], r["pipeline_run"]))

    # Assign op_ids sequentially
    for i, row in enumerate(ops_rows):
        row["op_id"] = f"op{i+1:06d}"

    # Merge persisted sidecar annotations (retry_reason, failure_code, fixed_stem)
    if RETRY_REASONS_CSV.exists():
        import pandas as pd

        rr = _load_sidecar()
        for col in ("retry_reason", "failure_code", "fixed_stem"):
            col_map = dict(zip(rr["stem"], rr[col].fillna("")))
            for row in all_rows:
                v = col_map.get(row["stem"], "")
                if v:
                    row[col] = str(v)

    _write_csv(PARTS_CSV, PARTS_FIELDS, all_rows)
    print(f"parts.csv: {len(all_rows)} rows")

    _write_csv(OPS_CSV, OPS_FIELDS, ops_rows)
    print(f"operations.csv: {len(ops_rows)} rows")


def _build_runs() -> None:
    """Build runs.csv from validation_report.json files + checkpoint stats."""
    runs_rows: list[dict] = []
    runs = _checkpoint_runs()

    for run in runs:
        cp_path = CV_ARCHIVE / run / "checkpoint.jsonl"
        report_path = CV_ARCHIVE / run / "validation_report.json"

        report: dict = {}
        if report_path.exists():
            with open(report_path) as f:
                report = json.load(f)

        # Count from checkpoint
        total = near_miss = passed = failed = 0
        providers: set[str] = set()
        with open(cp_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("stage") == "skip_gt_step":
                    continue
                total += 1
                iou_val = rec.get("iou")
                prov = rec.get("provider_used") or rec.get("provider", "")
                if prov:
                    providers.add(prov)
                if iou_val is None:
                    failed += 1
                    continue
                iou_f = float(iou_val)
                if iou_f >= 0.99:
                    passed += 1
                elif iou_f >= 0.75:
                    near_miss += 1
                else:
                    failed += 1

        pass_rate = f"{passed/total:.3f}" if total else "0.000"
        offset = report.get("offset", _infer_offset(run))
        created_at = report.get("date", "")
        if not created_at:
            created_at = datetime.datetime.utcfromtimestamp(
                cp_path.stat().st_mtime
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # status: complete if all done, partial if some still in codegen/execute stage
        with open(cp_path) as f:
            in_progress = any(
                json.loads(line).get("stage") not in ("done", "skip_gt_step", None)
                for line in f
                if line.strip()
            )
        status = "partial" if in_progress else "complete"

        runs_rows.append(
            {
                "run": run,
                "offset": offset,
                "total": total,
                "passed": passed,
                "near_miss": near_miss,
                "failed": failed,
                "pass_rate": pass_rate,
                "providers": "|".join(sorted(providers)),
                "status": status,
                "created_at": created_at,
            }
        )

    _write_csv(RUNS_CSV, RUNS_FIELDS, runs_rows)
    print(f"runs.csv: {len(runs_rows)} rows")


if __name__ == "__main__":
    build_all_csvs()
