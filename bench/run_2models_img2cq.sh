#!/usr/bin/env bash
# Resume img2cq on cad_bench_200 for gemini-2.5-pro + moonshot-v1-128k-vision-preview
# (parallel, workers=4 each). Already-done stems are dedup'd by eval.py.
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_2models_img2cq
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "START 2-model img2cq pipeline (single-axis, workers=4 each)"

PIDS=()
for M in gemini-2.5-pro moonshot-v1-128k-vision-preview; do
  log "EVAL launch: $M"
  ( uv run python bench/eval.py \
      --model "$M" \
      --repo BenchCAD/cad_bench_200 \
      --split train \
      --workers 4 \
      > "$LOG_DIR/eval_${M}.log" 2>&1 ) &
  PIDS+=($!)
done

RC=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    log "EVAL pid=$pid failed"
    RC=1
  fi
done
log "DONE 2-model img2cq (rc=$RC)"
