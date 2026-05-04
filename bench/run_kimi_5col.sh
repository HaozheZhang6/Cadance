#!/usr/bin/env bash
# Eval moonshot-v1-8k-vision-preview on cad_bench_200 (single-axis, workers=4), render gen codes,
# rebuild 5-col mosaic (GT | 4o | 5.3-thinking | 5.3-chat-latest | kimi), post 4 chunks.
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_kimi_5col
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "START kimi pipeline"

log "EVAL moonshot-v1-8k-vision-preview start"
T0=$(date +%s)
uv run python bench/eval.py \
  --model moonshot-v1-8k-vision-preview \
  --repo BenchCAD/cad_bench_200 \
  --split train \
  --workers 4 \
  > "$LOG_DIR/eval_kimi.log" 2>&1 || log "EVAL kimi failed (rc=$?)"
T1=$(date +%s)
log "EVAL kimi done in $((T1 - T0))s"

log "RENDER kimi start (subprocess+timeout 60, workers=4)"
T0=$(date +%s)
uv run python bench/render_eval_codes.py \
  --model moonshot-v1-8k-vision-preview \
  --workers 4 \
  --timeout 60 \
  > "$LOG_DIR/render_kimi.log" 2>&1 || log "RENDER kimi failed (rc=$?)"
T1=$(date +%s)
log "RENDER kimi done in $((T1 - T0))s"

log "MOSAIC 5-col + DISCORD start"
T0=$(date +%s)
uv run python bench/post_3model_mosaic.py \
  > "$LOG_DIR/post.log" 2>&1 || log "POST failed (rc=$?)"
T1=$(date +%s)
log "MOSAIC + DISCORD done in $((T1 - T0))s"

log "DONE kimi pipeline"
