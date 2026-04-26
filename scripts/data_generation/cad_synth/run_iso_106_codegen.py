"""Generate ~180k ISO 106-family code samples — copy of run_simple_ops_100k pipeline.

Same phase1 (build + STEP + .py + .json + inline exec validation) but driven
by the 106 ISO families from registry.list_families() instead of simple_ops.

Why: 180k runner.py path does heavy STL tessellation + roundtrip rebuild per
sample, blowing 16GB memory at WORKERS=4. This pipeline:
- Skip STL export
- Skip roundtrip validation (exec-validates the .py instead)
- Same speed as simple_ops (~178/s @ 12 workers)
- Embeds HashCode shim so generated .py runs in fresh Python (OCP 7.9.3)

Output: data/data_generation/iso_106_codegen/{code,step,meta}/

Resume-safe: skips a stem if all 3 of (.py, .step, .json) already exist.
"""

import argparse
import json
import multiprocessing as mp
import os
import signal
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


# Same shim as simple_ops — OCP 7.9.3 removed HashCode, cadquery selectors need it.
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


_FAM = None
_CQ = None
_RENDER_CODE = None


def _phase1_init(root_str: str):
    """Pool initializer for Phase 1 — load all 106 ISO families once per worker."""
    sys.path.insert(0, root_str)
    sys.path.insert(0, str(Path(root_str) / "scripts" / "data_generation"))

    global _FAM, _CQ, _RENDER_CODE
    import cadquery as cq
    from scripts.data_generation.cad_synth.pipeline.builder import render_program_to_code
    from scripts.data_generation.cad_synth.pipeline.registry import (
        get_family,
        list_families,
    )

    _CQ = cq
    _RENDER_CODE = render_program_to_code
    _FAM = {name: get_family(name) for name in list_families()}


def _phase1_worker(args):
    fam_name, params, stem, diff, out_root = args
    out_root = Path(out_root)
    step_path = out_root / "step" / f"{stem}.step"
    py_path = out_root / "code" / f"{stem}.py"
    json_path = out_root / "meta" / f"{stem}.json"

    if step_path.exists() and py_path.exists() and json_path.exists():
        return {"family": fam_name, "stem": stem, "skipped": "phase1_done"}

    try:
        signal.signal(signal.SIGALRM,
                      lambda *a: (_ for _ in ()).throw(TimeoutError("phase1 timeout")))
        signal.alarm(30)

        fam = _FAM[fam_name]
        program = fam.make_program(params)
        program.base_plane = params.get("base_plane", "XY")

        wp = fam.build(params)
        bb = wp.val().BoundingBox()
        if bb.xlen < 0.1 or bb.ylen < 0.1 or bb.zlen < 0.1:
            return {"family": fam_name, "stem": stem,
                    "error": f"degen {bb.xlen:.1f}x{bb.ylen:.1f}x{bb.zlen:.1f}"}

        step_path.parent.mkdir(parents=True, exist_ok=True)
        py_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        _CQ.exporters.export(wp, str(step_path),
                             exportType=_CQ.exporters.ExportTypes.STEP)
        py_src = _HASHCODE_SHIM + _RENDER_CODE(program)
        py_path.write_text(py_src)

        # Exec validation — guarantees the .py actually runs in fresh Python.
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


def _build_args_list(plan, out_root: Path, root_seed: int = 5000):
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


def run_phase1(plan, out_root: Path, n_workers: int = 8):
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
                if done % 500 == 0 or done == total:
                    elapsed = time.time() - t0
                    rate = done / max(elapsed, 1)
                    eta = (total - done) / rate
                    print(f"  [Phase1 {done}/{total}] rate={rate:.1f}/s eta={eta/60:.1f}min")
            else:
                fail_log.append(r)
                if len(fail_log) <= 30 or len(fail_log) % 100 == 0:
                    print(f"  FAIL {r.get('family')}/{r.get('stem')}: {r.get('error')}")

    elapsed = time.time() - t0
    print(f"[Phase 1] Done: {len(results)}/{total} in {elapsed/60:.1f}min, {len(fail_log)} fails")
    (out_root / "phase1_results.json").write_text(json.dumps(results, indent=2, default=str))
    (out_root / "phase1_fails.json").write_text(json.dumps(fail_log, indent=2, default=str))
    return results, fail_log


# Heavy-geometry families that bottleneck throughput (~30s/sample, hit timeout).
# Skip by default; can be re-enabled later with low-worker run.
SKIP_FAMILIES = {
    "sprocket",
    "double_simplex_sprocket",
    "spur_gear",
    "helical_gear",
    "bevel_gear",
    "worm_screw",
}


def build_default_plan(per_family: int):
    from scripts.data_generation.cad_synth.pipeline.registry import (
        get_family,
        list_families,
    )

    return [
        (get_family(name), per_family)
        for name in list_families()
        if name not in SKIP_FAMILIES
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=1700)
    ap.add_argument("--out", default=str(ROOT / "data" / "data_generation" / "iso_106_codegen"))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    plan = build_default_plan(args.per_family)
    n_fam = len(plan)
    total = n_fam * args.per_family
    print(f"Plan: {n_fam} ISO families × {args.per_family} = {total} samples")
    print(f"Out:  {out_root}")

    run_phase1(plan, out_root, n_workers=args.workers)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
