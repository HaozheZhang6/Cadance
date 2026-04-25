"""Edit-code bench — code-only edit (model sees orig CQ code + NL instruction).

Results land in `results/edit_code/<model>/`, dedup by record_id across runs.

Usage (zero-setup, HF):
    python -m bench.edit_gen.run_edit_code --model gpt-4o --limit 20 --seed 42

Usage (local bench dir):
    python -m bench.edit_gen.run_edit_code --model gpt-4o \
        --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


_PREAMBLE = """
import cadquery as cq
try:
    import OCP.TopoDS as _td
    for _cls in (_td.TopoDS_Shape, _td.TopoDS_Face, _td.TopoDS_Edge, _td.TopoDS_Vertex,
                 _td.TopoDS_Wire, _td.TopoDS_Shell, _td.TopoDS_Solid,
                 _td.TopoDS_Compound, _td.TopoDS_CompSolid):
        if not hasattr(_cls, 'HashCode'):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
except Exception:
    pass
show_object = lambda *a, **kw: None
"""
_SUFFIX = """
import sys as _sys
try:
    cq.exporters.export(result, _sys.argv[1])
except Exception as _e:
    raise RuntimeError(f"export failed: {_e}")
"""


def exec_cq(code: str, out_path: Path, timeout: int = 60) -> tuple[bool, str | None]:
    """Exec code in subprocess; write STEP to out_path. Returns (ok, err)."""
    lines = [
        ln
        for ln in code.splitlines()
        if ln.strip() not in ("import cadquery as cq", "import cadquery")
    ]
    script = _PREAMBLE + "\n".join(lines) + _SUFFIX
    env = {**os.environ, "LD_LIBRARY_PATH": LD}
    out_abs = out_path.resolve()
    try:
        r = subprocess.run(
            [sys.executable, "-c", script, str(out_abs)],
            env=env,
            timeout=timeout,
            capture_output=True,
            cwd=tempfile.gettempdir(),
        )
        if r.returncode != 0:
            return False, r.stderr.decode(errors="replace")[-400:]
        if not out_path.exists() or out_path.stat().st_size < 100:
            return False, "step missing or empty"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def _load_records(
    bench_dir: Path | None, hf_repo: str | None, hf_split: str
) -> tuple[list[dict], dict[str, str]]:
    """Return (records, orig_code_map) keyed by record_id."""
    if hf_repo:
        from bench.dataloader import load_hf

        rows = load_hf(hf_repo, hf_split)
        orig_code_map = {r["record_id"]: r["orig_code"] for r in rows}
        return list(rows), orig_code_map

    assert bench_dir is not None
    pairs_path = bench_dir / "pairs.jsonl"
    records = [json.loads(ln) for ln in pairs_path.read_text().splitlines() if ln]
    orig_code_map = {
        r["record_id"]: (bench_dir / r["original_code_path"]).read_text()
        for r in records
    }
    return records, orig_code_map


def run(
    bench_dir: Path | None,
    model: str,
    n: int,
    seed: int,
    hf_repo: str | None,
    hf_split: str,
) -> dict:
    from bench.models import call_edit_code
    from bench.results import ResultsDir
    from bench.sampling import sample_rows

    records, orig_code_map = _load_records(bench_dir, hf_repo, hf_split)
    sampled = sample_rows(records, n, seed, stratify_key="family", id_key="record_id")

    rd = ResultsDir(task="edit_code", model=model)
    done = rd.done_keys("record_id")
    todo = [r for r in sampled if r["record_id"] not in done]
    rd.log_run(
        {
            "seed": seed,
            "limit": n,
            "split": hf_split,
            "model": model,
            "hf_repo": hf_repo,
        },
        sampled,
        id_key="record_id",
    )

    print(f"Sampled {len(sampled)} (seed={seed})  done={len(done)}  todo={len(todo)}")
    print(f"Results dir: {rd.root}")

    n_total = len(todo)
    n_api_ok = n_exec_ok = 0
    t0 = time.time()

    with rd:
        for i, rec in enumerate(todo):
            rid = rec["record_id"]
            orig_code = orig_code_map[rid]
            instruction = rec["instruction"]

            t_api = time.time()
            code, api_err = call_edit_code(model, orig_code, instruction)
            api_dt = time.time() - t_api
            api_ok = code is not None
            exec_ok = False
            exec_err = None

            if api_ok:
                rd.save_code(rid, code)
                n_api_ok += 1
                rd.steps.mkdir(parents=True, exist_ok=True)
                step_path = rd.steps / f"{rid}.step"
                exec_ok, exec_err = exec_cq(code, step_path)
                if exec_ok:
                    n_exec_ok += 1

            rd.append(
                {
                    "record_id": rid,
                    "family": rec["family"],
                    "difficulty": rec.get("difficulty", ""),
                    "edit_type": rec.get("edit_type", ""),
                    "instruction": rec.get("instruction", ""),
                    "model": model,
                    "api_ok": api_ok,
                    "api_err": api_err,
                    "api_latency_s": round(api_dt, 3),
                    "exec_ok": exec_ok,
                    "exec_err": exec_err,
                }
            )
            print(
                f"[{i + 1:3d}/{n_total}] {rid:60s} api={'Y' if api_ok else 'N'}"
                f" exec={'Y' if exec_ok else 'N'} {api_dt:4.1f}s",
                flush=True,
            )

    elapsed = time.time() - t0
    summary = {
        "model": model,
        "n_total": n_total,
        "api_ok": n_api_ok,
        "exec_ok": n_exec_ok,
        "api_rate": round(n_api_ok / max(n_total, 1), 4),
        "exec_rate": round(n_exec_ok / max(n_total, 1), 4),
        "elapsed_s": round(elapsed, 1),
        "seed": seed,
    }
    (rd.root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{json.dumps(summary, indent=2)}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument(
        "--hf-repo",
        default="BenchCAD/cad_bench_edit",
        help="HF repo (set empty to use --bench-dir)",
    )
    ap.add_argument("--split", default="test")
    ap.add_argument(
        "--bench-dir", default="", help="Local bench dir (overrides --hf-repo)"
    )
    ap.add_argument("--limit", type=int, default=0, help="0=all; >200 stratified")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    bench_dir = Path(args.bench_dir) if args.bench_dir else None
    hf_repo = args.hf_repo if not bench_dir else None
    run(
        bench_dir,
        args.model,
        args.limit,
        args.seed,
        hf_repo=hf_repo,
        hf_split=args.split,
    )


if __name__ == "__main__":
    main()
