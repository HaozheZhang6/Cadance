#!/usr/bin/env bash
set -euo pipefail

export NPM_CONFIG_PREFIX=/npm-global
export PATH="/npm-global/bin:$PATH"

if [ ! -f "/npm-global/bin/claude" ]; then
    echo "[entrypoint] Installing @anthropic-ai/claude-code into /npm-global..."
    npm install -g @anthropic-ai/claude-code
else
    echo "[entrypoint] Updating @anthropic-ai/claude-code..."
    npm update -g @anthropic-ai/claude-code
fi

exec "$@"
