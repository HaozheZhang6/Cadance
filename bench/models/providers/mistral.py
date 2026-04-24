"""Mistral AI adapter — mistral-large / pixtral / codestral / magistral families.

OpenAI-compatible API at https://api.mistral.ai/v1. Requires MISTRAL_API_KEY.
Vision: pixtral-*; text-only: mistral-*, codestral-*, magistral-*.
Adapter unconditionally forwards images (provider rejects if unsupported).
"""

from __future__ import annotations

from bench.models.registry import register

from ._openai_compat import OpenAICompatAdapter


@register(
    # Mistral text
    "mistral-large-latest",
    "mistral-medium-latest",
    "mistral-small-latest",
    "mistral-tiny",
    # Pixtral (vision)
    "pixtral-large-latest",
    "pixtral-12b-2409",
    "pixtral-12b-latest",
    # Codestral
    "codestral-latest",
    "codestral-2508",
    # Magistral (reasoning)
    "magistral-medium-latest",
    "magistral-small-latest",
    # Ministral
    "ministral-8b-latest",
    "ministral-3b-latest",
)
class MistralAdapter(OpenAICompatAdapter):
    base_url = "https://api.mistral.ai/v1"
    env_key = "MISTRAL_API_KEY"
    supports_images = True
