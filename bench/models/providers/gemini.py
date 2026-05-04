"""Google Gemini adapter — Gemini 2.5 / 2.0 / 1.5 families.

Requires `google-genai` SDK + GEMINI_API_KEY (or GOOGLE_API_KEY).
"""

from __future__ import annotations

import io
import os

from bench.models.registry import ModelAdapter, register


@register(
    # Gemini 2.5
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro-preview",
    "gemini-2.5-flash-preview",
    # Gemini 2.0
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-pro-exp",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-thinking-exp",
    # Gemini 1.5
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b",
    # Gemini 3.x — thinking variants. Real API model = name with "-thinking"
    # /"-nonthinking" suffix stripped. Thinking budget set per-suffix.
    "gemini-3-pro-preview",
    "gemini-3-pro-preview-thinking",
    "gemini-3-pro-preview-nonthinking",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.1-pro-preview-thinking",
    "gemini-3.1-pro-preview-nonthinking",
    "gemini-3.1-flash-lite-preview",
)
class GeminiAdapter(ModelAdapter):
    def __init__(self, name: str):
        self.name = name
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
                "GOOGLE_API_KEY"
            )
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def generate(
        self,
        system: str,
        user_text: str,
        images: list | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str | None, str | None]:
        try:
            from google.genai import types as gtypes

            client = self._client_lazy()
            parts: list = []
            for img in images or []:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                parts.append(
                    gtypes.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")
                )
            parts.append(gtypes.Part.from_text(text=user_text))
            # Resolve real API model name + thinking strategy from suffix
            api_name = self.name
            thinking_budget: int | None = None
            if api_name.endswith("-nonthinking"):
                api_name = api_name[: -len("-nonthinking")]
                # Gemini 2.5 accepts 0 to fully disable; 3.x rejects 0 → use 128 min
                thinking_budget = 0 if "2.5" in api_name else 128
            elif api_name.endswith("-thinking"):
                api_name = api_name[: -len("-thinking")]
                thinking_budget = 2048
            elif "2.5" in api_name or "3" in api_name:
                thinking_budget = 512

            cfg_kwargs: dict = dict(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=0.0,
            )
            if thinking_budget is not None:
                cfg_kwargs["thinking_config"] = gtypes.ThinkingConfig(
                    thinking_budget=thinking_budget
                )
            resp = client.models.generate_content(
                model=api_name,
                contents=[gtypes.Content(role="user", parts=parts)],
                config=gtypes.GenerateContentConfig(**cfg_kwargs),
            )
            return resp.text or "", None
        except Exception as e:
            return None, str(e)[:200]
