"""Anthropic Claude adapter — Claude 4 / 3.7 / 3.5 families.

Requires `anthropic` SDK + ANTHROPIC_API_KEY. Uses messages API with
native image blocks (base64 PNG).
"""

from __future__ import annotations

import base64
import io
import os

from bench.models.registry import ModelAdapter, register


def _img_to_b64(pil_img) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@register(
    # Claude 4 (current flagship)
    "claude-opus-4",
    "claude-opus-4-0",
    "claude-opus-4-5",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-sonnet-4",
    "claude-sonnet-4-0",
    "claude-sonnet-4-5",
    "claude-sonnet-4-6",
    "claude-haiku-4",
    "claude-haiku-4-5",
    # Claude 3.7 / 3.5 (still in rotation)
    "claude-3-7-sonnet-latest",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-latest",
    "claude-3-opus-20240229",
    # Haiku / Sonnet legacy
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
)
class AnthropicAdapter(ModelAdapter):
    def __init__(self, name: str):
        self.name = name
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=api_key)
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
            content: list = []
            for img in images or []:
                b64 = _img_to_b64(img)
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64,
                        },
                    }
                )
            content.append({"type": "text", "text": user_text})
            resp = client.messages.create(
                model=self.name,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
            # resp.content is a list of blocks; concatenate text blocks.
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", "") == "text"
            )
            return text, None
        except Exception as e:
            return None, str(e)[:200]
