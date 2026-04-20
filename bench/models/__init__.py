"""VLM model wrappers — OpenAI and local Qwen2-VL / Qwen2.5-VL."""

from __future__ import annotations

import base64
import io
import os
import re

SYSTEM_PROMPT = """You are an expert CAD engineer. You will be shown a 2×2 composite image of an industrial mechanical part rendered from 4 fixed diagonal viewpoints (camera at unit cube corners, looking at bbox center [0.5, 0.5, 0.5]):
- Top-left:     camera at [ 1,  1,  1]
- Top-right:    camera at [-1, -1, -1]
- Bottom-left:  camera at [-1,  1, -1]
- Bottom-right: camera at [ 1, -1,  1]

All renders are normalized: the part's bounding box is centered at [0.5, 0.5, 0.5] and the longest side maps to [0, 1].

Your task: generate executable CadQuery Python code that recreates this part geometry.

Requirements:
- Use standard CadQuery operations: Workplane, extrude, revolve, sweep, loft, union, cut, fillet, chamfer, hole, shell, etc.
- Store the final solid in a variable named `result`
- Do NOT include import statements (cadquery is pre-imported as `import cadquery as cq`)
- Do NOT include show_object() or any display calls
- Always make your best attempt — even for complex shapes, approximate geometry is better than refusing
- Output ONLY executable Python code, no explanation or markdown

Example:
result = (
    cq.Workplane("XY")
    .circle(10)
    .extrude(5)
    .faces(">Z").hole(4)
)"""

CADRILLE_SYSTEM_PROMPT = (
    "You are a CadQuery expert. Given a 2×2 grid of normalized multi-view renders "
    "of a mechanical part (four diagonal viewpoints: [1,1,1], [-1,-1,-1], [-1,1,-1], "
    "[1,-1,1]), write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

USER_PROMPT = "Generate CadQuery code to recreate this industrial part shown in the 4-view composite render."

QA_SYSTEM_PROMPT = """You are an expert CAD engineer. You will be shown a 2×2 composite image of a mechanical part (4 diagonal viewpoints: camera at [1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1], looking at bbox center [0.5, 0.5, 0.5]).

You will be given a list of numeric questions about the part. Answer each with a single number.

Rules:
- Output ONLY a JSON array of numbers, one per question, in the same order.
- No text, no keys, no explanation. Just the array.
- For yes/no questions, use 1 for yes and 0 for no.
- For count questions, use an integer (e.g. 12, not "twelve").
- For ratio questions, use a decimal (e.g. 2.5).
- For dimensional questions, assume mm unless the question specifies otherwise.

Example input: ["How many teeth?", "What is the module in mm?"]
Example output: [20, 2.5]"""

_local_cache: dict = {}


def _strip_fences(code: str) -> str:
    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.M)
    code = re.sub(r"```\s*$", "", code, flags=re.M)
    return code.strip()


def image_to_b64(pil_img) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── OpenAI ────────────────────────────────────────────────────────────────────


def call_openai(
    model: str, b64_img: str, api_key: str
) -> tuple[str | None, str | None]:
    import openai

    client = openai.OpenAI(api_key=api_key)
    try:
        # gpt-5.x uses max_completion_tokens; older models use max_tokens
        tok_param = (
            "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            **{tok_param: 2048},
            temperature=0.0,
        )
        return _strip_fences(resp.choices[0].message.content), None
    except Exception as e:
        return None, str(e)[:200]


# ── Local Qwen2-VL / Qwen2.5-VL ──────────────────────────────────────────────


def _load_local(model_path: str) -> dict:
    if model_path in _local_cache:
        return _local_cache[model_path]

    import json as _json

    import torch
    from transformers import AutoProcessor

    print(f"\nLoading {model_path} ...", flush=True)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model_type = ""
    cfg_path = (
        os.path.join(model_path, "config.json") if os.path.isdir(model_path) else None
    )
    if cfg_path and os.path.exists(cfg_path):
        try:
            model_type = _json.load(open(cfg_path)).get("model_type", "")
        except Exception:
            pass

    if model_type == "qwen2_5_vl":
        from transformers import Qwen2_5_VLForConditionalGeneration

        cls = Qwen2_5_VLForConditionalGeneration
    else:
        from transformers import Qwen2VLForConditionalGeneration

        cls = Qwen2VLForConditionalGeneration

    model = cls.from_pretrained(model_path, torch_dtype=dtype).to(device)
    model.eval()
    processor = AutoProcessor.from_pretrained(model_path)
    _local_cache[model_path] = {
        "model": model,
        "processor": processor,
        "device": device,
    }
    print("Model loaded.", flush=True)
    return _local_cache[model_path]


def call_local(
    model_path: str, pil_img, max_new_tokens: int = 2048, temperature: float = 0.0
) -> tuple[str | None, str | None]:
    try:
        import torch
        from qwen_vl_utils import process_vision_info
    except ImportError as e:
        return None, f"missing dep: {e}"

    try:
        state = _load_local(model_path)
        model = state["model"]
        processor = state["processor"]
        device = state["device"]

        messages = [
            {"role": "system", "content": CADRILLE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_img},
                    {"type": "text", "text": "Generate CadQuery code for this part."},
                ],
            },
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

        gen_kw: dict = {"max_new_tokens": max_new_tokens}
        if temperature > 0:
            gen_kw.update({"temperature": temperature, "do_sample": True})
        else:
            gen_kw["do_sample"] = False

        with torch.no_grad():
            out = model.generate(**inputs, **gen_kw)
        code = processor.decode(
            out[0][len(inputs["input_ids"][0]) :], skip_special_tokens=True
        )
        return _strip_fences(code), None
    except Exception as e:
        return None, str(e)[:300]


# ── Dispatch ──────────────────────────────────────────────────────────────────


def call_vlm(model: str, pil_img, api_key: str | None) -> tuple[str | None, str | None]:
    if model.startswith("local:"):
        return call_local(model[len("local:") :], pil_img)
    b64 = image_to_b64(pil_img)
    if model.startswith(("gpt", "o1", "o3")):
        key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("OPENAI_API_KEY1")
        )
        return call_openai(model, b64, key)
    raise ValueError(
        f"Unsupported model: {model}. Use 'local:<path>' for local models."
    )


# ── QA (image + questions → numeric answers) ─────────────────────────────────


def _parse_qa_answers(raw: str, n_expected: int) -> list[float] | None:
    """Extract a JSON array of numbers from model output. Returns None on shape/type mismatch."""
    import json as _json

    s = raw.strip()
    # strip code fences if present
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.M)
    s = re.sub(r"```\s*$", "", s, flags=re.M).strip()
    # grab first [...] block
    m = re.search(r"\[[^\[\]]*\]", s, flags=re.S)
    if not m:
        return None
    try:
        arr = _json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(arr, list) or len(arr) != n_expected:
        return None
    out: list[float] = []
    for x in arr:
        try:
            out.append(float(x))
        except Exception:
            return None
    return out


def call_openai_qa(
    model: str, b64_img: str, questions: list[str], api_key: str
) -> tuple[list[float] | None, str | None]:
    import openai

    client = openai.OpenAI(api_key=api_key)
    import json as _json

    user_text = (
        "Answer these questions about the part shown. "
        "Output ONLY a JSON array of numbers, same order:\n" + _json.dumps(questions)
    )
    try:
        tok_param = (
            "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            **{tok_param: 512},
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or ""
        arr = _parse_qa_answers(raw, len(questions))
        if arr is None:
            return None, f"parse_fail: {raw[:120]}"
        return arr, None
    except Exception as e:
        return None, str(e)[:200]


def call_vlm_qa(
    model: str, pil_img, questions: list[str], api_key: str | None
) -> tuple[list[float] | None, str | None]:
    """Ask a VLM numeric questions about a part image. Returns (answers, error)."""
    if not questions:
        return [], None
    if model.startswith("local:"):
        return None, "local QA not yet implemented"
    b64 = image_to_b64(pil_img)
    if model.startswith(("gpt", "o1", "o3")):
        key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("OPENAI_API_KEY1")
        )
        return call_openai_qa(model, b64, questions, key)
    raise ValueError(
        f"Unsupported model: {model}. Use 'local:<path>' for local models."
    )
