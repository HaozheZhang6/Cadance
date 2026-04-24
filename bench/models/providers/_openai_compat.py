"""Shared base for OpenAI-compatible HTTP providers (xAI, DeepSeek, Zhipu, Mistral).

Subclass sets `base_url`, `env_key`, and per-model quirks. Uses the official
`openai` SDK with `base_url` override — no extra deps.
"""

from __future__ import annotations

import base64
import io
import os

from bench.models.registry import ModelAdapter


def _img_to_b64(pil_img) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class OpenAICompatAdapter(ModelAdapter):
    """Base class for OpenAI-compatible chat.completions providers.

    Subclass attributes:
      base_url: provider endpoint
      env_key: env var holding the API key
      supports_images: if False, drop images instead of including (text-only)
      temperature_value: None to omit temperature
      max_tokens_key: "max_tokens" or "max_completion_tokens"
    """

    base_url: str = ""
    env_key: str = ""
    supports_images: bool = True
    temperature_value: float | None = 0.0
    max_tokens_key: str = "max_tokens"

    def __init__(self, name: str):
        self.name = name
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import openai

            api_key = os.environ.get(self.env_key)
            if not api_key:
                raise RuntimeError(f"{self.env_key} not set")
            self._client = openai.OpenAI(api_key=api_key, base_url=self.base_url)
        return self._client

    def generate(
        self,
        system: str,
        user_text: str,
        images: list | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str | None, str | None]:
        try:
            client = self._client_lazy()
            user_content: list = [{"type": "text", "text": user_text}]
            if self.supports_images:
                for img in images or []:
                    b64 = _img_to_b64(img)
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        }
                    )
            kwargs: dict = {
                "model": self.name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                self.max_tokens_key: max_tokens,
            }
            if self.temperature_value is not None:
                kwargs["temperature"] = self.temperature_value
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or "", None
        except Exception as e:
            return None, str(e)[:200]
