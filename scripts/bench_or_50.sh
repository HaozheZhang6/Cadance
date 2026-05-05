#!/usr/bin/env bash
# UA-28 — bench 7 OR models on qixiaoqi/cad_bench_50 (50 stems × 12 [L1-L6] QA).
# Vision models run all 3 tasks (qa_img/qa_code/codegen).
# Text-only models run qa_code only.
# Continue-on-error per (model,task). Logs land in bench_logs/.
#
# Pre-req: OPENROUTER_API_KEY in .env, HF_TOKEN in .env.

set -u  # NOT -e — continue past failures

export PATH="$HOME/.local/bin:$PATH"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPO="qixiaoqi/cad_bench_50"
SPLIT="train"
LOGDIR="bench_logs/ua28_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGDIR"

# (model, mode)  mode = "all" → qa_img+qa_code+codegen ; "text" → qa_code only
MODELS_ALL=(
  "openai/o3"
  "google/gemma-4-31b-it:free"
  "google/gemma-4-26b-a4b-it:free"
  "nvidia/nemotron-nano-12b-v2-vl:free"
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
  "qwen/qwen3-vl-32b-instruct"
)
MODELS_TEXT=(
  "qwen/qwen3.5-122b-a10b"
)

run_task() {
  local model="$1" task="$2" runner="$3"
  local slug; slug=$(echo "$model" | tr '/:' '__')
  local log="$LOGDIR/${slug}__${task}.log"
  echo
  echo "--- [$model] $task -> $log"
  if uv run python "$runner" \
       --model "$model" --repo "$REPO" --split "$SPLIT" --limit 0 \
       > "$log" 2>&1; then
    tail -n 8 "$log" | sed 's/^/   /'
    echo "   ✓ $model / $task"
  else
    rc=$?
    echo "   ✗ $model / $task (exit=$rc) — continuing"
    tail -n 12 "$log" | sed 's/^/   /'
  fi
}

echo "=========================================="
echo "UA-28 bench: repo=$REPO  split=$SPLIT  limit=0 (all 50)"
echo "VISION models: ${#MODELS_ALL[@]} × 3 tasks"
echo "TEXT models:   ${#MODELS_TEXT[@]} × 1 task (qa_code)"
echo "Logs: $LOGDIR"
echo "=========================================="

for m in "${MODELS_ALL[@]}"; do
  run_task "$m" qa_img   bench/eval_qa_img.py
  run_task "$m" qa_code  bench/eval_qa_code.py
  run_task "$m" codegen  bench/eval.py
done
for m in "${MODELS_TEXT[@]}"; do
  run_task "$m" qa_code  bench/eval_qa_code.py
done

echo
echo "=========================================="
echo "DONE. Per-combo logs in $LOGDIR"
echo "Results in results/{qa_img,qa_code,img2cq}/<slug>/results.jsonl"
echo "=========================================="
