"""Bench model layer.

New code: use `get_adapter(model)` from `bench.models.registry`, plus the
prompt strings / parsers from `bench.models.prompts`.

Old call sites continue to work via the back-compat shims below.
"""

from __future__ import annotations

# Side-effect: register all built-in providers
from bench.models import providers as _providers  # noqa: F401
from bench.models.prompts import (
    CADRILLE_SYSTEM_PROMPT,
    EDIT_CODE_SYSTEM_PROMPT,
    EDIT_IMG_SYSTEM_PROMPT,
    QA_CODE_SYSTEM_PROMPT,
    QA_IMG_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    USER_PROMPT,
    build_edit_user_text,
    build_qa_user_text,
    parse_qa_answers,
    strip_fences,
)
from bench.models.registry import (
    ModelAdapter,
    get_adapter,
    list_models,
    register,
    register_prefix,
)

# Old name kept for back-compat with eval_qa.py and eval_qa_code.py
QA_SYSTEM_PROMPT = QA_IMG_SYSTEM_PROMPT
EDIT_VLM_SYSTEM_PROMPT = EDIT_IMG_SYSTEM_PROMPT


# ── Back-compat shims (used by old runners until refactored) ─────────────────


def _to_pil(img):
    """Normalize input (PIL / bytes / {'bytes': ...}) → PIL Image. Raises on bad type."""
    from PIL import Image as _PIL

    if hasattr(img, "save"):  # already PIL
        return img
    if isinstance(img, dict):
        if "bytes" not in img:
            raise TypeError(f"_to_pil: dict missing 'bytes' key (got keys={list(img)})")
        raw = img["bytes"]
    elif isinstance(img, (bytes, bytearray)):
        raw = img
    else:
        raise TypeError(f"_to_pil: unsupported image type {type(img).__name__}")
    import io as _io

    return _PIL.open(_io.BytesIO(raw))


def call_vlm(
    model: str, pil_img, api_key: str | None = None
) -> tuple[str | None, str | None]:
    """Image → CadQuery code (img2cq task)."""
    adapter = get_adapter(model)
    text, err = adapter.generate(
        SYSTEM_PROMPT, USER_PROMPT, images=[_to_pil(pil_img)], max_tokens=2048
    )
    if text is None:
        return None, err
    return strip_fences(text), None


def call_vlm_qa(
    model: str, pil_img, questions: list[str], api_key: str | None = None
) -> tuple[list[float] | None, str | None]:
    """Image + numeric questions → JSON array of numbers."""
    if not questions:
        return [], None
    adapter = get_adapter(model)
    user_text = build_qa_user_text(questions)
    raw, err = adapter.generate(
        QA_IMG_SYSTEM_PROMPT, user_text, images=[_to_pil(pil_img)], max_tokens=512
    )
    if raw is None:
        return None, err
    arr = parse_qa_answers(raw, len(questions))
    if arr is None:
        return None, f"parse_fail: {raw[:120]}"
    return arr, None


def call_llm_qa_code(
    model: str, code: str, questions: list[str], api_key: str | None = None
) -> tuple[list[float] | None, str | None]:
    """Code + numeric questions → JSON array of numbers."""
    if not questions:
        return [], None
    adapter = get_adapter(model)
    user_text = build_qa_user_text(questions, code=code)
    raw, err = adapter.generate(QA_CODE_SYSTEM_PROMPT, user_text, max_tokens=512)
    if raw is None:
        return None, err
    arr = parse_qa_answers(raw, len(questions))
    if arr is None:
        return None, f"parse_fail: {raw[:120]}"
    return arr, None


def call_edit_vlm(
    model: str, orig_code: str, instruction: str, pil_img, api_key: str | None = None
) -> tuple[str | None, str | None]:
    """Edit with vision (img + code + instruction → modified code)."""
    adapter = get_adapter(model)
    user_text = build_edit_user_text(orig_code, instruction)
    raw, err = adapter.generate(
        EDIT_IMG_SYSTEM_PROMPT, user_text, images=[_to_pil(pil_img)], max_tokens=4096
    )
    if raw is None:
        return None, err
    return strip_fences(raw), None


def call_edit_code(
    model: str, orig_code: str, instruction: str, api_key: str | None = None
) -> tuple[str | None, str | None]:
    """Edit code-only (code + instruction → modified code)."""
    adapter = get_adapter(model)
    user_text = build_edit_user_text(orig_code, instruction)
    raw, err = adapter.generate(EDIT_CODE_SYSTEM_PROMPT, user_text, max_tokens=4096)
    if raw is None:
        return None, err
    return strip_fences(raw), None


__all__ = [
    "ModelAdapter",
    "get_adapter",
    "register",
    "register_prefix",
    "list_models",
    "SYSTEM_PROMPT",
    "USER_PROMPT",
    "CADRILLE_SYSTEM_PROMPT",
    "QA_SYSTEM_PROMPT",
    "QA_IMG_SYSTEM_PROMPT",
    "QA_CODE_SYSTEM_PROMPT",
    "EDIT_CODE_SYSTEM_PROMPT",
    "EDIT_IMG_SYSTEM_PROMPT",
    "EDIT_VLM_SYSTEM_PROMPT",
    "call_vlm",
    "call_vlm_qa",
    "call_llm_qa_code",
    "call_edit_vlm",
    "call_edit_code",
    "strip_fences",
    "parse_qa_answers",
    "build_qa_user_text",
    "build_edit_user_text",
]
