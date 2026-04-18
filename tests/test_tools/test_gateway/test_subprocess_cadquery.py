"""Tests for SubprocessCadQueryBackend."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from src.tools.gateway.backends import SubprocessCadQueryBackend
from src.tools.gateway.protocol import (
    ErrorCategory,
    ExecutionResult,
    IoUResult,
    ToolBackend,
)


class TestSubprocessCadQueryBackend:
    """Tests for SubprocessCadQueryBackend."""

    def test_backend_name(self) -> None:
        """Backend name is cadquery-subprocess."""
        backend = SubprocessCadQueryBackend()
        assert backend.backend_name == "cadquery-subprocess"

    def test_implements_tool_backend_protocol(self) -> None:
        """Backend implements ToolBackend protocol."""
        backend = SubprocessCadQueryBackend()
        assert isinstance(backend, ToolBackend)

    def test_execute_returns_execution_result(self) -> None:
        """Execute returns ExecutionResult from valid JSON."""
        backend = SubprocessCadQueryBackend()
        response = {
            "success": True,
            "geometry_props": {"volume": 6000.0},
            "step_path": "/tmp/test.step",
            "error_category": "none",
            "error_message": None,
            "execution_time_ms": 123.45,
        }

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=json.dumps(response),
                stderr="",
            )

            result = backend.execute("import cadquery")

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.geometry_props == {"volume": 6000.0}
        assert result.error_category == ErrorCategory.NONE

    def test_execute_timeout_returns_timeout_error(self) -> None:
        """Execute returns TIMEOUT error on TimeoutExpired."""
        backend = SubprocessCadQueryBackend(timeout_seconds=5.0)

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

            result = backend.execute("while True: pass")

        assert result.success is False
        assert result.error_category == ErrorCategory.TIMEOUT
        assert "timed out" in result.error_message.lower()

    def test_execute_invalid_json_returns_validation_error(self) -> None:
        """Execute returns VALIDATION error on invalid JSON from executor."""
        backend = SubprocessCadQueryBackend()

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout="not valid json {{{",
                stderr="",
            )

            result = backend.execute("import cadquery")

        assert result.success is False
        assert result.error_category == ErrorCategory.VALIDATION
        assert "invalid json" in result.error_message.lower()

    def test_execute_crash_returns_crash_error(self) -> None:
        """Execute returns CRASH error on subprocess failure."""
        backend = SubprocessCadQueryBackend()

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=1,
                stdout="",
                stderr="Segmentation fault",
            )

            result = backend.execute("import cadquery")

        assert result.success is False
        assert result.error_category == ErrorCategory.CRASH

    def test_python_path_unix(self) -> None:
        """Python path uses bin/python on Unix."""
        backend = SubprocessCadQueryBackend(venv_path=Path("/test/venv"))

        with mock.patch("sys.platform", "linux"):
            path = backend._get_python_path()

        assert path == Path("/test/venv/bin/python")

    def test_python_path_windows(self) -> None:
        """Python path uses Scripts/python.exe on Windows."""
        backend = SubprocessCadQueryBackend(venv_path=Path("C:/test/venv"))

        with mock.patch("sys.platform", "win32"):
            path = backend._get_python_path()

        assert path == Path("C:/test/venv/Scripts/python.exe")

    def test_ensure_venv_creates_on_missing(self) -> None:
        """Ensure venv calls create when venv missing."""
        backend = SubprocessCadQueryBackend(venv_path=Path("/nonexistent/venv"))

        with (
            mock.patch.object(backend, "_get_python_path") as mock_py,
            mock.patch.object(backend, "_create_venv") as mock_create,
        ):
            mock_path = mock.Mock()
            mock_path.exists.return_value = False
            mock_py.return_value = mock_path

            backend._ensure_venv()

        mock_create.assert_called_once()

    def test_ensure_venv_skips_create_when_healthy(self) -> None:
        """Ensure venv skips create when venv exists and is healthy."""
        backend = SubprocessCadQueryBackend(venv_path=Path("/existing/venv"))

        with (
            mock.patch.object(backend, "_get_python_path") as mock_py,
            mock.patch.object(backend, "_venv_is_healthy", return_value=True),
            mock.patch.object(backend, "_create_venv") as mock_create,
        ):
            mock_path = mock.Mock()
            mock_path.exists.return_value = True
            mock_py.return_value = mock_path

            backend._ensure_venv()

        mock_create.assert_not_called()

    def test_ensure_venv_recreates_on_broken_venv(self) -> None:
        """Ensure venv recreates when python exists but is broken."""
        backend = SubprocessCadQueryBackend(venv_path=Path("/broken/venv"))

        with (
            mock.patch.object(backend, "_get_python_path") as mock_py,
            mock.patch.object(backend, "_venv_is_healthy", return_value=False),
            mock.patch.object(backend, "_create_venv") as mock_create,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.shutil"
            ) as mock_shutil,
        ):
            mock_path = mock.Mock()
            mock_path.exists.return_value = True
            mock_py.return_value = mock_path

            backend._ensure_venv()

        mock_shutil.rmtree.assert_called_once_with(
            Path("/broken/venv"), ignore_errors=True
        )
        mock_create.assert_called_once()

    def test_venv_is_healthy_returns_false_on_crash(self) -> None:
        """Health check returns False when python crashes."""
        backend = SubprocessCadQueryBackend()

        with mock.patch(
            "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
        ) as mock_run:
            mock_run.return_value = mock.Mock(returncode=-6)  # SIGABRT
            assert backend._venv_is_healthy(Path("/some/python")) is False

    def test_venv_is_healthy_returns_true_on_success(self) -> None:
        """Health check returns True when python runs OK."""
        backend = SubprocessCadQueryBackend()

        with mock.patch(
            "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
        ) as mock_run:
            mock_run.return_value = mock.Mock(returncode=0)
            assert backend._venv_is_healthy(Path("/some/python")) is True

    def test_create_venv_uses_uv(self, tmp_path: Path) -> None:
        """_create_venv uses uv venv + pip bootstrap + pip install."""
        venv_dir = tmp_path / "cadquery" / ".venv"
        backend = SubprocessCadQueryBackend(venv_path=venv_dir)

        with (
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.shutil.which",
                return_value="/usr/local/bin/uv",
            ),
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            backend._create_venv()

        assert mock_run.call_count == 3
        # First call: uv venv
        venv_call = mock_run.call_args_list[0]
        assert venv_call[0][0][:3] == ["/usr/local/bin/uv", "venv", str(venv_dir)]
        # Second call: uv pip install pip (bootstrap)
        pip_bootstrap = mock_run.call_args_list[1]
        assert pip_bootstrap[0][0][:3] == ["/usr/local/bin/uv", "pip", "install"]
        assert "pip" in pip_bootstrap[0][0]
        # Third call: pip install cadquery
        pip_install = mock_run.call_args_list[2]
        assert pip_install[0][0][0].endswith("python")
        assert "-m" in pip_install[0][0]
        assert "pip" in pip_install[0][0]

    def test_create_venv_raises_without_uv(self, tmp_path: Path) -> None:
        """_create_venv raises RuntimeError when uv not on PATH."""
        venv_dir = tmp_path / "cadquery" / ".venv"
        backend = SubprocessCadQueryBackend(venv_path=venv_dir)

        with mock.patch(
            "src.tools.gateway.backends.subprocess_cadquery.shutil.which",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="uv not found"):
                backend._create_venv()

    def test_categorize_error_syntax(self) -> None:
        """Categorize SyntaxError as SYNTAX."""
        backend = SubprocessCadQueryBackend()
        category = backend._categorize_error(1, "SyntaxError: invalid syntax")
        assert category == ErrorCategory.SYNTAX

    def test_categorize_error_import(self) -> None:
        """Categorize ImportError as VALIDATION."""
        backend = SubprocessCadQueryBackend()
        category = backend._categorize_error(1, "ImportError: No module named 'foo'")
        assert category == ErrorCategory.VALIDATION

    def test_categorize_error_default_crash(self) -> None:
        """Default error category is CRASH."""
        backend = SubprocessCadQueryBackend()
        category = backend._categorize_error(1, "Unknown error occurred")
        assert category == ErrorCategory.CRASH

    def test_executor_path_exists(self) -> None:
        """Executor path points to existing file."""
        backend = SubprocessCadQueryBackend()
        path = backend._get_executor_path()
        assert path.exists(), f"Executor not found at {path}"
        assert path.name == "executor.py"

    def test_compute_iou_returns_iou_result(self) -> None:
        """compute_iou returns IoUResult from valid JSON."""
        backend = SubprocessCadQueryBackend()
        response = {
            "success": True,
            "iou_score": 0.95,
            "iou_result": {
                "intersection_volume": 950.0,
                "union_volume": 1000.0,
            },
            "generated_props": {"volume": 1000.0},
            "ground_truth_props": {"volume": 1000.0},
            "execution_time_ms": 100.0,
        }

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=json.dumps(response),
                stderr="",
            )

            result = backend.compute_iou("gen_code", "gt_code")

        assert isinstance(result, IoUResult)
        assert result.iou_score == 0.95
        assert result.intersection_volume == 950.0
        assert result.union_volume == 1000.0

    def test_compute_iou_timeout_returns_none(self) -> None:
        """compute_iou returns None on timeout."""
        backend = SubprocessCadQueryBackend(timeout_seconds=5.0)

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

            result = backend.compute_iou("gen_code", "gt_code")

        assert result is None

    def test_compute_iou_failure_returns_none(self) -> None:
        """compute_iou returns None on execution failure."""
        backend = SubprocessCadQueryBackend()
        response = {
            "success": False,
            "error": "Execution failed",
        }

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=json.dumps(response),
                stderr="",
            )

            result = backend.compute_iou("gen_code", "gt_code")

        assert result is None

    def test_compute_iou_sends_correct_mode(self) -> None:
        """compute_iou sends mode=iou in request."""
        backend = SubprocessCadQueryBackend()
        response = {
            "success": True,
            "iou_score": 1.0,
            "iou_result": {"intersection_volume": 1000, "union_volume": 1000},
            "generated_props": {},
            "ground_truth_props": {},
        }

        mock_executor_path = mock.MagicMock()
        mock_executor_path.exists.return_value = True

        with (
            mock.patch.object(backend, "_ensure_venv") as mock_venv,
            mock.patch.object(backend, "_get_executor_path") as mock_exec,
            mock.patch(
                "src.tools.gateway.backends.subprocess_cadquery.subprocess.run"
            ) as mock_run,
        ):
            mock_venv.return_value = Path("/fake/venv/bin/python")
            mock_exec.return_value = mock_executor_path
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=json.dumps(response),
                stderr="",
            )

            backend.compute_iou("gen_code", "gt_code")

        # Check that the input JSON contains mode=iou
        call_args = mock_run.call_args
        input_data = json.loads(call_args.kwargs["input"])
        assert input_data["mode"] == "iou"
        assert input_data["generated_code"] == "gen_code"
        assert input_data["ground_truth_code"] == "gt_code"
