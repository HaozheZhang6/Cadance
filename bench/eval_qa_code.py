"""Code-QA bench — CadQuery code + numeric questions → answers → ratio accuracy.

Flow per sample:
  gt_code (from HF) + qa_pairs (questions) → text LLM → JSON[float] → qa_score

No image, no CadQuery exec, no STEP. Pure "read code, answer numeric Qs".

Usage:
    uv run python bench/eval_qa_code.py \
        --repo Hula0401/cad_synth_bench_smoke \
        --split test_iid --limit 12 --model gpt-4o
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
    from bench.models import call_llm_qa_code

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
    answers, err = call_llm_qa_code(model, row["gt_code"], questions, api_key)
    res["llm_latency_s"] = round(time.time() - t0, 2)

    if answers is None:
        res["error"] = f"llm_fail: {err}"
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
    print(f"Code-QA Bench  |  model={results[0]['model']}  N={n}")
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


def main():
    ap = argparse.ArgumentParser(description="Code-QA bench runner")
    ap.add_argument("--repo", default="Hula0401/cad_synth_bench_smoke")
    ap.add_argument("--split", default="test_iid")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--out", default="bench/test/results/qa_code_results.jsonl")
    args = ap.parse_args()

    from bench.dataloader import load_hf

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY1")
    if not api_key:
        sys.exit("OPENAI_API_KEY not set")

    print(f"Loading {args.repo}[{args.split}] ...")
    rows = load_hf(args.repo, args.split, token=token)
    if args.limit:
        rows = rows[: args.limit]
    print(f"N={len(rows)}  model={args.model}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with open(out_path, "w") as f:
        for i, row in enumerate(rows):
            print(f"  [{i + 1}/{len(rows)}] {row['stem']}  ", end="", flush=True)
            res = eval_sample(row, args.model, api_key)
            slim = {k: v for k, v in res.items() if k != "per_qa"}
            slim["per_qa"] = res["per_qa"]
            f.write(json.dumps(slim) + "\n")
            f.flush()
            results.append(res)
            if res["error"]:
                print(f"ERR {res['error'][:80]}")
            else:
                print(f"qa={res['qa_score']:.3f}  n={res['n_qa']}")

    report(results)
    print(f"Results: {out_path}")


if __name__ == "__main__":
    main()
