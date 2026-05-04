#!/usr/bin/env bash
# Run qa_img + qa_code on kimi-k2.6 (parallel, workers=4 each).
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

LOG_DIR=data/data_generation/_run_qa_kimi_k26
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$PIPELINE_LOG"; }

log "START kimi-k2.6 qa pipeline"
log "EVAL launch qa_img: kimi-k2.6"
( uv run python bench/eval_qa_img.py \
    --model kimi-k2.6 \
    --repo BenchCAD/cad_bench_200 \
    --split train \
    --workers 4 \
    > "$LOG_DIR/qa_img.log" 2>&1 ) &
PID_IMG=$!

log "EVAL launch qa_code: kimi-k2.6"
( uv run python bench/eval_qa_code.py \
    --model kimi-k2.6 \
    --repo BenchCAD/cad_bench_200 \
    --split train \
    --workers 4 \
    > "$LOG_DIR/qa_code.log" 2>&1 ) &
PID_CODE=$!

RC=0
wait "$PID_IMG" || { log "qa_img failed (rc=$?)"; RC=1; }
wait "$PID_CODE" || { log "qa_code failed (rc=$?)"; RC=1; }
log "DONE kimi-k2.6 (rc=$RC)"
