"""Tests for CadQueryExecTool."""

from pathlib import Path

import pytest

# Skip entire module if cadquery unavailable (nlopt missing on aarch64)
pytest.importorskip("cadquery")

from src.cad.comparator import GeometricComparator
from src.tools.base import ToolResult
from src.tools.cadquery_tool import CadQueryExecTool
from tests.test_tools.test_cadquery.harness.runner import EvaluationHarness


class TestCadQueryExecTool:
    """Tests for CadQueryExecTool."""

    @pytest.fixture
    def tool(self):
        """Create CadQuery tool instance."""
        return CadQueryExecTool(backend="mock")

    def test_tool_creation(self, tool):
        """Tool should be creatable."""
        assert tool is not None
        assert tool.name == "CadQuery"

    def test_tool_has_capabilities(self, tool):
        """Tool should have capabilities defined."""
        caps = tool.capabilities
        assert len(caps) > 0
        assert caps[0].name == "execute_cadquery_code"

    def test_tool_is_deterministic(self, tool):
        """Tool should report determinism."""
        assert tool.is_deterministic is True

    def test_tool_has_cost_estimate(self, tool):
        """Tool should have cost estimate."""
        assert 0.0 <= tool.cost_estimate <= 1.0

    def test_validate_valid_inputs(self, tool):
        """Tool should validate correct inputs."""
        inputs = {
            "code": "import cadquery as cq\nresult = cq.Workplane('XY').box(100, 50, 30)",
        }
        assert tool.validate_inputs(inputs) is True

    def test_validate_invalid_inputs_missing_code(self, tool):
        """Tool should reject inputs without code."""
        inputs = {"export_format": "json"}
        assert tool.validate_inputs(inputs) is False

    def test_validate_invalid_inputs_empty_code(self, tool):
        """Tool should reject empty code."""
        inputs = {"code": ""}
        assert tool.validate_inputs(inputs) is False

    def test_validate_invalid_inputs_not_string(self, tool):
        """Tool should reject non-string code."""
        inputs = {"code": 123}
        assert tool.validate_inputs(inputs) is False

    def test_execute_returns_tool_result(self, tool):
        """Tool should return ToolResult on execute."""
        inputs = {
            "code": "import cadquery as cq\nresult = cq.Workplane('XY').box(100, 50, 30)",
        }
        result = tool.execute(inputs)

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "geometry_id" in result.data

    def test_execute_with_invalid_inputs(self, tool):
        """Tool should fail gracefully with invalid inputs."""
        inputs = {"invalid": "data"}
        result = tool.execute(inputs)

        assert result.success is False
        assert result.error is not None

    def test_mock_backend_returns_placeholder(self, tool):
        """Mock backend should return placeholder data."""
        inputs = {"code": "cq.Workplane('XY').box(100, 50, 30)"}
        result = tool.execute(inputs)

        assert result.success is True
        assert result.data.get("backend") == "mock"
        assert result.data.get("code_received") is True

    def test_real_backend_not_implemented(self):
        """Real backend should return not implemented error."""
        tool = CadQueryExecTool(backend="real")
        inputs = {"code": "cq.Workplane('XY').box(100, 50, 30)"}
        result = tool.execute(inputs)

        assert result.success is False
        assert "not implemented" in result.message.lower()


class TestEvaluationSuite:
    """Tests for the evaluation suite harness."""

    @pytest.fixture
    def harness(self):
        """Create evaluation harness with mock tool."""
        tool = CadQueryExecTool(backend="mock")
        comparator = GeometricComparator(tolerance=0.01)
        suite_path = Path(__file__).parent / "evaluation_suite"
        return EvaluationHarness(tool, comparator, suite_path)

    def test_discover_all_test_cases(self, harness):
        """Harness should discover all 50 train test cases."""
        test_cases = harness.discover_test_cases(split="train")
        assert (
            len(test_cases) == 50
        ), f"Expected 50 train test cases, found {len(test_cases)}"

    def test_discover_test_cases_by_level(self, harness):
        """Harness should find correct number of cases per level."""
        test_cases = harness.discover_test_cases(split="train")

        levels = {}
        for tc in test_cases:
            spec = harness.load_spec(tc)
            level = spec.get("level", 0)
            levels[level] = levels.get(level, 0) + 1

        assert levels.get(1, 0) == 12, "Level 1 should have 12 train cases"
        assert levels.get(2, 0) == 15, "Level 2 should have 15 train cases"
        assert levels.get(3, 0) == 13, "Level 3 should have 13 train cases"
        assert levels.get(4, 0) == 10, "Level 4 should have 10 train cases"

    def test_load_spec_has_required_fields(self, harness):
        """Each spec should have required fields."""
        test_cases = harness.discover_test_cases(split="train")

        for tc in test_cases:
            spec = harness.load_spec(tc)
            assert "id" in spec, f"{tc.name} missing 'id'"
            assert "level" in spec, f"{tc.name} missing 'level'"
            assert "expected_volume" in spec, f"{tc.name} missing 'expected_volume'"
            assert (
                "expected_bounding_box" in spec
            ), f"{tc.name} missing 'expected_bounding_box'"

    def test_load_intent_exists(self, harness):
        """Each test case should have intent.txt."""
        test_cases = harness.discover_test_cases(split="train")

        for tc in test_cases:
            intent = harness.load_intent(tc)
            assert len(intent) > 0, f"{tc.name} has empty intent.txt"

    def test_load_ground_truth_exists(self, harness):
        """Each test case should have ground_truth.py."""
        test_cases = harness.discover_test_cases(split="train")

        for tc in test_cases:
            code = harness.load_ground_truth_code(tc)
            assert len(code) > 0, f"{tc.name} has empty ground_truth.py"
            assert (
                "cadquery" in code.lower()
            ), f"{tc.name} ground_truth missing cadquery import"

    def test_run_suite_executes_all_cases(self, harness):
        """Running suite should execute all 50 train test cases."""
        results = harness.run_suite(split="train")

        total = sum(len(level_results) for level_results in results.values())
        assert total == 50, f"Expected 50 results, got {total}"

    def test_mock_backend_shows_zero_success(self, harness):
        """Mock backend with placeholder data should show 0% success rate."""
        results = harness.run_suite(split="train")

        passed = 0
        failed = 0
        for level_results in results.values():
            for r in level_results:
                if r.success:
                    passed += 1
                else:
                    failed += 1

        total = passed + failed
        success_rate = passed / total if total > 0 else 0

        assert total == 50, f"Expected 50 tests, got {total}"
        assert passed == 0, f"Expected 0 passed with mock backend, got {passed}"
        assert success_rate == 0.0, f"Expected 0% success rate, got {success_rate:.1%}"

    def test_generate_report_shows_results(self, harness):
        """Report should show 0/50 success rate."""
        results = harness.run_suite(split="train")
        report = harness.generate_report(results)

        assert "Total Tests: 50" in report
        assert "Passed: 0" in report
        assert "Failed: 50" in report
        assert "Success Rate: 0.0%" in report

    def test_run_single_returns_test_case_result(self, harness):
        """run_single should return TestCaseResult."""
        test_cases = harness.discover_test_cases(split="train")
        result = harness.run_single(test_cases[0])

        assert result.test_id is not None
        assert result.level > 0
        assert result.attempts >= 0
        assert result.execution_time_ms >= 0


class TestCadQueryExecToolGatewayBackend:
    """Tests for CadQueryExecTool with gateway backend."""

    def test_gateway_backend_requires_gateway_instance(self):
        """backend='gateway' without gateway raises ValueError."""
        with pytest.raises(ValueError, match="gateway parameter required"):
            CadQueryExecTool(backend="gateway")

    def test_gateway_backend_accepts_gateway(self):
        """backend='gateway' with gateway instance succeeds."""
        from src.tools.gateway import ToolGateway

        gateway = ToolGateway()
        tool = CadQueryExecTool(backend="gateway", gateway=gateway)

        assert tool.backend == "gateway"
        assert tool._gateway is gateway

    def test_gateway_execute_success(self):
        """Gateway execution returns ToolResult with geometry data."""
        from unittest.mock import Mock

        from src.tools.gateway.protocol import ExecutionResult

        mock_gateway = Mock()
        mock_gateway.execute.return_value = ExecutionResult(
            success=True,
            geometry_props={
                "volume": 1000.0,
                "face_count": 6,
                "edge_count": 12,
                "vertex_count": 8,
                "bounding_box": {"xlen": 10.0, "ylen": 10.0, "zlen": 10.0},
            },
            step_path="/tmp/test.step",
        )

        tool = CadQueryExecTool(backend="gateway", gateway=mock_gateway)
        result = tool.execute(
            {
                "code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
            }
        )

        assert result.success is True
        assert result.data["volume"] == 1000.0
        assert result.data["face_count"] == 6
        assert result.data["step_path"] == "/tmp/test.step"
        assert result.data["backend"] == "gateway"

    def test_gateway_execute_failure(self):
        """Gateway execution failure returns ToolResult with error."""
        from unittest.mock import Mock

        from src.tools.gateway.protocol import ErrorCategory, ExecutionResult

        mock_gateway = Mock()
        mock_gateway.execute.return_value = ExecutionResult(
            success=False,
            error_category=ErrorCategory.SYNTAX,
            error_message="SyntaxError: invalid syntax",
        )

        tool = CadQueryExecTool(backend="gateway", gateway=mock_gateway)
        result = tool.execute({"code": "result = cq.box("})

        assert result.success is False
        assert "SyntaxError" in result.error
        assert result.data["execution_success"] is False

    def test_gateway_execute_validates_inputs(self):
        """Gateway backend still validates inputs before execution."""
        from src.tools.gateway import ToolGateway

        gateway = ToolGateway()
        tool = CadQueryExecTool(backend="gateway", gateway=gateway)

        # Empty code should fail validation
        result = tool.execute({"code": ""})

        assert result.success is False
        assert "Invalid inputs" in result.message

    def test_mock_backend_unchanged(self):
        """Mock backend still works (backward compatibility)."""
        tool = CadQueryExecTool(backend="mock")
        result = tool.execute(
            {
                "code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
            }
        )

        assert result.success is True
        assert result.data["backend"] == "mock"
