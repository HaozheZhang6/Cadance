"""Local HuggingFace adapter — `local:<path>` for Qwen2-VL / Qwen2.5-VL.

Loads on first call; caches per-process by path.
"""

from __future__ import annotations

import json as _json
import os

from bench.models.registry import ModelAdapter, register_prefix

_PREFIX = "local:"
_cache: dict = {}


def _load(model_path: str) -> dict:
    if model_path in _cache:
        return _cache[model_path]
    import torch
    from transformers import AutoProcessor

    print(f"\nLoading {model_path} ...", flush=True)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_type = ""
    cfg = os.path.join(model_path, "config.json") if os.path.isdir(model_path) else None
    if cfg and os.path.exists(cfg):
        try:
            model_type = _json.load(open(cfg)).get("model_type", "")
        except Exception:
            pass

    if model_type == "qwen2_5_vl":
        from transformers import Qwen2_5_VLForConditionalGeneration as Cls
    else:
        from transformers import Qwen2VLForConditionalGeneration as Cls

    model = Cls.from_pretrained(model_path, torch_dtype=dtype).to(device)
    model.eval()
    processor = AutoProcessor.from_pretrained(model_path)
    _cache[model_path] = {"model": model, "processor": processor, "device": device}
    print("Model loaded.", flush=True)
    return _cache[model_path]


@register_prefix(_PREFIX)
class LocalHFAdapter(ModelAdapter):
    def __init__(self, name: str):
        assert name.startswith(_PREFIX)
        self.name = name
        self.model_path = name[len(_PREFIX) :]

    def generate(
        self,
        system: str,
        user_text: str,
        images: list | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str | None, str | None]:
        try:
            import torch
            from qwen_vl_utils import process_vision_info
        except ImportError as e:
            return None, f"missing dep: {e}"
        try:
            state = _load(self.model_path)
            model = state["model"]
            processor = state["processor"]
            device = state["device"]

            user_content: list = []
            for img in images or []:
                user_content.append({"type": "image", "image": img})
            user_content.append({"type": "text", "text": user_text})
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]
            text = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(device)

            with torch.no_grad():
                out = model.generate(
                    **inputs, max_new_tokens=max_tokens, do_sample=False
                )
            decoded = processor.decode(
                out[0][len(inputs["input_ids"][0]) :], skip_special_tokens=True
            )
            return decoded, None
        except Exception as e:
            return None, str(e)[:300]
