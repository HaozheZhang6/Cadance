"""OpenRouter adapter — unified gateway across providers.

OpenAI-compatible API at https://openrouter.ai/api/v1. Requires OPENROUTER_API_KEY.
Slug format: <provider>/<model> (e.g. "openai/o3", "qwen/qwen3-vl-32b-instruct").
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


def _is_reasoning_model(slug: str) -> bool:
    """OpenAI o1/o3 + GPT-5* via OR need max_completion_tokens and no temperature."""
    tail = slug.split("/", 1)[-1]
    return tail.startswith(("o1", "o3", "gpt-5"))


@register(
    # UA-27 — 7-model bench
    "openai/o3",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "qwen/qwen3-vl-32b-instruct",  # replaces dead qwen2.5-vl-32b-instruct
    "qwen/qwen3.5-122b-a10b",
    # add more OR slugs here as needed
)
class OpenRouterAdapter(OpenAICompatAdapter):
    base_url = "https://openrouter.ai/api/v1"
    env_key = "OPENROUTER_API_KEY"
    supports_images = True

    def __init__(self, name: str):
        super().__init__(name)
        if _is_reasoning_model(name):
            self.max_tokens_key = "max_completion_tokens"
            self.temperature_value = None
