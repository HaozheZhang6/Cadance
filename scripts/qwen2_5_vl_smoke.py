#!/usr/bin/env python3
"""Minimal Qwen2.5-VL-7B smoke test on local hardware.

Uses ``torch_dtype='auto'`` and ``device_map='auto'``; on CUDA this typically
loads BF16 weights unless explicit int8/int4 quantization is configured.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _make_test_image():
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - handled by user environment
        _fail(f"Pillow is required for the synthetic image: {exc}")

    img = Image.new("RGB", (224, 224), color=(40, 60, 90))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 184, 184], outline=(220, 220, 220), width=4)
    return img


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        default="model/Qwen2.5-VL-7B-Instruct",
        help="Local path to the model directory.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=64,
        help="Max tokens to generate.",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Allow CPU fallback (not bf16).",
    )
    args = parser.parse_args()

    try:
        import torch
    except Exception as exc:  # pragma: no cover - handled by user environment
        _fail(f"PyTorch is required: {exc}")

    if not Path(args.model_dir).exists():
        _fail(f"Model directory not found: {args.model_dir}")

    use_cuda = torch.cuda.is_available()
    if not use_cuda and not args.cpu:
        _fail("CUDA GPU not available. Use --cpu to override.")

    try:
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
    except Exception as exc:  # pragma: no cover - handled by user environment
        _fail(f"transformers is required: {exc}")

    try:
        from qwen_vl_utils import process_vision_info
    except Exception as exc:  # pragma: no cover - handled by user environment
        _fail(f"qwen-vl-utils is required: {exc}")

    dtype = torch.bfloat16 if use_cuda and not args.cpu else None

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model_dir,
        torch_dtype=dtype,
        device_map="auto",
    )

    if use_cuda and not args.cpu:
        if next(model.parameters()).device.type != "cuda":
            _fail("Model did not load onto CUDA device. Check device_map.")

    processor = AutoProcessor.from_pretrained(args.model_dir)

    image = _make_test_image()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "Describe the image."},
            ],
        }
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
    )

    if use_cuda and not args.cpu:
        inputs = inputs.to("cuda")

    generated_ids = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )

    print(output_text[0].strip())


if __name__ == "__main__":
    main()
