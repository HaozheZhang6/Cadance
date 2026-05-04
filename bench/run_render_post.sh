#!/usr/bin/env bash
# Re-render saved gen codes (subprocess + timeout=60 + cad_bench_200 stem filter)
# + rebuild mosaic + post to Discord.
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_3models_200
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "RE-RENDER v2 start (subprocess+timeout 60, workers=4, stems=cad_bench_200)"
T0=$(date +%s)
uv run python bench/render_eval_codes.py \
  --models gpt-4o,gpt-5.3-chat-latest,gpt-5.3-thinking \
  --workers 4 \
  --timeout 60 \
  > "$LOG_DIR/render.log" 2>&1 || log "RENDER failed (rc=$?)"
T1=$(date +%s)
log "RENDER done in $((T1 - T0))s"

log "MOSAIC + DISCORD start"
T0=$(date +%s)
uv run python bench/post_3model_mosaic.py \
  > "$LOG_DIR/post.log" 2>&1 || log "POST failed (rc=$?)"
T1=$(date +%s)
log "MOSAIC + DISCORD done in $((T1 - T0))s"

log "DONE re-render+post v2"
