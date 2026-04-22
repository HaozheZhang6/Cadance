"""Main batch runner — Stages A through H.

Parallel execution with per-sample subprocess isolation:
- Main process pre-samples all params (keeps RNG deterministic for resume).
- Each sample runs in an isolated subprocess; SIGKILL on timeout.
- N_WORKERS concurrent subprocesses (configurable via config or --workers).
"""

import argparse
import json
import logging
import multiprocessing as mp
import subprocess
import time
from pathlib import Path

import numpy as np
import yaml

from .exporter import export_sample, log_rejection
from .registry import get_family
from .reporter import build_report, write_report
from .sampler import sample_difficulty, sample_family
from .validator import validate_geometry, validate_realism, validate_roundtrip

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "data" / "data_generation"
logger = logging.getLogger("cad_synth")

MAX_PARAM_RETRIES = 10
BUILD_TIMEOUT_S = 60  # per-sample build budget (seconds)
EXPORT_TIMEOUT_S = 120  # per-sample export+render budget (seconds)
TOTAL_TIMEOUT_S = BUILD_TIMEOUT_S + EXPORT_TIMEOUT_S

# Per-family allowed base planes. Families whose ops use world-Z axes or
# hard-coded selectors break on non-XY planes — restrict to what actually
# produces a correct assembly.
_ALLOWED_PLANES: dict[str, tuple[str, ...]] = {
    # XY-only (revolve/helix/sweep axis is world-fixed, or offsets assume Z=up)
    "pipe_elbow": ("XY",),
    "coil_spring": ("XY",),
    "worm_screw": ("XY",),
    "dome_cap": ("XY",),
    "capsule": ("XY",),
    "torus_link": ("XY",),
    "piston": ("XY",),
    "duct_elbow": ("XY",),
    "bucket": ("XY",),
    "nozzle": ("XY",),
    "bellows": ("XY",),
    "u_bolt": ("XY",),
    "cotter_pin": ("XY",),
    "pan_head_screw": ("XY",),
    "tee_nut": ("XY",),
    "j_hook": ("XY",),
    "gridfinity_bin": ("XY",),
    "phone_stand": ("XY",),
    "eyebolt": ("XY",),
    "torsion_spring": ("XY",),
    "wing_nut": ("XY",),
    "twisted_drill": ("XY",),
    "wall_anchor": ("XY",),
    "battery_holder": ("XY",),
    "hex_key_organizer": ("XY",),
    # partial restrictions
    "grease_nipple": ("YZ", "XZ"),  # XY assembly wrong
    "knob": ("XY", "YZ"),  # XZ assembly wrong
}
_XY_ONLY = {f for f, pl in _ALLOWED_PLANES.items() if pl == ("XY",)}


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _step_exists(stem: str, run_name: str) -> bool:
    p = (
        DATA
        / "generated_data"
        / "fusion360"
        / stem
        / f"verified_{run_name}"
        / "gen.step"
    )
    return p.exists()


# ── Pre-flight: stuck-process detector ────────────────────────────────────────


def _scan_stuck_workers() -> list[tuple[str, str, str]]:
    """Return [(pid, etime, command), ...] for python processes in U state.

    U state = uninterruptible IO wait. SIGKILL doesn't always reach them, and
    they hold OCCT/render memory hostage → swap thrash on next batch launch.
    """
    try:
        out = subprocess.check_output(
            ["ps", "-axo", "pid,stat,etime,command"],
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    stuck = []
    for line in out.splitlines()[1:]:
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, stat, etime, cmd = parts
        if stat.startswith("U") and "python" in cmd:
            stuck.append((pid, etime, cmd))
    return stuck


# ── Worker ────────────────────────────────────────────────────────────────────


def _worker(
    queue: mp.Queue,
    sample_id: int,
    stem: str,
    fam_name: str,
    diff: str,
    params: dict,
    run_name: str,
    render: bool,
) -> None:
    """Runs in a subprocess. Result is put on queue."""
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

        # Stage C: build
        program = family.make_program(params)
        wp = family.build(params)

        result["ops_used"] = [op.name for op in program.ops]
        result["feature_tags"] = program.feature_tags

        # Stage E: geometry validation
        geo_ok, geo_reason = validate_geometry(wp)
        if not geo_ok:
            result["reject_stage"] = "degenerate_geometry"
            result["reject_reason"] = geo_reason
            queue.put(result)
            return

        # Stage F: realism filter
        real_ok, real_reason = validate_realism(program)
        if not real_ok:
            result["reject_stage"] = "realism_filter"
            result["reject_reason"] = real_reason
            queue.put(result)
            return

        # Stage F2: roundtrip check — ensure emitted gt_code re-execs to
        # geometry matching wp (catches families where _apply_op silently
        # succeeded but the string code crashes, or where the two paths
        # diverge in face count).
        rt_ok, rt_reason = validate_roundtrip(program, wp)
        if not rt_ok:
            result["reject_stage"] = "roundtrip_mismatch"
            result["reject_reason"] = rt_reason
            queue.put(result)
            return

        # Stage G: export + render
        code = family.export_code(params)
        export_sample(sample_id, stem, program, wp, code, run_name, render=render)

        result["status"] = "accepted"

    except Exception as e:  # noqa: BLE001
        stage = result.get("reject_stage") or "build_failed"
        result["reject_stage"] = stage
        result["reject_reason"] = str(e)[:200]

    queue.put(result)


# ── Batch orchestrator ─────────────────────────────────────────────────────────


def run_batch(
    config: dict, render: bool = True, resume: bool = False, n_workers: int = 4
) -> dict:
    """Run a full batch. Pre-sample params in main process, dispatch to workers."""
    num_samples = config["num_samples"]
    seed = config.get("seed", 42)
    run_name = config.get("run_name", f"synth_s{seed}")
    family_mix = config["family_mix"]
    difficulty_mix = config["difficulty_mix"]

    rng = np.random.default_rng(seed)

    logger.info(
        "Batch: %d samples, seed=%d, run=%s, workers=%d, resume=%s",
        num_samples,
        seed,
        run_name,
        n_workers,
        resume,
    )

    # ── Stage A+B: pre-sample all params (deterministic, single-threaded) ──
    sample_specs = []
    for i in range(num_samples):
        sample_id = i + 1
        fam_name = sample_family(family_mix, rng)
        diff = sample_difficulty(difficulty_mix, rng)
        stem = f"synth_{fam_name}_{sample_id:06d}_s{seed}"

        params = None
        for _ in range(MAX_PARAM_RETRIES):
            family = get_family(fam_name)
            candidate = family.sample_params(diff, rng)
            if family.validate_params(candidate):
                params = candidate
                break

        if params is not None and "base_plane" not in params:
            allowed = _ALLOWED_PLANES.get(fam_name, ("XY", "YZ", "XZ"))
            params["base_plane"] = (
                allowed[0] if len(allowed) == 1 else str(rng.choice(allowed))
            )

        sample_specs.append(
            {
                "sample_id": sample_id,
                "stem": stem,
                "fam_name": fam_name,
                "diff": diff,
                "params": params,  # None → param_invalid
            }
        )

    logger.info(
        "Pre-sampling done. Dispatching %d samples to %d workers.",
        num_samples,
        n_workers,
    )

    # ── Stages C–G: parallel execution with kill-on-timeout ────────────────
    results = []
    pending = list(sample_specs)
    running: dict[mp.Process, tuple] = {}  # proc → (spec, queue, t_start)

    while pending or running:
        # Launch new workers up to n_workers
        while pending and len(running) < n_workers:
            spec = pending.pop(0)
            sid = spec["sample_id"]

            # param_invalid → no worker needed
            if spec["params"] is None:
                results.append(
                    {
                        "sample_id": sid,
                        "stem": spec["stem"],
                        "family": spec["fam_name"],
                        "difficulty": spec["diff"],
                        "status": "rejected",
                        "reject_stage": "param_invalid",
                        "reject_reason": "exceeded_max_retries",
                        "ops_used": [],
                        "feature_tags": {},
                    }
                )
                log_rejection(
                    sid,
                    spec["stem"],
                    spec["fam_name"],
                    spec["diff"],
                    {},
                    "param_invalid",
                    "exceeded_max_retries",
                    run_name,
                )
                logger.debug("[%d] REJECT param_invalid: %s", sid, spec["stem"])
                continue

            # resume skip
            if resume and _step_exists(spec["stem"], run_name):
                results.append(
                    {
                        "sample_id": sid,
                        "stem": spec["stem"],
                        "family": spec["fam_name"],
                        "difficulty": spec["diff"],
                        "status": "skipped_resume",
                        "reject_stage": "",
                        "reject_reason": "",
                        "ops_used": [],
                        "feature_tags": {},
                    }
                )
                logger.debug("[%d] SKIP (resume) %s", sid, spec["stem"])
                continue

            q = mp.Queue()
            p = mp.Process(
                target=_worker,
                args=(
                    q,
                    sid,
                    spec["stem"],
                    spec["fam_name"],
                    spec["diff"],
                    spec["params"],
                    run_name,
                    render,
                ),
                daemon=True,
            )
            p.start()
            running[p] = (spec, q, time.time())

        # Poll running workers
        for proc in list(running.keys()):
            spec, q, t_start = running[proc]
            sid = spec["sample_id"]
            elapsed = time.time() - t_start

            if not proc.is_alive():
                # Worker finished (success or exception)
                proc.join()
                if not q.empty():
                    res = q.get_nowait()
                else:
                    res = {
                        "sample_id": sid,
                        "stem": spec["stem"],
                        "family": spec["fam_name"],
                        "difficulty": spec["diff"],
                        "status": "rejected",
                        "reject_stage": "worker_crash",
                        "reject_reason": "worker exited without result",
                        "ops_used": [],
                        "feature_tags": {},
                    }
                _log_result(res, run_name, elapsed)
                results.append(res)
                q.close()
                q.join_thread()
                proc.close()
                del running[proc]

            elif elapsed > TOTAL_TIMEOUT_S:
                # Hard kill — handles OCCT infinite loops
                proc.kill()
                proc.join()
                res = {
                    "sample_id": sid,
                    "stem": spec["stem"],
                    "family": spec["fam_name"],
                    "difficulty": spec["diff"],
                    "status": "rejected",
                    "reject_stage": "build_failed",
                    "reject_reason": f"timeout>{TOTAL_TIMEOUT_S}s",
                    "ops_used": [],
                    "feature_tags": {},
                }
                log_rejection(
                    sid,
                    spec["stem"],
                    spec["fam_name"],
                    spec["diff"],
                    spec["params"],
                    "build_failed",
                    f"timeout>{TOTAL_TIMEOUT_S}s",
                    run_name,
                )
                logger.debug(
                    "[%d] REJECT timeout: %s (%.0fs)", sid, spec["stem"], elapsed
                )
                results.append(res)
                q.close()
                q.join_thread()
                proc.close()
                del running[proc]

        if running:
            time.sleep(0.05)

    # Sort by sample_id (parallel completion is out of order)
    results.sort(key=lambda r: r["sample_id"])

    # ── Stage H: report ────────────────────────────────────────────────────
    report = build_report(results)
    report["run_name"] = run_name
    report["seed"] = seed
    report["config"] = config

    report_path = (
        ROOT / "data" / "data_generation" / "synth_reports" / f"{run_name}.json"
    )
    write_report(report, report_path)
    logger.info(
        "Done: %d/%d accepted (%.1f%%). Report: %s",
        report["accepted"],
        report["requested"],
        report["accept_rate"],
        report_path,
    )
    return report


def _log_result(res: dict, run_name: str, elapsed: float) -> None:
    sid = res["sample_id"]
    if res["status"] == "accepted":
        logger.debug("[%d] ACCEPT %s (%.1fs)", sid, res["stem"], elapsed)
    elif res["status"] == "skipped_resume":
        pass
    else:
        stage = res["reject_stage"]
        reason = res["reject_reason"]
        logger.debug("[%d] REJECT %s: %s — %s", sid, stage, res["stem"], reason)
        if stage not in ("param_invalid",):  # already logged before dispatch
            log_rejection(
                sid,
                res["stem"],
                res["family"],
                res["difficulty"],
                {},
                stage,
                reason,
                run_name,
            )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="CadQuery Synthetic Data Harness")
    ap.add_argument("--config", required=True, help="YAML config path")
    ap.add_argument("--no-render", action="store_true", help="Skip rendering")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Skip already-exported stems (RNG still advances deterministically)",
    )
    ap.add_argument(
        "--workers", type=int, default=4, help="Parallel worker processes (default: 4)"
    )
    ap.add_argument(
        "--ignore-stuck",
        action="store_true",
        help="Skip pre-flight U-state python scan (not recommended)",
    )
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.ignore_stuck:
        stuck = _scan_stuck_workers()
        if stuck:
            logger.error(
                "Found %d python process(es) in U (uninterruptible IO) state:",
                len(stuck),
            )
            for pid, etime, cmd in stuck:
                logger.error("  PID %s  age %s  %s", pid, etime, cmd[:120])
            logger.error(
                "These hold memory + push swap → new batch will thrash. "
                "Run `kill -9 %s` first, or pass --ignore-stuck to override.",
                " ".join(p for p, _, _ in stuck),
            )
            raise SystemExit(2)

    config = load_config(args.config)
    n_workers = config.get("n_workers", args.workers)
    if n_workers > 4:
        logger.warning(
            "n_workers=%d is high; 4 is the safe default on this box "
            "(8 workers × ~500MB OCCT can push swap). Override only if "
            "the machine is otherwise idle.",
            n_workers,
        )
    report = run_batch(
        config, render=not args.no_render, resume=args.resume, n_workers=n_workers
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
