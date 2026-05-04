"""Kimi adapter — Moonshot AI (OpenAI-compatible chat.completions API).

Vision-capable models (probed): kimi-k2.6, moonshot-v1-*-vision-preview.
Probed text-only despite accepting images: kimi-k2.5 (silent ignore).
Requires MOONSHOT_API_KEY.
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    "kimi-latest",
    "kimi-k2.5",
    "kimi-k2.6",
    "moonshot-v1-8k-vision-preview",
    "moonshot-v1-32k-vision-preview",
    "moonshot-v1-128k-vision-preview",
)
class KimiAdapter(OpenAICompatAdapter):
    base_url = "https://api.moonshot.ai/v1"
    env_key = "MOONSHOT_API_KEY"
    supports_images = True

    def __init__(self, name: str):
        super().__init__(name)
        # kimi-k2.5/k2.6 reject non-default temperature (API: "only 1 is supported")
        if name in ("kimi-k2.5", "kimi-k2.6"):
            self.temperature_value = None
