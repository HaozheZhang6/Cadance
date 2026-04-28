"""Kimi adapter — Moonshot AI (OpenAI-compatible chat.completions API).

Vision-capable models: kimi-latest, moonshot-v1-*-vision-preview.
Requires MOONSHOT_API_KEY.
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    "kimi-latest",
    "moonshot-v1-8k-vision-preview",
    "moonshot-v1-32k-vision-preview",
    "moonshot-v1-128k-vision-preview",
)
class KimiAdapter(OpenAICompatAdapter):
    base_url = "https://api.moonshot.ai/v1"
    env_key = "MOONSHOT_API_KEY"
    supports_images = True
