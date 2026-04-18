"""Tests for ToolGateway registry."""

from src.tools.gateway import (
    ErrorCategory,
    ExecutionResult,
    IoUResult,
    ToolBackend,
    ToolGateway,
)


class MockBackend:
    """Mock backend for testing ToolGateway dispatch."""

    def __init__(self, name: str = "mock"):
        self._name = name
        self.execute_calls: list[tuple[str, float]] = []
        self.compute_iou_calls: list[tuple[str, str, float]] = []

    @property
    def backend_name(self) -> str:
        return self._name

    def execute(self, code: str, timeout_seconds: float = 30.0) -> ExecutionResult:
        self.execute_calls.append((code, timeout_seconds))
        return ExecutionResult(success=True, geometry_props={"test": True})

    def is_available(self) -> bool:
        return True

    def compute_iou(
        self,
        generated_code: str,
        ground_truth_code: str,
        timeout_seconds: float = 60.0,
    ) -> IoUResult | None:
        self.compute_iou_calls.append(
            (generated_code, ground_truth_code, timeout_seconds)
        )
        return IoUResult(
            iou_score=0.95,
            intersection_volume=950.0,
            union_volume=1000.0,
            generated_volume=1000.0,
            ground_truth_volume=1000.0,
        )


class TestToolGateway:
    """Tests for ToolGateway class."""

    def test_gateway_register_and_get(self):
        """Register backend, verify get_backend returns it."""
        gateway = ToolGateway()
        backend = MockBackend("cadquery")

        gateway.register("cadquery", backend)
        result = gateway.get_backend("cadquery")

        assert result is backend

    def test_gateway_get_unknown_returns_none(self):
        """get_backend for unregistered tool returns None."""
        gateway = ToolGateway()

        result = gateway.get_backend("unknown")

        assert result is None

    def test_gateway_execute_dispatches(self):
        """execute() dispatches to registered backend."""
        gateway = ToolGateway()
        backend = MockBackend("cadquery")
        gateway.register("cadquery", backend)

        result = gateway.execute("cadquery", "show(box)")

        assert result.success is True
        assert result.geometry_props == {"test": True}
        assert len(backend.execute_calls) == 1
        assert backend.execute_calls[0][0] == "show(box)"

    def test_gateway_execute_unknown_returns_error(self):
        """execute() for unknown tool returns error with VALIDATION category."""
        gateway = ToolGateway()

        result = gateway.execute("unknown", "code")

        assert result.success is False
        assert result.error_category == ErrorCategory.VALIDATION
        assert "unknown" in result.error_message.lower()

    def test_gateway_list_tools(self):
        """list_tools() returns registered tool_ids."""
        gateway = ToolGateway()
        gateway.register("cadquery", MockBackend("cadquery"))
        gateway.register("openscad", MockBackend("openscad"))

        tools = gateway.list_tools()

        assert set(tools) == {"cadquery", "openscad"}

    def test_mock_backend_implements_protocol(self):
        """Verify MockBackend satisfies ToolBackend protocol."""
        backend = MockBackend()
        assert isinstance(backend, ToolBackend)

    def test_gateway_compute_iou_dispatches(self):
        """compute_iou() dispatches to registered backend."""
        gateway = ToolGateway()
        backend = MockBackend("cadquery")
        gateway.register("cadquery", backend)

        result = gateway.compute_iou(
            "cadquery",
            generated_code="gen_code",
            ground_truth_code="gt_code",
        )

        assert result is not None
        assert result.iou_score == 0.95
        assert len(backend.compute_iou_calls) == 1
        assert backend.compute_iou_calls[0][0] == "gen_code"
        assert backend.compute_iou_calls[0][1] == "gt_code"

    def test_gateway_compute_iou_unknown_returns_none(self):
        """compute_iou() for unknown tool returns None."""
        gateway = ToolGateway()

        result = gateway.compute_iou(
            "unknown",
            generated_code="gen_code",
            ground_truth_code="gt_code",
        )

        assert result is None

    def test_gateway_compute_iou_with_timeout(self):
        """compute_iou() passes timeout to backend."""
        gateway = ToolGateway()
        backend = MockBackend("cadquery")
        gateway.register("cadquery", backend)

        gateway.compute_iou(
            "cadquery",
            generated_code="gen",
            ground_truth_code="gt",
            timeout_seconds=120.0,
        )

        assert backend.compute_iou_calls[0][2] == 120.0
