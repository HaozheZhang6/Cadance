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
            resp = client.models.generate_content(
                model=self.name,
                contents=[gtypes.Content(role="user", parts=parts)],
                config=gtypes.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=0.0,
                ),
            )
            return resp.text or "", None
        except Exception as e:
            return None, str(e)[:200]
