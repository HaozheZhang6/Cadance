"""Tests for run_resume_from_ops_loop helper functions."""

from pathlib import Path

from scripts.run_resume_from_ops_loop import (
    _extract_pipeline_lines,
    _write_pipeline_logs,
)


def test_extract_pipeline_lines_filters_expected_markers() -> None:
    stdout = "\n".join(
        [
            "some noise",
            "[OPS_GEN] Pipeline succeeded, confidence=0.77",
            "Vision evaluation completed: 3 attempts",
        ]
    )
    stderr = "LLM call log summary: 14 calls -> data/logs/x/summary.json"

    lines = _extract_pipeline_lines(stdout, stderr)

    assert "[OPS_GEN] Pipeline succeeded, confidence=0.77" in lines
    assert "Vision evaluation completed: 3 attempts" in lines
    assert "LLM call log summary: 14 calls -> data/logs/x/summary.json" in lines
    assert "some noise" not in lines


def test_write_pipeline_logs_writes_per_run_and_global(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260213_161350"
    run_dir.mkdir(parents=True)
    logs_root = tmp_path

    per_run, global_log = _write_pipeline_logs(
        run_dir=run_dir,
        logs_root=logs_root,
        iteration=2,
        exit_code=1,
        duration_seconds=12.34,
        pipeline_lines=["[OPS_GEN] fail example"],
    )

    assert per_run.exists()
    assert global_log.exists()
    assert "[OPS_GEN] fail example" in per_run.read_text(encoding="utf-8")
    history_text = global_log.read_text(encoding="utf-8")
    assert "iteration=2" in history_text
    assert "exit_code=1" in history_text
