#!/usr/bin/env bash
# Push all 106 data_arg_180k_* runs to BenchCAD/cad_bench_X (UA-24).

set -euo pipefail

REPO="${REPO:-BenchCAD/cad_bench_X}"
CONFIG_DIR="scripts/data_generation/cad_synth/configs/data_arg_180k"

shopt -s nullglob
ARGS=()
for cfg in "$CONFIG_DIR"/*.yaml; do
  bn=$(basename "$cfg" .yaml)
  [[ "$bn" == _* ]] && continue
  ARGS+=(--run "data_arg_180k_${bn}")
done
shopt -u nullglob

run_count=$(( ${#ARGS[@]} / 2 ))
echo "Pushing ${run_count} runs to $REPO"
echo "Run names: $(echo "${ARGS[@]}" | tr ' ' '\n' | grep -v '^--run$' | head -3) ..."

uv run python3 scripts/data_generation/cad_synth/push_bench_hf.py \
  "${ARGS[@]}" --repo "$REPO" --workers 8
