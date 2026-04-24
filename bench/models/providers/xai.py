"""xAI Grok adapter — vision-capable grok-2-vision / grok-3 / grok-4 families.

OpenAI-compatible API at https://api.x.ai/v1. Requires XAI_API_KEY.
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    # Grok 2
    "grok-2",
    "grok-2-latest",
    "grok-2-vision",
    "grok-2-vision-latest",
    "grok-2-vision-1212",
    # Grok 3
    "grok-3",
    "grok-3-latest",
    "grok-3-mini",
    "grok-3-mini-latest",
    "grok-3-fast",
    # Grok 4
    "grok-4",
    "grok-4-latest",
    "grok-4-fast-reasoning",
    "grok-4-fast-non-reasoning",
    "grok-code-fast-1",
)
class XAIAdapter(OpenAICompatAdapter):
    base_url = "https://api.x.ai/v1"
    env_key = "XAI_API_KEY"
    supports_images = True
