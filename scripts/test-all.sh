#!/bin/bash
# Run all tests across the monorepo
# Usage: ./scripts/test-all.sh [pytest-args]
#
# Examples:
#   ./scripts/test-all.sh              # Run all tests
#   ./scripts/test-all.sh -v           # Run with verbose output
#   ./scripts/test-all.sh -x           # Stop on first failure
#   ./scripts/test-all.sh --tb=short   # Short tracebacks

set -e  # Exit on first failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "=========================================="
echo "Running root project tests..."
echo "=========================================="
uv run pytest tests "$@"

echo ""
echo "=========================================="
echo "Running eda_verify tests..."
echo "=========================================="
# Use -c to specify the root pyproject.toml to avoid picking up eda_verify's config
uv run pytest -c pyproject.toml src/eda_verifier/eda_verify/tests/unit src/eda_verifier/eda_verify/tests/property "$@"

echo ""
echo "=========================================="
echo "Running kicad_verify tests..."
echo "=========================================="
# Use -c to specify the root pyproject.toml to avoid picking up kicad_verify's config
uv run pytest -c pyproject.toml src/eda_verifier/kicad_verify/tests/unit "$@"

echo ""
echo "=========================================="
echo "All tests passed!"
echo "=========================================="
