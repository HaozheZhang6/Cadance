#!/usr/bin/env bash
# Parallel img2cq eval × 3 models on BenchCAD/cad_bench_200 (single-axis IoU,
# workers 4 each), then render saved codes → 4-view PNG, build mosaic, post 4
# chunks to Discord.
#
# Note: gpt-4o was completed earlier with 24-axis IoU (199/199, dedup'd by
# stem); this run will see all-done and skip it. 5.3-chat-latest and
# 5.3-thinking are full 200-sample fresh runs with single-axis.
#
# 跑: bash bench/run_3models_200.sh
#
# Logs: data/data_generation/_run_3models_200/

set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_3models_200
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "START pipeline (3 models parallel, workers=4 each, single-axis IoU)"

# 1-3. Eval 3 models IN PARALLEL (each with its own workers=4 thread pool)
PIDS=()
for MODEL in gpt-4o gpt-5.3-chat-latest gpt-5.3-thinking; do
  log "EVAL launch: $MODEL"
  (
    uv run python bench/eval.py \
      --model "$MODEL" \
      --repo BenchCAD/cad_bench_200 \
      --split train \
      --workers 4 \
      > "$LOG_DIR/eval_${MODEL}.log" 2>&1
  ) &
  PIDS+=($!)
done

# Wait for all 3 evals
RC=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    log "EVAL pid=$pid failed"
    RC=1
  fi
done
log "EVAL all done (rc=$RC)"

# 4. Render generated codes for all 3 models (workers 4)
log "RENDER start (up to 599 codes, workers=4)"
T0=$(date +%s)
uv run python bench/render_eval_codes.py \
  --models gpt-4o,gpt-5.3-chat-latest,gpt-5.3-thinking \
  --workers 4 \
  > "$LOG_DIR/render.log" 2>&1 || log "RENDER failed (rc=$?)"
T1=$(date +%s)
log "RENDER done in $((T1 - T0))s"

# 5. Build mosaic + post to Discord
log "MOSAIC + DISCORD start"
T0=$(date +%s)
uv run python bench/post_3model_mosaic.py \
  > "$LOG_DIR/post.log" 2>&1 || log "POST failed (rc=$?)"
T1=$(date +%s)
log "MOSAIC + DISCORD done in $((T1 - T0))s"

log "DONE pipeline"
