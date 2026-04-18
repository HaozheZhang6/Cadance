"""Security tests for path validation and executor timeout.

Tests the security hardening features added to prevent:
- Path traversal attacks
- Denial of service via infinite loops
"""

import pytest

from src.cad.intent_decomposition.observability.trace_storage import (
    resolve_safe_path,
    validate_run_id,
)

# Check if cadquery available (nlopt missing on aarch64)
try:
    import cadquery  # noqa: F401

    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False


class TestValidateRunId:
    """Tests for validate_run_id function."""

    def test_valid_timestamp_id(self):
        """Standard timestamp IDs should be valid."""
        # Should not raise
        validate_run_id("2026-01-29_143052")

    def test_valid_alphanumeric_id(self):
        """Alphanumeric IDs should be valid."""
        validate_run_id("run123")
        validate_run_id("test_run")
        validate_run_id("my-run-id")

    def test_valid_with_underscores_and_hyphens(self):
        """IDs with underscores and hyphens should be valid."""
        validate_run_id("run_123-test")
        validate_run_id("baseline_train")
        validate_run_id("latest_eval")

    def test_rejects_empty_id(self):
        """Empty ID should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_run_id("")

    def test_rejects_path_traversal_dotdot(self):
        """Path traversal with .. should be rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_run_id("../etc/passwd")

    def test_rejects_path_traversal_slash(self):
        """Path with forward slash should be rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_run_id("foo/bar")

    def test_rejects_path_traversal_backslash(self):
        """Path with backslash should be rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_run_id("foo\\bar")

    def test_rejects_special_characters(self):
        """IDs with special characters should be rejected."""
        invalid_ids = [
            "run@123",
            "test$var",
            "my run",  # space
            "run!test",
            "foo;bar",
            "$(whoami)",
            "`ls`",
        ]
        for run_id in invalid_ids:
            with pytest.raises(ValueError):
                validate_run_id(run_id)

    def test_rejects_dot_only(self):
        """Single dot should be rejected."""
        with pytest.raises(ValueError):
            validate_run_id(".")


class TestResolveSafePath:
    """Tests for resolve_safe_path function."""

    def test_valid_subdirectory(self, tmp_path):
        """Valid subdirectory should resolve correctly."""
        base = tmp_path / "base"
        base.mkdir()

        result = resolve_safe_path(base, "subdir")
        assert str(result).startswith(str(base))

    def test_valid_nested_subdirectory(self, tmp_path):
        """Nested subdirectory should resolve correctly."""
        base = tmp_path / "base"
        base.mkdir()

        result = resolve_safe_path(base, "sub1/sub2")
        assert str(result).startswith(str(base.resolve()))

    def test_rejects_path_traversal(self, tmp_path):
        """Path traversal should be rejected."""
        base = tmp_path / "base"
        base.mkdir()

        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_safe_path(base, "../escape")

    def test_rejects_absolute_path_outside(self, tmp_path):
        """Absolute path outside base should be rejected."""
        base = tmp_path / "base"
        base.mkdir()

        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_safe_path(base, "/etc/passwd")

    def test_allows_path_that_looks_like_traversal_but_isnt(self, tmp_path):
        """Path with .. in name (not traversal) should work."""
        base = tmp_path / "base"
        base.mkdir()

        # This is a valid filename, not traversal - should not raise
        resolve_safe_path(base, "file..txt")


class TestExecutorTimeout:
    """Tests for executor timeout configuration.

    Note: We don't test actual timeouts here as that would make tests slow.
    These tests verify the timeout is configurable and fast code works.
    """

    def test_executor_accepts_timeout_parameter(self):
        """CADExecutor should accept timeout_seconds parameter."""
        from src.cad.intent_decomposition.execution.executor import CADExecutor

        executor = CADExecutor(timeout_seconds=5.0)
        assert executor.timeout_seconds == 5.0

    def test_executor_default_timeout(self):
        """CADExecutor should have a default timeout."""
        from src.cad.intent_decomposition.execution.executor import CADExecutor

        executor = CADExecutor()
        assert executor.timeout_seconds > 0

    @pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery unavailable")
    def test_fast_code_completes_successfully(self):
        """Fast code should complete successfully within timeout."""
        from src.cad.intent_decomposition.execution.executor import CADExecutor

        executor = CADExecutor(timeout_seconds=30.0)

        code = """
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = executor.execute(code)

        assert result.success is True
        assert result.geometry_properties["volume"] == pytest.approx(1000.0, rel=0.01)


class TestTraceStoragePathValidation:
    """Integration tests for TraceStore path validation."""

    def test_start_run_with_valid_id(self, tmp_path):
        """start_run with valid ID should work."""
        from src.cad.intent_decomposition.observability.trace_storage import TraceStore

        store = TraceStore(base_dir=tmp_path)
        run_id = store.start_run("valid_run_123")

        assert run_id == "valid_run_123"
        assert (tmp_path / "valid_run_123").exists()

    def test_start_run_rejects_traversal(self, tmp_path):
        """start_run should reject path traversal attempts."""
        from src.cad.intent_decomposition.observability.trace_storage import TraceStore

        store = TraceStore(base_dir=tmp_path)

        with pytest.raises(ValueError, match="path traversal"):
            store.start_run("../escape")

    def test_start_run_rejects_special_chars(self, tmp_path):
        """start_run should reject special characters."""
        from src.cad.intent_decomposition.observability.trace_storage import TraceStore

        store = TraceStore(base_dir=tmp_path)

        with pytest.raises(ValueError):
            store.start_run("run$(whoami)")

    def test_start_run_generates_valid_id_when_none(self, tmp_path):
        """start_run without ID should generate valid timestamp."""
        from src.cad.intent_decomposition.observability.trace_storage import TraceStore

        store = TraceStore(base_dir=tmp_path)
        run_id = store.start_run()

        # Should match timestamp pattern
        assert run_id is not None
        # Should have created directory
        assert (tmp_path / run_id).exists()
