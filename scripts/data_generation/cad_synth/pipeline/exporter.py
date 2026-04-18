"""Export accepted samples: code.py, mesh.stl, renders, meta.json, CSV row."""

import csv
import datetime
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # repo root
DATA = ROOT / "data" / "data_generation"
SYNTH_CSV = DATA / "synth_parts.csv"

SYNTH_FIELDS = [
    "gid",  # global monotonic row ID (unique across all runs)
    "sample_id",
    "stem",
    "family",
    "variant",
    "difficulty",
    "base_plane",  # "XY" | "XZ" | "YZ" — starting workplane for this sample
    "ops_used",
    "feature_tags",
    "params_json",
    "standard",  # ISO/DIN/ASME standard, e.g. "DIN 950", "ISO 4032", "N/A"
    "status",
    "reject_stage",
    "reject_reason",
    "code_path",
    "step_path",
    "render_dir",
    "meta_path",
    "pipeline_run",
    "sample_type",  # "production" | "test"
    "created_at",
]

# Run names that are test/smoke/verification runs, not production batches
_PREFLIGHT_KEYWORDS = ("smoke", "test", "fix", "preflight", "debug")


def _classify_run(run_name: str) -> str:
    """Return 'test' if this is a smoke/preflight run, else 'production'."""
    rn = (run_name or "").lower()
    return "test" if any(kw in rn for kw in _PREFLIGHT_KEYWORDS) else "production"


def _next_gid() -> int:
    """Return the next global row ID (1-based sequential across all rows)."""
    if not SYNTH_CSV.exists():
        return 1
    with open(SYNTH_CSV) as f:
        n_rows = sum(1 for _ in f) - 1  # subtract header line
    return max(1, n_rows + 1)


def _ensure_csv_header():
    """Write header if CSV does not exist."""
    SYNTH_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not SYNTH_CSV.exists():
        with open(SYNTH_CSV, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=SYNTH_FIELDS).writeheader()


def export_sample(
    sample_id: int,
    stem: str,
    program,
    wp,
    code: str,
    run_name: str,
    render: bool = True,
) -> dict:
    """Write all artifacts for an accepted sample. Returns meta dict."""
    sample_dir = DATA / "generated_data" / "fusion360" / stem / f"verified_{run_name}"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # code.py
    code_path = sample_dir / "code.py"
    code_path.write_text(code)

    # STEP export
    step_path = sample_dir / "gen.step"
    import cadquery as cq

    cq.exporters.export(wp, str(step_path), exportType=cq.exporters.ExportTypes.STEP)

    # GT STEP = gen STEP (same file, IoU=1.0)
    gt_dir = DATA / "generated_data" / "fusion360" / stem / "gt"
    gt_dir.mkdir(parents=True, exist_ok=True)
    gt_step = gt_dir / "gt.step"
    shutil.copy2(step_path, gt_step)

    # STL export
    stl_path = sample_dir / "mesh.stl"
    cq.exporters.export(wp, str(stl_path), exportType=cq.exporters.ExportTypes.STL)

    # Renders
    render_paths = {}
    if render:
        try:
            import sys

            sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))
            from render_normalized_views import render_step_normalized

            view_dir = sample_dir / "views"
            result = render_step_normalized(str(step_path), str(view_dir))
            # Copy to render_N.png
            view_names = ["front", "right", "top", "iso"]
            for i in range(4):
                src = view_dir / f"view_{i}.png"
                dst = sample_dir / f"render_{i}.png"
                if src.exists():
                    shutil.copy2(src, dst)
                    render_paths[f"render_{i}"] = str(dst.relative_to(ROOT))
        except Exception as e:
            render_paths["error"] = str(e)

    # meta.json
    ops_used = [op.name for op in program.ops]

    from .qa_generator import get_qa_and_iso

    qa_pairs, iso_tags = get_qa_and_iso(program.family, program.params)

    meta = {
        "sample_id": f"sample_{sample_id:06d}",
        "stem": stem,
        "family": program.family,
        "difficulty": program.difficulty,
        "ops_used": ops_used,
        "feature_tags": program.feature_tags,
        "params": program.params,
        "qa_pairs": qa_pairs,
        "iso_tags": iso_tags,
        "artifacts": {
            "code": "code.py",
            "mesh": "mesh.stl",
            "step": "gen.step",
            "renders": [f"render_{i}.png" for i in range(4)],
        },
    }
    meta_path = sample_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, default=str))

    # CSV row
    _ensure_csv_header()
    from .registry import get_family as _get_family

    _fam_cls = _get_family(program.family)
    row = {
        "gid": _next_gid(),
        "sample_id": f"sample_{sample_id:06d}",
        "stem": stem,
        "family": program.family,
        "variant": program.params.get("variant", "standard"),
        "difficulty": program.difficulty,
        "base_plane": program.params.get("base_plane", "XY"),
        "ops_used": json.dumps(ops_used),
        "feature_tags": json.dumps(program.feature_tags),
        "params_json": json.dumps(program.params, default=str),
        "standard": getattr(_fam_cls, "standard", "N/A"),
        "status": "accepted",
        "reject_stage": "",
        "reject_reason": "",
        "code_path": str(code_path.relative_to(ROOT)),
        "step_path": str(step_path.relative_to(ROOT)),
        "render_dir": str((sample_dir / "views").relative_to(ROOT)),
        "meta_path": str(meta_path.relative_to(ROOT)),
        "pipeline_run": run_name,
        "sample_type": _classify_run(run_name),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(SYNTH_CSV, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=SYNTH_FIELDS, extrasaction="ignore").writerow(row)

    return meta


def log_rejection(
    sample_id: int,
    stem: str,
    family: str,
    difficulty: str,
    params: dict,
    stage: str,
    reason: str,
    run_name: str,
):
    """Log a rejected sample to synth_parts.csv."""
    from .registry import get_family as _get_family

    _ensure_csv_header()
    row = {
        "gid": _next_gid(),
        "sample_id": f"sample_{sample_id:06d}",
        "stem": stem,
        "family": family,
        "variant": params.get("variant", "standard"),
        "difficulty": difficulty,
        "base_plane": params.get("base_plane", "XY"),
        "ops_used": "",
        "feature_tags": "",
        "params_json": json.dumps(params, default=str),
        "standard": getattr(_get_family(family), "standard", "N/A"),
        "status": "rejected",
        "reject_stage": stage,
        "reject_reason": reason,
        "code_path": "",
        "step_path": "",
        "render_dir": "",
        "meta_path": "",
        "pipeline_run": run_name,
        "sample_type": _classify_run(run_name),
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(SYNTH_CSV, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=SYNTH_FIELDS, extrasaction="ignore").writerow(row)
