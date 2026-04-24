"""DeepSeek adapter — deepseek-chat (V3) + deepseek-reasoner (R1).

OpenAI-compatible API at https://api.deepseek.com/v1. Requires DEEPSEEK_API_KEY.
Text-only (no vision support).
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    "deepseek-chat",
    "deepseek-reasoner",
    "deepseek-coder",
)
class DeepSeekAdapter(OpenAICompatAdapter):
    base_url = "https://api.deepseek.com/v1"
    env_key = "DEEPSEEK_API_KEY"
    supports_images = False  # DeepSeek API chat.completions is text-only
