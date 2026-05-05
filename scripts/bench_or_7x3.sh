#!/usr/bin/env bash
# UA-27 — bench 7 OR models × 3 tasks × 50 samples (seed=42).
# Continue-on-error per (model,task). Logs land in bench_logs/.
#
# Pre-req: OPENROUTER_API_KEY in .env.
# Codegen needs CadQuery exec env (LD_LIBRARY_PATH=/workspace/.local/lib).

set -u  # NOT -e — we want to continue past failures

export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-/workspace/.local/lib}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LIMIT=50
SEED=42
LOGDIR="bench_logs/ua27_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGDIR"

MODELS=(
  "openai/o3"
  "google/gemma-4-31b-it:free"
  "google/gemma-4-26b-a4b-it:free"
  "nvidia/nemotron-nano-12b-v2-vl:free"
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
  "qwen/qwen3-vl-32b-instruct"
  "qwen/qwen3.5-122b-a10b"
)

# task_name : runner_path
TASKS_NAMES=(qa_img qa_code codegen)
TASKS_RUNNERS=(bench/eval_qa_img.py bench/eval_qa_code.py bench/eval.py)

echo "=========================================="
echo "UA-27 bench: 7 models x 3 tasks x N=$LIMIT (seed=$SEED)"
echo "Logs: $LOGDIR"
echo "=========================================="

for model in "${MODELS[@]}"; do
  slug=$(echo "$model" | tr '/:' '__')
  for i in "${!TASKS_NAMES[@]}"; do
    task="${TASKS_NAMES[$i]}"
    runner="${TASKS_RUNNERS[$i]}"
    log="$LOGDIR/${slug}__${task}.log"
    echo
    echo "--- [$model] $task -> $log"
    if uv run python "$runner" --model "$model" --limit "$LIMIT" --seed "$SEED" \
         > "$log" 2>&1; then
      tail -n 8 "$log" | sed 's/^/   /'
      echo "   ✓ $model / $task"
    else
      rc=$?
      echo "   ✗ $model / $task (exit=$rc) — continuing"
      tail -n 15 "$log" | sed 's/^/   /'
    fi
  done
done

echo
echo "=========================================="
echo "DONE. Per-combo logs in $LOGDIR"
echo "Results in results/{qa_img,qa_code,img2cq}/<slug>/results.jsonl"
echo "=========================================="
