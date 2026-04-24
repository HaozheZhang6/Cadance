"""QA-img bench — composite image + numeric questions → answers → ratio acc.

Flow per sample:
  composite_png + qa_pairs → VLM (registry adapter) → JSON[float] → qa_score

No CadQuery exec. Pure "look at render, answer numeric Qs".

Results land in `results/qa_img/<model>/`, dedup by stem across runs.

Usage:
    uv run python bench/eval_qa_img.py --model gpt-4o --limit 50 --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def _load_qa_pairs(row: dict) -> list[dict]:
    raw = row.get("qa_pairs", "[]")
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def eval_sample(row: dict, model: str, api_key: str) -> dict:
    from bench.metrics import qa_score, qa_score_single
    from bench.models import call_vlm_qa

    qa_pairs = _load_qa_pairs(row)
    res = {
        "stem": row["stem"],
        "family": row["family"],
        "difficulty": row["difficulty"],
        "model": model,
        "n_qa": len(qa_pairs),
        "qa_score": 0.0,
        "per_qa": [],
        "error": None,
    }
    if not qa_pairs:
        res["error"] = "no_qa_pairs"
        return res

    questions = [q["question"] for q in qa_pairs]
    t0 = time.time()
    answers, err = call_vlm_qa(model, row["composite_png"], questions, api_key)
    res["vlm_latency_s"] = round(time.time() - t0, 2)

    if answers is None:
        res["error"] = f"vlm_fail: {err}"
        return res

    res["pred_answers"] = answers
    res["gt_answers"] = [q["answer"] for q in qa_pairs]
    res["per_qa"] = [
        {
            "q": q["question"],
            "type": q["type"],
            "gt": q["answer"],
            "pred": p,
            "score": qa_score_single(p, q),
        }
        for q, p in zip(qa_pairs, answers, strict=True)
    ]
    res["qa_score"] = qa_score(answers, qa_pairs)
    return res


def report(results: list[dict]) -> None:
    if not results:
        print("No results.")
        return
    n = len(results)
    ok = [r for r in results if r["error"] is None]
    scores = [r["qa_score"] for r in ok]
    print(f"\n{'=' * 60}")
    print(f"QA-Img Bench  |  model={results[0]['model']}  N={n}")
    print(f"{'=' * 60}")
    print(f"parse_ok : {len(ok)}/{n}  ({len(ok) / n * 100:.1f}%)")
    print(f"qa_score : {sum(scores) / len(scores):.3f}" if scores else "qa_score: —")

    by_fam = defaultdict(list)
    for r in results:
        by_fam[r["family"]].append(r)
    print(f"\n{'family':<20} {'N':>3} {'ok':>3} {'qa_score':>10}")
    print("-" * 40)
    for fam, rs in sorted(by_fam.items()):
        ok_rs = [x for x in rs if x["error"] is None]
        sc = sum(x["qa_score"] for x in ok_rs) / len(ok_rs) if ok_rs else 0.0
        print(f"{fam:<20} {len(rs):>3} {len(ok_rs):>3} {sc:>10.3f}")
    print("=" * 60)


def main() -> None:
    from bench.dataloader import load_hf
    from bench.results import ResultsDir
    from bench.sampling import sample_rows

    ap = argparse.ArgumentParser(description="QA-img bench")
    ap.add_argument("--model", required=True)
    ap.add_argument("--repo", default="BenchCAD/cad_bench")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=0, help="0=all; >200 stratified")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    token = (
        os.environ.get("BenchCAD_HF_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
    )
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY1")
    if not api_key:
        sys.exit("OPENAI_API_KEY not set")

    print(f"Loading {args.repo}[{args.split}] ...")
    rows = load_hf(args.repo, args.split, token=token)
    sampled = sample_rows(rows, args.limit, args.seed)

    rd = ResultsDir(task="qa_img", model=args.model)
    done = rd.done_keys("stem")
    todo = [r for r in sampled if r["stem"] not in done]
    rd.log_run(vars(args), sampled)

    print(
        f"Sampled {len(sampled)} (seed={args.seed})  done={len(done)}  todo={len(todo)}"
    )
    print(f"Results dir: {rd.root}")

    with rd:
        for i, row in enumerate(todo):
            print(f"  [{i + 1}/{len(todo)}] {row['stem']}  ", end="", flush=True)
            res = eval_sample(row, args.model, api_key)
            rd.append(res)
            if res["error"]:
                print(f"ERR {res['error'][:80]}")
            else:
                print(f"qa={res['qa_score']:.3f}  n={res['n_qa']}")

    with open(rd.results_path) as f:
        results = [json.loads(line) for line in f if line.strip()]
    report(results)


if __name__ == "__main__":
    main()
