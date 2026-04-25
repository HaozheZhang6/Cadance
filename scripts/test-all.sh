#!/bin/bash
# Run all tests
# Usage: ./scripts/test-all.sh [pytest-args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

uv run pytest tests "$@"
