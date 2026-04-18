"""Tests for gateway protocol types."""

from src.tools.gateway.protocol import ErrorCategory, ExecutionResult, ToolBackend


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_error_category_values(self):
        """All enum members exist and are string-valued."""
        assert ErrorCategory.NONE.value == "none"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.CRASH.value == "crash"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.SYNTAX.value == "syntax"
        assert ErrorCategory.GEOMETRY.value == "geometry"
        assert ErrorCategory.UNKNOWN.value == "unknown"
        # Verify 7 members total
        assert len(ErrorCategory) == 7


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_execution_result_success_to_dict(self):
        """Success result serializes correctly."""
        result = ExecutionResult(
            success=True,
            geometry_props={"volume": 100.0, "surface_area": 50.0},
            step_path="/tmp/output.step",
            execution_time_ms=123.45,
        )
        d = result.to_dict()

        assert d["success"] is True
        assert d["geometry_props"] == {"volume": 100.0, "surface_area": 50.0}
        assert d["step_path"] == "/tmp/output.step"
        assert d["error_category"] == "none"
        assert d["error_message"] is None
        assert d["execution_time_ms"] == 123.45

    def test_execution_result_error_to_dict(self):
        """Error result serializes category as string."""
        result = ExecutionResult(
            success=False,
            error_category=ErrorCategory.TIMEOUT,
            error_message="Execution exceeded 30s limit",
            execution_time_ms=30000.0,
        )
        d = result.to_dict()

        assert d["success"] is False
        assert d["error_category"] == "timeout"
        assert d["error_message"] == "Execution exceeded 30s limit"
        assert d["geometry_props"] == {}
        assert d["step_path"] is None


class TestToolBackend:
    """Tests for ToolBackend protocol."""

    def test_tool_backend_protocol_runtime_checkable(self):
        """Protocol works with isinstance at runtime."""

        class MockBackend:
            """Mock implementation of ToolBackend."""

            @property
            def backend_name(self) -> str:
                return "mock"

            def execute(
                self, code: str, timeout_seconds: float = 30.0
            ) -> ExecutionResult:
                return ExecutionResult(success=True)

            def is_available(self) -> bool:
                return True

            def compute_iou(
                self,
                generated_code: str,
                ground_truth_code: str,
                timeout_seconds: float = 60.0,
            ):
                return None

        backend = MockBackend()
        assert isinstance(backend, ToolBackend)

    def test_non_backend_fails_isinstance(self):
        """Non-implementing class fails isinstance check."""

        class NotABackend:
            pass

        obj = NotABackend()
        assert not isinstance(obj, ToolBackend)
