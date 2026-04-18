"""Tests for LLM call logger path and file format."""

from src.cad.intent_decomposition.observability.llm_call_logger import (
    close_call_logger,
    init_call_logger,
)


def test_init_call_logger_uses_screenshot_env_parent(monkeypatch, tmp_path) -> None:
    close_call_logger()
    run_dir = tmp_path / "20260213_999999"
    screenshot_dir = run_dir / "screenshots"
    monkeypatch.setenv("VISION_SCREENSHOT_DIR", str(screenshot_dir))

    logger = init_call_logger()
    try:
        assert logger.run_dir == run_dir
    finally:
        close_call_logger()


def test_log_file_extension_is_log(monkeypatch, tmp_path) -> None:
    close_call_logger()
    run_dir = tmp_path / "20260213_888888"
    monkeypatch.delenv("VISION_SCREENSHOT_DIR", raising=False)
    logger = init_call_logger(run_dir=run_dir)
    try:
        path = logger.log(
            agent="code_gen",
            prompt="p",
            response="r",
            system_prompt="s",
        )
        assert path.suffix == ".log"
    finally:
        close_call_logger()
