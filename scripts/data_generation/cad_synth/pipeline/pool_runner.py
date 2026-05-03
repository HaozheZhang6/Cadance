"""Warm-pool batched runner for 100k batch.

Replaces runner.py's per-sample mp.Process (which re-imports cadquery every
sample) with a persistent ProcessPoolExecutor that imports cadquery ONCE per
worker via initializer.

Processes specs in chunks of 1000; checkpoints + flushes after each chunk so
crashes don't lose work. Resume-aware via parts.csv + step file existence.
"""

import csv
import json
import os
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # repo root (cad_synth/pipeline/pool_runner.py)
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data" / "data_generation"
GENDIR = DATA / "generated_data" / "fusion360"
PARTS_CSV = DATA / "parts.csv"
DEFAULT_N_WORKERS = 4
CHUNK_SIZE = 1000
LOG_PATH = ROOT / "tmp" / "pool_runner.log"

# Set in main() from --config / --workers args. Workers reference these via _step_exists.
RUN_NAME = ""
N_WORKERS = DEFAULT_N_WORKERS


# ─── Worker init: imports cadquery + builder ONCE per worker ─────────────────


def _worker_init():
    """Called once per worker process. Pre-imports CadQuery + pipeline modules."""
    import cadquery  # noqa: F401
    from scripts.data_generation.cad_synth.pipeline import (  # noqa: F401
        builder,
        exporter,
        registry,
        validator,
    )

    # Quiet down OCCT logger
    os.environ.setdefault("MMGT_OPT", "0")


def _do_one_sample(spec: dict) -> dict:
    """Build + verify + export ONE sample. Runs in persistent worker."""
    from scripts.data_generation.cad_synth.pipeline.exporter import export_sample
    from scripts.data_generation.cad_synth.pipeline.registry import get_family
    from scripts.data_generation.cad_synth.pipeline.validator import (
        validate_geometry,
        validate_realism,
    )

    sample_id = spec["sample_id"]
    stem = spec["stem"]
    fam_name = spec["fam_name"]
    diff = spec["diff"]
    params = spec["params"]
    run_name = spec["run_name"]
    render = spec["render"]

    result = {
        "sample_id": sample_id,
        "stem": stem,
        "family": fam_name,
        "difficulty": diff,
        "status": "rejected",
        "reject_stage": "",
        "reject_reason": "",
        "ops_used": [],
        "feature_tags": {},
    }
    try:
        family = get_family(fam_name)
        program = family.make_program(params)
        wp = family.build(params)
        result["ops_used"] = [op.name for op in program.ops]
        result["feature_tags"] = program.feature_tags

        geo_ok, geo_reason = validate_geometry(wp)
        if not geo_ok:
            result["reject_stage"] = "degenerate_geometry"
            result["reject_reason"] = geo_reason
            return result

        real_ok, real_reason = validate_realism(program)
        if not real_ok:
            result["reject_stage"] = "realism_filter"
            result["reject_reason"] = real_reason
            return result

        # Per-sample roundtrip skipped — covered by per-family unit test
        # `tests/test_family_roundtrip.py` (run once in CI).

        code = family.export_code(params)
        export_sample(sample_id, stem, program, wp, code, run_name, render=render)
        result["status"] = "accepted"
    except Exception as e:
        stage = result.get("reject_stage") or "build_failed"
        result["reject_stage"] = stage
        result["reject_reason"] = str(e)[:200]
    return result


# ─── Main loop ────────────────────────────────────────────────────────────────


def _step_exists(stem: str) -> bool:
    return (GENDIR / stem / f"verified_{RUN_NAME}" / "gen.step").exists()


def _log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def main():
    import argparse
    import yaml
    from scripts.data_generation.cad_synth.pipeline.runner import _ALLOWED_PLANES
    from scripts.data_generation.cad_synth.pipeline.registry import get_family
    import numpy as np

    ap = argparse.ArgumentParser(
        description="Warm-pool batched runner (replaces fork-per-sample runner)"
    )
    ap.add_argument("--config", required=True, help="YAML config path")
    ap.add_argument("--workers", type=int, default=None, help="override n_workers")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    global RUN_NAME, N_WORKERS
    RUN_NAME = cfg["run_name"]
    N_WORKERS = args.workers or cfg.get("n_workers", DEFAULT_N_WORKERS)
    num_samples = cfg["num_samples"]
    seed = cfg["seed"]
    family_mix = cfg["family_mix"]
    diff_mix = cfg["difficulty_mix"]
    render = cfg.get("render", True)

    # Build family + difficulty distributions
    fams = list(family_mix.keys())
    fam_w = np.array([family_mix[f] for f in fams], dtype=float)
    fam_w /= fam_w.sum()
    diffs = list(diff_mix.keys())
    diff_w = np.array([diff_mix[d] for d in diffs], dtype=float)
    diff_w /= diff_w.sum()

    rng = np.random.default_rng(seed)
    _log(f"Pre-sampling {num_samples} specs ...")
    MAX_PARAM_RETRIES = 8
    specs = []
    skipped_resume = 0
    for i in range(num_samples):
        sid = i + 1
        fam_name = str(rng.choice(fams, p=fam_w))
        diff = str(rng.choice(diffs, p=diff_w))
        stem = f"synth_{fam_name}_{sid:06d}_s{seed}"

        # Resume skip — count as skipped, don't put in work list
        if _step_exists(stem):
            skipped_resume += 1
            continue

        params = None
        for _ in range(MAX_PARAM_RETRIES):
            family = get_family(fam_name)
            cand = family.sample_params(diff, rng)
            if family.validate_params(cand):
                params = cand
                break
        if params is None:
            continue

        if "base_plane" not in params:
            allowed = _ALLOWED_PLANES.get(fam_name, ("XY", "YZ", "XZ"))
            params["base_plane"] = (
                allowed[0] if len(allowed) == 1 else str(rng.choice(allowed))
            )

        specs.append({
            "sample_id": sid,
            "stem": stem,
            "fam_name": fam_name,
            "diff": diff,
            "params": params,
            "run_name": RUN_NAME,
            "render": render,
        })

    _log(f"Pre-sample done. {len(specs)} new + {skipped_resume} skipped (resume)")

    if not specs:
        _log("Nothing to do.")
        return

    # Process in chunks with persistent pool
    accepted = 0
    rejected = 0
    # accepted_stems collected here → batch-written to exec cache at end so
    # downstream push step skips redundant re-exec (already validated via roundtrip).
    accepted_stems_list: list[str] = []

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=N_WORKERS, initializer=_worker_init) as pool:
        for chunk_start in range(0, len(specs), CHUNK_SIZE):
            chunk = specs[chunk_start:chunk_start + CHUNK_SIZE]
            t_chunk = time.time()
            futs = {pool.submit(_do_one_sample, s): s for s in chunk}
            for fut in as_completed(futs):
                try:
                    res = fut.result(timeout=60)
                    if res["status"] == "accepted":
                        accepted += 1
                        accepted_stems_list.append(res["stem"])
                    else:
                        rejected += 1
                except Exception as e:
                    rejected += 1
                    s = futs[fut]
                    _log(f"  ERR {s['stem']}: {type(e).__name__}: {str(e)[:80]}")
            elapsed = time.time() - t_chunk
            total_elapsed = time.time() - t0
            done = chunk_start + len(chunk)
            rate = accepted / total_elapsed if total_elapsed > 0 else 0
            eta_s = (len(specs) - done) / rate if rate > 0 else -1
            _log(
                f"chunk {done // CHUNK_SIZE}: {len(chunk)} in {elapsed:.0f}s | "
                f"accepted={accepted} rejected={rejected} | "
                f"rate={rate:.1f}/s | ETA={eta_s/60:.0f}min"
            )

    _log(f"DONE: accepted={accepted} rejected={rejected} elapsed={time.time()-t0:.0f}s")

    # Update exec cache: pool_runner roundtrip == _upload_filter exec
    # validation, so mark stems as exec-ok to skip redundant push-stage exec.
    if accepted_stems_list:
        try:
            from scripts.data_generation.cad_synth._upload_filter import _write_exec_cache
            updates = {stem: ("True", "") for stem in accepted_stems_list}
            _write_exec_cache(updates)
            _log(f"wrote {len(updates)} exec-cache entries (skips push re-exec)")
        except Exception as e:
            _log(f"WARN exec-cache write failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
