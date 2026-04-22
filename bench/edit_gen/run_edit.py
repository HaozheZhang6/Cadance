"""Run the CAD edit benchmark.

For each pair: model gets (orig code + instruction) and must return modified code.
We save the returned code, exec it to STEP, record success/error.

Usage (zero-setup, read from HF):
    python -m bench.edit_gen.run_edit --model gpt-4o --n 10

Usage (local bench_dir with pairs.jsonl + codes/):
    python -m bench.edit_gen.run_edit --model gpt-4o --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCH = ROOT / "data" / "data_generation" / "bench_edit"
LD = os.environ.get("LD_LIBRARY_PATH", "/workspace/.local/lib")


try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


EDIT_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be given:
1. A CadQuery Python script that builds a parametric mechanical part.
2. A natural-language edit instruction describing a single numeric change.

Your task: return the script with that one change applied. Keep every other line
and value exactly the same.

Rules:
- Output ONLY executable Python code, no explanation, no markdown fences.
- The top of the script has a `# --- parameters ---` comment block listing the
  numeric parameters by name. Use those names to find the value to change.
- If the instruction says "Set X to V unit", set the value to V (respect the unit).
- If the instruction says "Change X by +P%" or "-P%", multiply the current value
  by (1 + P/100) and keep up to 4 decimal places.
- Do NOT refactor, rename, reorder, or add imports."""


def _strip_fences(code: str) -> str:
    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.M)
    code = re.sub(r"```\s*$", "", code, flags=re.M)
    return code.strip()


def call_edit(
    model: str, orig_code: str, instruction: str, api_key: str
) -> tuple[str | None, str | None]:
    import openai

    client = openai.OpenAI(api_key=api_key)
    user_text = (
        "Original CadQuery code:\n```python\n"
        + orig_code
        + "\n```\n\nEdit instruction: "
        + instruction
        + "\n\nReturn the full modified script."
    )
    try:
        tok_param = (
            "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EDIT_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            **{tok_param: 4096},
            temperature=0.0,
        )
        return _strip_fences(resp.choices[0].message.content or ""), None
    except Exception as e:
        return None, str(e)[:200]


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
    bench_dir: Path | None,
    hf_repo: str | None,
    hf_split: str,
) -> tuple[list[dict], dict[str, str]]:
    """Return (records, orig_code_map). orig_code_map keyed by record_id."""
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
    n: int | None,
    seed: int,
    skip_existing: bool,
    hf_repo: str | None = None,
    hf_split: str = "test",
    out_dir: Path | None = None,
) -> dict:
    records, orig_code_map = _load_records(bench_dir, hf_repo, hf_split)

    # Deterministic sampling: take first n per (family,difficulty,level) in file order
    if n:
        records = records[:n]

    run_root = out_dir or (bench_dir / "runs" if bench_dir else Path("bench_edit_runs"))
    run_dir = run_root / model.replace(":", "_").replace("/", "_")
    gen_code_dir = run_dir / "gen_code"
    gen_step_dir = run_dir / "gen_step"
    gen_code_dir.mkdir(parents=True, exist_ok=True)
    gen_step_dir.mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "results.jsonl"

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY1")
    if not key:
        raise RuntimeError("set OPENAI_API_KEY or OPENAI_API_KEY1")

    fh = results_path.open("w")
    n_total = len(records)
    n_api_ok = n_exec_ok = 0
    t0 = time.time()

    for i, rec in enumerate(records):
        rid = rec["record_id"]
        orig_code = orig_code_map[rid]
        instruction = rec["instruction"]

        gen_code_path = gen_code_dir / f"{rid}.py"
        gen_step_path = gen_step_dir / f"{rid}.step"

        if skip_existing and gen_code_path.exists() and gen_step_path.exists():
            n_api_ok += 1
            n_exec_ok += 1
            fh.write(
                json.dumps(
                    {
                        "record_id": rid,
                        "api_ok": True,
                        "exec_ok": True,
                        "skipped": True,
                    }
                )
                + "\n"
            )
            continue

        t_api = time.time()
        code, api_err = call_edit(model, orig_code, instruction, key)
        api_dt = time.time() - t_api
        api_ok = code is not None
        exec_ok = False
        exec_err = None

        if api_ok:
            gen_code_path.write_text(code)
            n_api_ok += 1
            exec_ok, exec_err = exec_cq(code, gen_step_path)
            if exec_ok:
                n_exec_ok += 1

        fh.write(
            json.dumps(
                {
                    "record_id": rid,
                    "family": rec["family"],
                    "difficulty": rec["difficulty"],
                    "level": rec["level"],
                    "axis": rec["axis"],
                    "pct_delta": rec["pct_delta"],
                    "api_ok": api_ok,
                    "api_err": api_err,
                    "api_latency_s": round(api_dt, 3),
                    "exec_ok": exec_ok,
                    "exec_err": exec_err,
                }
            )
            + "\n"
        )
        fh.flush()

        print(
            f"[{i+1:3d}/{n_total}] {rid:60s} api={'Y' if api_ok else 'N'}"
            f" exec={'Y' if exec_ok else 'N'} {api_dt:4.1f}s",
            flush=True,
        )

    fh.close()
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
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{json.dumps(summary, indent=2)}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hf-repo",
        type=str,
        default="BenchCAD/cad_bench_edit",
        help="HF dataset repo (default: BenchCAD/cad_bench_edit). Set empty to use --bench-dir.",
    )
    ap.add_argument("--split", type=str, default="test")
    ap.add_argument(
        "--bench-dir",
        type=str,
        default="",
        help="Local bench dir (pairs.jsonl + codes/). Takes precedence over --hf-repo when set.",
    )
    ap.add_argument("--model", type=str, default="gpt-4o")
    ap.add_argument("--n", type=int, default=None, help="Limit to first N records")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--out",
        type=str,
        default="",
        help="Output root dir (default: bench_edit_runs/ for HF, <bench-dir>/runs/ for local)",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip records whose gen_code and gen_step already exist",
    )
    args = ap.parse_args()
    bench_dir = Path(args.bench_dir) if args.bench_dir else None
    hf_repo = args.hf_repo if not bench_dir else None
    out_dir = Path(args.out) if args.out else None
    run(
        bench_dir,
        args.model,
        args.n,
        args.seed,
        args.skip_existing,
        hf_repo=hf_repo,
        hf_split=args.split,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
