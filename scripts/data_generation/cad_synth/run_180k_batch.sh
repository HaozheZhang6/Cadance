#!/usr/bin/env bash
# Serial driver for UA-24 180k data-arg expansion.
#
# Loops 106 single-family configs in scripts/data_generation/cad_synth/configs/data_arg_180k/
# Resume-safe: --resume skips already-exported stems.
# Logs per-family elapsed + accept count to data/data_generation/synth_reports/180k_progress.log
#
# Usage:
#   bash scripts/data_generation/cad_synth/run_180k_batch.sh           # all 106
#   bash scripts/data_generation/cad_synth/run_180k_batch.sh --start grease_nipple  # resume from family
#   FAMILIES="hex_nut pulley" bash scripts/data_generation/cad_synth/run_180k_batch.sh  # subset

set -euo pipefail

CONFIG_DIR="scripts/data_generation/cad_synth/configs/data_arg_180k"
LOG_DIR="data/data_generation/synth_reports"
PROGRESS="$LOG_DIR/180k_progress.log"
WORKERS="${WORKERS:-8}"
RENDER="${RENDER:-0}"  # 0=skip PNG (Phase 1), 1=full pipeline incl render
NO_RENDER_FLAG=""
[[ "$RENDER" == "0" ]] && NO_RENDER_FLAG="--no-render"

mkdir -p "$LOG_DIR"

START_FAM=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START_FAM="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

CONFIGS=()
if [[ -n "${FAMILIES:-}" ]]; then
  for f in $FAMILIES; do
    CONFIGS+=("$CONFIG_DIR/${f}.yaml")
  done
else
  while IFS= read -r line; do
    CONFIGS+=("$line")
  done < <(ls "$CONFIG_DIR"/*.yaml | grep -v '/_' | sort)
fi

TOTAL=${#CONFIGS[@]}
echo "[$(date '+%Y-%m-%d %H:%M:%S')] START 180k batch: $TOTAL configs" | tee -a "$PROGRESS"

SKIPPING=0
[[ -n "$START_FAM" ]] && SKIPPING=1

i=0
for cfg in "${CONFIGS[@]}"; do
  i=$((i + 1))
  fam=$(basename "$cfg" .yaml)

  if [[ $SKIPPING -eq 1 ]]; then
    if [[ "$fam" == "$START_FAM" ]]; then
      SKIPPING=0
    else
      continue
    fi
  fi

  T1=$(date +%s)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$i/$TOTAL] $fam → start" | tee -a "$PROGRESS"

  if uv run python3 -m scripts.data_generation.cad_synth.pipeline.runner \
       --config "$cfg" --workers "$WORKERS" --resume --ignore-stuck $NO_RENDER_FLAG \
       > "$LOG_DIR/180k_${fam}.log" 2>&1; then
    T2=$(date +%s)
    REPORT="data/data_generation/synth_reports/data_arg_180k_${fam}.json"
    if [[ -f "$REPORT" ]]; then
      ACC=$(uv run python3 -c "import json; print(json.load(open('$REPORT'))['accepted'])")
      RATE=$(uv run python3 -c "import json; print(f\"{json.load(open('$REPORT'))['accept_rate']:.1f}\")")
    else
      ACC="?"; RATE="?"
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$i/$TOTAL] $fam → done in $((T2-T1))s, accepted=$ACC ($RATE%)" | tee -a "$PROGRESS"
  else
    T2=$(date +%s)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$i/$TOTAL] $fam → FAILED in $((T2-T1))s, see $LOG_DIR/180k_${fam}.log" | tee -a "$PROGRESS"
  fi
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] DONE 180k batch" | tee -a "$PROGRESS"

# Auto-push to HF unless NO_AUTO_PUSH=1 or Phase 1 (RENDER=0; no PNGs to push)
if [[ "${NO_AUTO_PUSH:-0}" != "1" && "$RENDER" == "1" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] AUTO-PUSH start → BenchCAD/cad_bench_X" | tee -a "$PROGRESS"
  if bash scripts/data_generation/cad_synth/push_180k.sh > "$LOG_DIR/180k_push.log" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AUTO-PUSH success" | tee -a "$PROGRESS"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AUTO-PUSH FAILED → see $LOG_DIR/180k_push.log" | tee -a "$PROGRESS"
  fi
fi
