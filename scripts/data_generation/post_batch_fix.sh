#!/usr/bin/env bash
# Run after a batch completes to fix verified_pairs.jsonl:
# - Fill missing metadata fields
# - Render views for new records
# Usage: ./scripts/data_generation/post_batch_fix.sh

export PATH="$HOME/.local/bin:$PATH"
LD_LIBRARY_PATH=/workspace/.local/lib PYTHONUNBUFFERED=1 \
uv run python scripts/data_generation/fix_verified_pairs.py --render-only
