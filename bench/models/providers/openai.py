"""OpenAI adapter — gpt-4o, gpt-4.1, gpt-5*, o1, o3 families."""

from __future__ import annotations

import base64
import io
import os

from bench.models.registry import ModelAdapter, register


def _img_to_b64(pil_img) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _max_tokens_kwarg(model: str, n: int) -> dict:
    """gpt-5.x uses `max_completion_tokens`; older OpenAI models use `max_tokens`."""
    key = (
        "max_completion_tokens"
        if model.startswith(("gpt-5", "o1", "o3"))
        else "max_tokens"
    )
    return {key: n}


def _supports_temperature(model: str) -> bool:
    # o1/o3 reasoning models reject `temperature`; gpt-5 accepts only default
    return not model.startswith(("o1", "o3", "gpt-5"))


@register(
    # GPT-4 family
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    # GPT-5 family (bare)
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-pro",
    "gpt-5-codex",
    "gpt-5-chat-latest",
    # GPT-5.1
    "gpt-5.1",
    "gpt-5.1-codex",
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
    "gpt-5.1-chat-latest",
    # GPT-5.2
    "gpt-5.2",
    "gpt-5.2-pro",
    "gpt-5.2-codex",
    "gpt-5.2-chat-latest",
    # GPT-5.3 (only chat + codex variants exist)
    "gpt-5.3-chat-latest",
    "gpt-5.3-codex",
    # GPT-5.4
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.4-pro",
    # o-series
    "o1",
    "o1-mini",
    "o3",
    "o3-mini",
)
class OpenAIAdapter(ModelAdapter):
    def __init__(self, name: str):
        self.name = name
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import openai

            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get(
                "OPENAI_API_KEY1"
            )
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            self._client = openai.OpenAI(api_key=api_key)
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
                **_max_tokens_kwarg(self.name, max_tokens),
            }
            if _supports_temperature(self.name):
                kwargs["temperature"] = 0.0
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or "", None
        except Exception as e:
            return None, str(e)[:200]
