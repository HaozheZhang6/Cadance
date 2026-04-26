"""Main batch runner — Stages A through H.

Parallel execution with per-sample subprocess isolation:
- Main process pre-samples all params (keeps RNG deterministic for resume).
- Each sample runs in an isolated subprocess; SIGKILL on timeout.
- N_WORKERS concurrent subprocesses (configurable via config or --workers).
"""

import argparse
import hashlib
import json
import logging
import multiprocessing as mp
import subprocess
import time
from pathlib import Path

import numpy as np
import yaml

from ..families.base import scale_params
from .exporter import export_sample, log_rejection
from .registry import get_family
from .reporter import build_report, write_report
from .sampler import sample_difficulty, sample_family
from .validator import validate_geometry, validate_realism, validate_roundtrip


def _param_hash(params: dict) -> str:
    return hashlib.md5(
        json.dumps(params, sort_keys=True, default=str).encode()
    ).hexdigest()


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


def _process_one(
    sample_id: int,
    stem: str,
    fam_name: str,
    diff: str,
    params: dict,
    run_name: str,
    render: bool,
) -> dict:
    """Process a single sample (build → validate → export). Pure compute, no IPC."""
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

        rt_ok, rt_reason = validate_roundtrip(program, wp)
        if not rt_ok:
            result["reject_stage"] = "roundtrip_mismatch"
            result["reject_reason"] = rt_reason
            return result

        code = family.export_code(params)
        export_sample(sample_id, stem, program, wp, code, run_name, render=render)
        result["status"] = "accepted"
    except Exception as e:  # noqa: BLE001
        stage = result.get("reject_stage") or "build_failed"
        result["reject_stage"] = stage
        result["reject_reason"] = str(e)[:200]
    return result


def _worker_loop(in_q: "mp.Queue", out_q: "mp.Queue") -> None:
    """Persistent worker: import cadquery once, then loop on tasks until poison pill."""
    while True:
        try:
            task = in_q.get()
        except (EOFError, OSError):
            return
        if task is None:
            return
        try:
            res = _process_one(*task)
        except Exception as e:  # noqa: BLE001
            sid, stem, fam_name, diff, *_ = task
            res = {
                "sample_id": sid,
                "stem": stem,
                "family": fam_name,
                "difficulty": diff,
                "status": "rejected",
                "reject_stage": "worker_crash",
                "reject_reason": str(e)[:200],
                "ops_used": [],
                "feature_tags": {},
            }
        try:
            out_q.put(res)
        except Exception:  # noqa: BLE001
            return


class _PersistentWorker:
    """One subprocess that processes samples in a loop. Replace on timeout."""

    __slots__ = ("in_q", "out_q", "proc", "busy_spec", "t_start")

    def __init__(self) -> None:
        self._spawn()
        self.busy_spec: dict | None = None
        self.t_start: float = 0.0

    def _spawn(self) -> None:
        self.in_q = mp.Queue()
        self.out_q = mp.Queue()
        self.proc = mp.Process(
            target=_worker_loop, args=(self.in_q, self.out_q), daemon=True
        )
        self.proc.start()

    def submit(self, spec: dict, run_name: str, render: bool) -> None:
        self.in_q.put(
            (
                spec["sample_id"],
                spec["stem"],
                spec["fam_name"],
                spec["diff"],
                spec["params"],
                run_name,
                render,
            )
        )
        self.busy_spec = spec
        self.t_start = time.time()

    def try_collect(self) -> dict | None:
        if self.busy_spec is None:
            return None
        try:
            res = self.out_q.get_nowait()
        except Exception:  # noqa: BLE001 — Empty et al.
            return None
        self.busy_spec = None
        return res

    def is_dead(self) -> bool:
        return not self.proc.is_alive()

    def elapsed(self) -> float:
        return time.time() - self.t_start if self.busy_spec else 0.0

    def kill_and_replace(self) -> None:
        try:
            self.proc.kill()
            self.proc.join(timeout=2)
        except Exception:  # noqa: BLE001
            pass
        self._cleanup_handles()
        self._spawn()
        self.busy_spec = None

    def shutdown(self) -> None:
        try:
            self.in_q.put(None)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.proc.join(timeout=3)
            if self.proc.is_alive():
                self.proc.kill()
                self.proc.join(timeout=2)
        except Exception:  # noqa: BLE001
            pass
        self._cleanup_handles()

    def _cleanup_handles(self) -> None:
        for q in (self.in_q, self.out_q):
            try:
                q.close()
                q.join_thread()
            except Exception:  # noqa: BLE001
                pass
        try:
            self.proc.close()
        except Exception:  # noqa: BLE001
            pass


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
    scale_cfg = config.get("param_scale", {}) or {}
    scale_enabled = bool(scale_cfg.get("enabled", False))
    scale_lo = float(scale_cfg.get("lo", 0.8))
    scale_hi = float(scale_cfg.get("hi", 1.2))
    dedup_enabled = bool(config.get("dedup_params", False))

    rng = np.random.default_rng(seed)

    logger.info(
        "Batch: %d samples, seed=%d, run=%s, workers=%d, resume=%s, scale=%s, dedup=%s",
        num_samples,
        seed,
        run_name,
        n_workers,
        resume,
        f"[{scale_lo},{scale_hi}]" if scale_enabled else "off",
        dedup_enabled,
    )

    seen_param_hashes: set[str] = set()

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
            if scale_enabled:
                candidate = scale_params(candidate, rng, scale_lo, scale_hi)
            if not family.validate_params(candidate):
                continue
            if dedup_enabled:
                h = _param_hash(candidate)
                if h in seen_param_hashes:
                    continue
                seen_param_hashes.add(h)
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

    # ── Stages C–G: persistent worker pool with per-task timeout ──────────
    results = []
    pending = list(sample_specs)
    pool: list[_PersistentWorker] = [_PersistentWorker() for _ in range(n_workers)]

    def _drain_pre_dispatch(spec: dict) -> bool:
        """Handle param_invalid + resume skip in main proc. Returns True if consumed."""
        sid = spec["sample_id"]
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
            return True
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
            return True
        return False

    while pending or any(w.busy_spec is not None for w in pool):
        # Assign pending samples to free workers
        for w in pool:
            while w.busy_spec is None and pending:
                spec = pending.pop(0)
                if _drain_pre_dispatch(spec):
                    continue
                w.submit(spec, run_name, render)
                break

        # Poll workers for completions / timeouts / unexpected death
        for w in pool:
            if w.busy_spec is None:
                continue
            spec = w.busy_spec
            sid = spec["sample_id"]
            elapsed = w.elapsed()

            res = w.try_collect()
            if res is not None:
                _log_result(res, run_name, elapsed)
                results.append(res)
                continue

            if w.is_dead():
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
                log_rejection(
                    sid,
                    spec["stem"],
                    spec["fam_name"],
                    spec["diff"],
                    spec["params"],
                    "worker_crash",
                    "worker exited without result",
                    run_name,
                )
                results.append(res)
                w.kill_and_replace()
                continue

            if elapsed > TOTAL_TIMEOUT_S:
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
                w.kill_and_replace()

        if any(w.busy_spec is not None for w in pool):
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
