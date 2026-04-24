"""Importing this package registers all built-in provider adapters."""

from __future__ import annotations

# Side-effect imports — each module calls registry.register(...) at import.
# SDK imports inside each adapter's generate() are lazy, so a missing SDK
# only fails when the user actually picks that model (not at bench startup).
from . import (  # noqa: F401
    anthropic,
    deepseek,
    gemini,
    local_hf,
    mistral,
    openai,
    xai,
    zhipu,
)
