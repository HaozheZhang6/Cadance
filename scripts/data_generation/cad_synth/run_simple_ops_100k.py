"""Generate 100k simple_ops samples — two-phase parallel build + serial render.

Phase 1 (parallel, mp.Pool, 12 worker): for each (family, params, stem):
    sample_params -> validate -> build wp -> bbox check -> exportStep ->
    render_program_to_code -> .py -> serialize Op program -> .json
    All artifacts on disk; no rendering yet.

Phase 2 (serial in-process): for each STEP file with no composite:
    render_step_normalized -> 4 view PNGs + composite.png
    Wrapped in SIGALRM(45s) so OCCT/VTK stalls auto-skip.

Resume-safe: skipping anything where (.py + .json + .step) all exist for
phase 1, or composite.png exists for phase 2.
"""

import argparse
import json
import multiprocessing as mp
import os
import signal
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


# Prepended to every generated .py so exec works in plain Python (OCP 7.9.3
# removed HashCode but cadquery's face/edge selectors still call it).
_HASHCODE_SHIM = '''\
# --- OCP HashCode shim (OCP 7.9.3 removed HashCode; cadquery selectors need it) ---
from OCP.TopoDS import (TopoDS_Compound, TopoDS_CompSolid, TopoDS_Edge, TopoDS_Face,
                        TopoDS_Shape, TopoDS_Shell, TopoDS_Solid, TopoDS_Vertex, TopoDS_Wire)
for _cls in (TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex, TopoDS_Wire,
             TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid):
    if not hasattr(_cls, "HashCode"):
        _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
# --- end shim ---
'''


# --- list of family classes -------------------------------------------------


def _all_family_classes():
    """Return list of all SimpleXxxFamily classes — keep here so worker sees them."""
    from scripts.data_generation.cad_synth.families import simple_ops as so
    import inspect

    classes = []
    for name, cls in inspect.getmembers(so, inspect.isclass):
        if not name.startswith("Simple") or not name.endswith("Family"):
            continue
        # Skip mirror (deprecated) and known-broken families.
        if name in ("SimpleMirrorFamily", "SimpleSweepHelixFilletFamily"):
            continue
        classes.append(cls)
    return classes


# --- phase 1: parallel build + STEP + .py + .json ---------------------------


_FAM = None  # populated by _phase1_init


def _phase1_init(root_str: str):
    """Pool initializer for Phase 1."""
    sys.path.insert(0, root_str)
    sys.path.insert(0, str(Path(root_str) / "scripts" / "data_generation"))

    global _FAM, _CQ, _RENDER_CODE
    import cadquery as cq
    from scripts.data_generation.cad_synth.pipeline.builder import render_program_to_code

    _CQ = cq
    _RENDER_CODE = render_program_to_code
    _FAM = {cls().name: cls() for cls in _all_family_classes()}


def _phase1_worker(args):
    """Build wp, write STEP + .py + .json. Returns metadata dict."""
    fam_name, params, stem, diff, out_root = args
    out_root = Path(out_root)
    step_path = out_root / "step" / f"{stem}.step"
    py_path = out_root / "code" / f"{stem}.py"
    json_path = out_root / "meta" / f"{stem}.json"

    # Resume: if all 3 exist, skip.
    if step_path.exists() and py_path.exists() and json_path.exists():
        return {"family": fam_name, "stem": stem, "skipped": "phase1_done"}

    try:
        signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TimeoutError("phase1 timeout")))
        signal.alarm(30)

        fam = _FAM[fam_name]
        program = fam.make_program(params)
        program.base_plane = params.get("base_plane", "XY")

        wp = fam.build(params)
        solid = wp.val()
        bb = solid.BoundingBox()
        if bb.xlen < 0.1 or bb.ylen < 0.1 or bb.zlen < 0.1:
            return {"family": fam_name, "stem": stem,
                    "error": f"degen {bb.xlen:.1f}x{bb.ylen:.1f}x{bb.zlen:.1f}"}

        step_path.parent.mkdir(parents=True, exist_ok=True)
        py_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        _CQ.exporters.export(wp, str(step_path),
                             exportType=_CQ.exporters.ExportTypes.STEP)
        py_src = _RENDER_CODE(program)
        # Prepend HashCode shim — OCP 7.9.3 removed HashCode but cadquery's
        # face/edge selectors call it. Without this, exec'd .py crashes.
        py_src = _HASHCODE_SHIM + py_src
        py_path.write_text(py_src)

        # Validate the .py actually exec's and produces a valid bbox.
        ns = {"show_object": lambda *a, **kw: None}
        try:
            exec(compile(py_src, str(py_path), "exec"), ns)
            r = ns.get("result")
            if r is None:
                raise RuntimeError("no 'result' var")
            r_bb = r.val().BoundingBox()
            if r_bb.xlen < 0.1 or r_bb.ylen < 0.1 or r_bb.zlen < 0.1:
                raise RuntimeError(f"py-exec degen {r_bb.xlen:.1f}x{r_bb.ylen:.1f}x{r_bb.zlen:.1f}")
        except Exception as e:
            # Roll back artifacts so this stem is not counted as completed.
            for f in (step_path, py_path, json_path):
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
            return {"family": fam_name, "stem": stem,
                    "error": f"py-exec: {type(e).__name__}: {str(e)[:140]}"}

        prog_json = {
            "family": program.family,
            "difficulty": program.difficulty,
            "diff_label": diff,
            "params": program.params,
            "ops": [{"name": o.name, "args": o.args} for o in program.ops],
            "feature_tags": program.feature_tags,
            "base_plane": program.base_plane,
            "bbox": [bb.xlen, bb.ylen, bb.zlen],
        }
        json_path.write_text(json.dumps(prog_json, indent=2, default=str))

        signal.alarm(0)
        return {"family": fam_name, "stem": stem,
                "step": str(step_path), "py": str(py_path), "meta": str(json_path)}
    except TimeoutError:
        return {"family": fam_name, "stem": stem, "error": "phase1 timeout"}
    except Exception as e:
        return {"family": fam_name, "stem": stem,
                "error": f"{type(e).__name__}: {str(e)[:160]}"}
    finally:
        signal.alarm(0)


def _build_args_list(plan, out_root: Path, root_seed: int = 42):
    """Sample params upfront; return list of phase1 args + skip_log."""
    args_list = []
    skip_log = []
    seed = root_seed
    for fam, n in plan:
        rng = np.random.default_rng(seed)
        seed += 1
        got = 0
        attempts = 0
        max_attempts = n * 6
        while got < n and attempts < max_attempts:
            attempts += 1
            diff = ["easy", "medium", "hard"][attempts % 3]
            try:
                params = fam.sample_params(diff, rng)
                if not fam.validate_params(params):
                    continue
            except Exception as e:
                skip_log.append({"family": fam.name, "error": f"sample: {e}"})
                continue
            stem = f"{fam.name}_{got:05d}"
            args_list.append((fam.name, params, stem, diff, str(out_root)))
            got += 1
        if got < n:
            skip_log.append({"family": fam.name, "got": got, "needed": n,
                             "shortfall": n - got})
    return args_list, skip_log


def run_phase1(plan, out_root: Path, n_workers: int = 12):
    """Phase 1: parallel build + STEP + .py + .json."""
    print(f"[Phase 1] Building args ...")
    t0 = time.time()
    args_list, skip_log = _build_args_list(plan, out_root)
    total = len(args_list)
    print(f"[Phase 1] {total} samples, {n_workers} workers")

    results = []
    fail_log = list(skip_log)
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=n_workers, initializer=_phase1_init,
                  initargs=(str(ROOT),)) as pool:
        for i, r in enumerate(pool.imap_unordered(_phase1_worker, args_list, chunksize=4)):
            done = i + 1
            if "step" in r or r.get("skipped"):
                results.append(r)
                if done % 200 == 0 or done == total:
                    elapsed = time.time() - t0
                    rate = done / max(elapsed, 1)
                    eta = (total - done) / rate
                    print(f"  [Phase1 {done}/{total}] rate={rate:.1f}/s eta={eta/60:.1f}min")
            else:
                fail_log.append(r)
                if len(fail_log) <= 20 or len(fail_log) % 50 == 0:
                    print(f"  FAIL {r.get('family')}/{r.get('stem')}: {r.get('error')}")

    elapsed = time.time() - t0
    print(f"[Phase 1] Done: {len(results)}/{total} in {elapsed/60:.1f}min, {len(fail_log)} fails")
    (out_root / "phase1_results.json").write_text(json.dumps(results, indent=2, default=str))
    (out_root / "phase1_fails.json").write_text(json.dumps(fail_log, indent=2, default=str))
    return results, fail_log


# --- phase 2: serial render ------------------------------------------------


def _spawn_render_worker():
    """Spawn the persistent _render_worker subprocess and wait for READY."""
    import select
    import subprocess

    worker_py = ROOT / "scripts" / "data_generation" / "cad_synth" / "_render_worker.py"
    env = {**os.environ}
    proc = subprocess.Popen(
        [sys.executable, "-u", str(worker_py)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, env=env, bufsize=1,
    )
    # Wait up to 30s for READY signal — VTK + cadquery import is slow.
    ready_in, _, _ = select.select([proc.stdout], [], [], 30.0)
    if not ready_in:
        proc.kill()
        raise RuntimeError("render worker did not become READY in 30s")
    line = proc.stdout.readline().strip()
    if line != "READY":
        proc.kill()
        raise RuntimeError(f"render worker bad first line: {line!r}")
    return proc


def run_phase2(out_root: Path, timeout_s: int = 45):
    """Phase 2: render via persistent subprocess with hard-kill watchdog.

    Why subprocess: VTK/OCCT can deadlock in OS U-state where SIGALRM is
    silently ignored. SIGKILL on the subprocess bypasses U-state.
    """
    import select
    import subprocess

    step_dir = out_root / "step"
    png_root = out_root / "png"
    pending = []
    for step_path in sorted(step_dir.glob("*.step")):
        stem = step_path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        fam_name = parts[0]
        png_dir = png_root / fam_name
        if (png_dir / f"{stem}_composite.png").exists():
            continue
        pending.append((step_path, png_dir, stem))

    total = len(pending)
    print(f"[Phase 2] {total} STEPs need rendering (rest already done)")
    t0 = time.time()
    ok = 0
    fail = 0
    fails = []

    proc = _spawn_render_worker()
    print(f"[Phase 2] worker pid={proc.pid} ready, timeout={timeout_s}s")

    for i, (step_path, png_dir, stem) in enumerate(pending):
        png_dir.mkdir(parents=True, exist_ok=True)
        if proc is None or proc.poll() is not None:
            proc = _spawn_render_worker()
            print(f"  [Phase2] respawned worker pid={proc.pid}")
        try:
            proc.stdin.write(f"{step_path}|{png_dir}|{stem}\n")
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            proc.kill()
            proc = _spawn_render_worker()
            try:
                proc.stdin.write(f"{step_path}|{png_dir}|{stem}\n")
                proc.stdin.flush()
            except Exception as e:
                fail += 1
                fails.append({"stem": stem, "error": f"feed: {e}"})
                continue

        # Watchdog read with timeout — if no response, SIGKILL the worker.
        ready, _, _ = select.select([proc.stdout], [], [], timeout_s)
        if not ready:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
            fail += 1
            fails.append({"stem": stem, "error": f"TIMEOUT >{timeout_s}s (killed)"})
            proc = _spawn_render_worker()
        else:
            line = proc.stdout.readline().strip()
            if line.startswith("OK|"):
                ok += 1
            else:
                fail += 1
                parts = line.split("|", 2)
                err = parts[2] if len(parts) >= 3 else line
                fails.append({"stem": stem, "error": err})

        done = i + 1
        if done % 25 == 0 or done == total:
            elapsed = time.time() - t0
            rate = done / max(elapsed, 1)
            eta = (total - done) / rate if rate > 0 else 0
            print(f"  [Phase2 {done}/{total}] ok={ok} fail={fail} "
                  f"rate={rate:.2f}/s eta={eta/60:.1f}min")

    if proc and proc.poll() is None:
        try:
            proc.stdin.write("EXIT\n")
            proc.stdin.flush()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    elapsed = time.time() - t0
    print(f"[Phase 2] Done in {elapsed/60:.1f}min: ok={ok} fail={fail}")
    (out_root / "phase2_fails.json").write_text(json.dumps(fails, indent=2, default=str))
    return ok, fail


# --- main -------------------------------------------------------------------


def build_default_plan(per_family: int):
    classes = _all_family_classes()
    return [(cls(), per_family) for cls in classes]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=1700)
    ap.add_argument("--out", default=str(ROOT / "data" / "data_generation" / "simple_ops_100k"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--phase", default="all", choices=["all", "build", "render"])
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    plan = build_default_plan(args.per_family)
    n_fam = len(plan)
    total = n_fam * args.per_family
    print(f"Plan: {n_fam} families × {args.per_family} = {total} samples")
    print(f"Out:  {out_root}")

    if args.phase in ("all", "build"):
        run_phase1(plan, out_root, n_workers=args.workers)
    if args.phase in ("all", "render"):
        run_phase2(out_root)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
