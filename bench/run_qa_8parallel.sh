#!/usr/bin/env bash
# 4 models × 2 tasks (qa_img + qa_code) all parallel, each workers=4 = 8 evals
# Logs: data/data_generation/_run_qa_8parallel/
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_qa_8parallel
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "START 8-parallel QA pipeline"

MODELS=(gpt-4o gpt-5.3-chat-latest gpt-5.3-thinking moonshot-v1-8k-vision-preview)
PIDS=()

for M in "${MODELS[@]}"; do
  log "EVAL launch qa_img: $M"
  ( uv run python bench/eval_qa_img.py \
      --model "$M" \
      --repo BenchCAD/cad_bench_200 \
      --split train \
      --workers 4 \
      > "$LOG_DIR/qa_img_${M}.log" 2>&1 ) &
  PIDS+=($!)

  log "EVAL launch qa_code: $M"
  ( uv run python bench/eval_qa_code.py \
      --model "$M" \
      --repo BenchCAD/cad_bench_200 \
      --split train \
      --workers 4 \
      > "$LOG_DIR/qa_code_${M}.log" 2>&1 ) &
  PIDS+=($!)
done

RC=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    log "EVAL pid=$pid failed"
    RC=1
  fi
done
log "ALL 8 EVALS done (rc=$RC)"
log "DONE qa pipeline"
