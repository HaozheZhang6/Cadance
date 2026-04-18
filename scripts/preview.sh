#!/usr/bin/env bash
# Render a CadQuery Python file to 4-view PNG composite.
#
# Usage:
#   ./scripts/preview.sh path/to/file.py
#   ./scripts/preview.sh path/to/file.py /custom/out/dir
#   ./scripts/preview.sh path/to/file.py --size 512
#
# Output: tmp/previews/<stem>/composite.png (+ view_0..3 + <stem>.step)

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <code.py> [out_dir] [--size N] [--timeout N]"
    exit 1
fi

CODE="$1"; shift
STEM=$(basename "${CODE%.py}")
OUT="tmp/previews/${STEM}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --size|--timeout) EXTRA_ARGS+=("$1" "$2"); shift 2 ;;
        --*) EXTRA_ARGS+=("$1"); shift ;;
        *) OUT="$1"; shift ;;
    esac
done

export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="/workspace/.venv/lib/python3.11/site-packages"
LD_LIBRARY_PATH=/workspace/.local/lib \
python3 scripts/data_generation/render_cq_file.py \
    --code "$CODE" \
    --out "$OUT" \
    --keep-step \
    "${EXTRA_ARGS[@]}"
