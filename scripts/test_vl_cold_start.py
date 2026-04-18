#!/usr/bin/env python3
"""Test Qwen2.5-VL-7B cold-start capability for CadQuery generation.

Checks whether the base model can produce plausible CadQuery code from
a text description (no SFT) — determines RL cold-start feasibility.

Also optionally tests the vision path (screenshot -> description).

Usage:
    # text-only cold start test (fits 16GB GPU with 4-bit)
    uv run --with torch --with transformers --with accelerate \
           --with bitsandbytes --with qwen-vl-utils --with pillow \
           python scripts/test_vl_cold_start.py

    # include vision test with a screenshot
    uv run ... python scripts/test_vl_cold_start.py --vision

    # full precision (needs >16GB VRAM)
    uv run ... python scripts/test_vl_cold_start.py --no-4bit
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "data" / "benchmark"
SCREENSHOTS_DIR = ROOT / "data" / "benchmark_runs" / "20260219_005050"
MODEL_DIR = ROOT / "model" / "Qwen2.5-VL-7B-Instruct"

# ── test prompts (pulled from benchmark descriptions) ─────────────────────────
TEXT_PROMPTS = [
    {
        "name": "thick_spacer",
        "description": (
            "Thick Spacer. Create cylindrical base extrusion for spacer; "
            "Cut central through hole."
        ),
    },
    {
        "name": "box_with_beveled_corners",
        "description": (
            "Box With Beveled Corners. Create base box (extrusion); "
            "Apply beveled corners using chamfer operation on vertical edges."
        ),
    },
    {
        "name": "base_reinforcement_plate",
        "description": (
            "Base Reinforcement Plate. Create base rectangular plate (extrusion); "
            "Add four counterbored holes near corners; Add central through hole."
        ),
    },
]

SYSTEM_PROMPT = """\
You are a CadQuery expert. Given a mechanical part description, generate valid \
CadQuery Python code that builds the part.

Rules:
- Import cadquery as cq
- Use cq.Workplane as the entry point
- Assign the final result to a variable named `result`
- Output ONLY the Python code block, no explanation
"""

TEXT_USER_TEMPLATE = """\
Generate CadQuery code for this part:

{description}
"""

VISION_USER_TEXT = """\
This is a 3D CAD part rendered from an isometric view.
Describe what kind of mechanical part this is and write CadQuery code to \
approximate it.
Output ONLY the Python code block.
"""

# ── helpers ───────────────────────────────────────────────────────────────────

CQ_PATTERNS = [
    r"import cadquery",
    r"cq\.Workplane",
    r"\.box\(",
    r"\.cylinder\(",
    r"\.circle\(",
    r"\.extrude\(",
    r"\.cut\(",
    r"\.fillet\(",
    r"\.chamfer\(",
    r"result\s*=",
]


def score_output(text: str) -> dict:
    hits = [p for p in CQ_PATTERNS if re.search(p, text)]
    code_block = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    raw_code = code_block.group(1) if code_block else text

    parseable = False
    try:
        ast.parse(raw_code)
        parseable = True
    except SyntaxError:
        pass

    return {
        "pattern_hits": len(hits),
        "patterns_found": hits,
        "has_code_block": code_block is not None,
        "parseable": parseable,
        "total_score": len(hits) + (2 if parseable else 0),
    }


def build_text_messages(description: str) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": TEXT_USER_TEMPLATE.format(description=description),
        },
    ]


def build_vision_messages(image_path: Path) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": VISION_USER_TEXT},
            ],
        },
    ]


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=str(MODEL_DIR))
    parser.add_argument("--no-4bit", action="store_true", help="disable 4-bit quant")
    parser.add_argument("--vision", action="store_true", help="run vision test too")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()

    try:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        from qwen_vl_utils import process_vision_info
    except ImportError as e:
        print(f"Missing dep: {e}")
        print(
            "Install with:\n"
            "  uv run --with torch --with transformers --with accelerate "
            "--with bitsandbytes --with qwen-vl-utils --with pillow "
            "python scripts/test_vl_cold_start.py"
        )
        sys.exit(1)

    if not torch.cuda.is_available():
        print("WARN: no CUDA GPU found, running on CPU (slow)")

    use_4bit = not args.no_4bit and torch.cuda.is_available()

    print(f"Loading {args.model_dir} (4-bit={use_4bit}) ...")
    load_kwargs = {"device_map": "auto"}
    if use_4bit:
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
    else:
        load_kwargs["torch_dtype"] = torch.bfloat16

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model_dir, **load_kwargs
    )
    processor = AutoProcessor.from_pretrained(args.model_dir)
    print("Model loaded.\n")

    def run_inference(messages: list) -> str:
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs or None,
            videos=video_inputs or None,
            padding=True,
            return_tensors="pt",
        )
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            out_ids = model.generate(**inputs, max_new_tokens=args.max_new_tokens)

        trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], out_ids)]
        return processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

    # ── text tests ────────────────────────────────────────────────────────────
    print("=" * 70)
    print("TEXT → CadQuery cold-start tests")
    print("=" * 70)

    total_score = 0
    max_possible = len(TEXT_PROMPTS) * (len(CQ_PATTERNS) + 2)

    for i, prompt in enumerate(TEXT_PROMPTS, 1):
        print(f"\n[{i}/{len(TEXT_PROMPTS)}] {prompt['name']}")
        print(f"  desc: {prompt['description'][:80]}...")
        messages = build_text_messages(prompt["description"])
        output = run_inference(messages)
        s = score_output(output)
        total_score += s["total_score"]

        print(f"  patterns matched : {s['pattern_hits']}/{len(CQ_PATTERNS)}")
        print(f"  has code block   : {s['has_code_block']}")
        print(f"  ast.parse OK     : {s['parseable']}")
        print(f"  score            : {s['total_score']}")
        print("  --- output (first 20 lines) ---")
        for line in output.splitlines()[:20]:
            print("  " + line)
        print()

    pct = total_score / max_possible * 100
    print("=" * 70)
    print(f"TEXT TOTAL SCORE: {total_score}/{max_possible} ({pct:.0f}%)")
    if pct >= 60:
        print("VERDICT: Sufficient for RL cold start (model understands CadQuery)")
    elif pct >= 30:
        print("VERDICT: Marginal — minimal SFT cold start recommended before RL")
    else:
        print("VERDICT: Poor — needs SFT cold start before RL")
    print("=" * 70)

    # ── vision test ───────────────────────────────────────────────────────────
    if args.vision:
        img_path = SCREENSHOTS_DIR / "panel" / "screenshots" / "panel_isometric.png"
        if not img_path.exists():
            print(f"\nSkipping vision test: {img_path} not found")
        else:
            print(f"\nVISION test: {img_path.name}")
            messages = build_vision_messages(img_path)
            output = run_inference(messages)
            s = score_output(output)
            print(f"  patterns matched : {s['pattern_hits']}/{len(CQ_PATTERNS)}")
            print(f"  parseable        : {s['parseable']}")
            print("  --- output (first 20 lines) ---")
            for line in output.splitlines()[:20]:
                print("  " + line)


if __name__ == "__main__":
    main()
