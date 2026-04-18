"""Tests for the execution module (executor, error handler, feedback loop)."""

from src.cad.intent_decomposition.execution.error_handler import (
    ERROR_PATTERNS,
    ErrorAnalysis,
    ErrorAnalyzer,
    ErrorCategory,
)
from src.cad.intent_decomposition.execution.executor import (
    CADExecutor,
    ExecutionResult,
    MockCADExecutor,
)
from src.cad.intent_decomposition.execution.feedback_loop import (
    FeedbackIteration,
    FeedbackLoopResult,
    MockFeedbackLoopManager,
)
from src.cad.intent_decomposition.retrieval.retriever import RetrievalContext


def make_empty_retrieval_context() -> RetrievalContext:
    """Helper to create an empty RetrievalContext for testing."""
    return RetrievalContext(operations=[], metadata={})


# =============================================================================
# ExecutionResult Tests
# =============================================================================


class TestExecutionResult:
    """Tests for the ExecutionResult dataclass."""

    def test_execution_result_success(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            geometry_properties={"volume": 1000.0, "face_count": 6},
            execution_time_ms=15.5,
        )
        assert result.success is True
        assert result.geometry_properties["volume"] == 1000.0
        assert result.error is None

    def test_execution_result_failure(self):
        """Test failed execution result."""
        result = ExecutionResult(
            success=False,
            error="SyntaxError: invalid syntax",
            error_traceback="Traceback...",
        )
        assert result.success is False
        assert "SyntaxError" in result.error
        assert result.geometry_properties == {}

    def test_execution_result_str_success(self):
        """Test string representation for success."""
        result = ExecutionResult(
            success=True,
            geometry_properties={"volume": 500.0},
        )
        str_repr = str(result)
        assert "success=True" in str_repr
        assert "500" in str_repr

    def test_execution_result_str_failure(self):
        """Test string representation for failure."""
        result = ExecutionResult(
            success=False,
            error="Some error message that is quite long",
        )
        str_repr = str(result)
        assert "success=False" in str_repr


# =============================================================================
# MockCADExecutor Tests
# =============================================================================


class TestMockCADExecutor:
    """Tests for MockCADExecutor."""

    def test_mock_executor_creation(self):
        """Test mock executor creation."""
        executor = MockCADExecutor()
        assert executor.execution_count == 0

    def test_mock_executor_success(self):
        """Test successful mock execution."""
        executor = MockCADExecutor()
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 5)
"""
        result = executor.execute(code)

        assert result.success is True
        assert "volume" in result.geometry_properties
        assert executor.execution_count == 1

    def test_mock_executor_no_result_variable(self):
        """Test mock execution without result variable."""
        executor = MockCADExecutor()
        code = """
import cadquery as cq
box = cq.Workplane("XY").box(10, 20, 5)
"""
        result = executor.execute(code)

        assert result.success is False
        assert "result" in result.error.lower()

    def test_mock_executor_syntax_error(self):
        """Test mock execution with syntax error."""
        executor = MockCADExecutor()
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20,
"""
        result = executor.execute(code)

        assert result.success is False
        assert "syntax" in result.error.lower()

    def test_mock_executor_box_dimensions(self):
        """Test mock executor extracts box dimensions."""
        executor = MockCADExecutor()
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(30, 20, 10)
"""
        result = executor.execute(code)

        assert result.success is True
        # Mock should extract dimensions from code
        props = result.geometry_properties
        assert props["volume"] == 30 * 20 * 10

    def test_mock_executor_set_failure(self):
        """Test configuring mock to fail."""
        executor = MockCADExecutor()
        executor.set_should_fail(True, "Simulated geometry error")

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        result = executor.execute(code)

        assert result.success is False
        assert "Simulated" in result.error

    def test_mock_executor_validate_code(self):
        """Test code validation."""
        executor = MockCADExecutor()

        valid, error = executor.validate_code("x = 1 + 2")
        assert valid is True
        assert error is None

        valid, error = executor.validate_code("x = 1 +")
        assert valid is False
        assert "Syntax error" in error


# =============================================================================
# ErrorCategory Tests
# =============================================================================


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_error_categories_exist(self):
        """Test that all expected error categories exist."""
        assert ErrorCategory.SYNTAX_ERROR is not None
        assert ErrorCategory.IMPORT_ERROR is not None
        assert ErrorCategory.GEOMETRY_ERROR is not None
        assert ErrorCategory.FILLET_ERROR is not None
        assert ErrorCategory.HOLE_ERROR is not None
        assert ErrorCategory.SELECTION_ERROR is not None
        assert ErrorCategory.UNKNOWN is not None

    def test_is_recoverable_syntax_error(self):
        """Test syntax errors are not recoverable."""
        assert ErrorCategory.SYNTAX_ERROR.is_recoverable is False

    def test_is_recoverable_import_error(self):
        """Test import errors are not recoverable."""
        assert ErrorCategory.IMPORT_ERROR.is_recoverable is False

    def test_is_recoverable_geometry_error(self):
        """Test geometry errors are recoverable."""
        assert ErrorCategory.GEOMETRY_ERROR.is_recoverable is True

    def test_is_recoverable_fillet_error(self):
        """Test fillet errors are recoverable."""
        assert ErrorCategory.FILLET_ERROR.is_recoverable is True

    def test_suggested_strategy_exists(self):
        """Test each category has a suggested strategy."""
        for category in ErrorCategory:
            strategy = category.suggested_strategy
            assert strategy is not None
            assert len(strategy) > 5


# =============================================================================
# ErrorAnalysis Tests
# =============================================================================


class TestErrorAnalysis:
    """Tests for ErrorAnalysis dataclass."""

    def test_error_analysis_creation(self):
        """Test ErrorAnalysis creation."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.FILLET_ERROR,
            message="Fillet radius too large",
            root_cause="Fillet radius exceeds edge length",
            suggested_fix="Reduce fillet radius by 50%",
            confidence=0.85,
        )

        assert analysis.category == ErrorCategory.FILLET_ERROR
        assert "too large" in analysis.message
        assert analysis.confidence == 0.85

    def test_error_analysis_str(self):
        """Test string representation."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.HOLE_ERROR,
            message="Hole outside bounds",
            root_cause="Hole position is outside solid geometry",
            suggested_fix="Adjust hole position",
        )

        str_repr = str(analysis)
        assert "hole_error" in str_repr

    def test_error_analysis_to_prompt_context(self):
        """Test conversion to prompt context."""
        analysis = ErrorAnalysis(
            category=ErrorCategory.SELECTION_ERROR,
            message="Face not found",
            root_cause="Invalid face selector",
            suggested_fix="Use valid selector like >Z",
        )

        context = analysis.to_prompt_context()

        assert "selection_error" in context
        assert "Invalid face selector" in context
        assert ">Z" in context


# =============================================================================
# ErrorAnalyzer Tests
# =============================================================================


class TestErrorAnalyzer:
    """Tests for ErrorAnalyzer."""

    def test_error_analyzer_creation(self):
        """Test error analyzer creation."""
        analyzer = ErrorAnalyzer()
        assert analyzer is not None

    def test_analyze_syntax_error(self):
        """Test analyzing syntax error."""
        analyzer = ErrorAnalyzer()
        code = "result = cq.box(10, 10"
        error = "SyntaxError: unexpected EOF while parsing"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.SYNTAX_ERROR

    def test_analyze_name_error(self):
        """Test analyzing name error."""
        analyzer = ErrorAnalyzer()
        code = "result = undefined_var + 1"
        error = "NameError: name 'undefined_var' is not defined"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.NAME_ERROR
        assert "undefined_var" in analysis.root_cause

    def test_analyze_import_error(self):
        """Test analyzing import error."""
        analyzer = ErrorAnalyzer()
        code = "import nonexistent_module"
        error = "ModuleNotFoundError: No module named 'nonexistent_module'"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.IMPORT_ERROR

    def test_analyze_fillet_error(self):
        """Test analyzing fillet error."""
        analyzer = ErrorAnalyzer()
        code = "result = box.edges().fillet(100)"
        error = "ValueError: fillet radius too large for geometry"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.FILLET_ERROR
        assert (
            "50%" in analysis.suggested_fix
            or "reduce" in analysis.suggested_fix.lower()
        )

    def test_analyze_selection_error(self):
        """Test analyzing selection error."""
        analyzer = ErrorAnalyzer()
        code = 'result = box.faces("invalid")'
        error = "ValueError: no face found for selector"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.SELECTION_ERROR

    def test_analyze_no_geometry(self):
        """Test analyzing no geometry error."""
        analyzer = ErrorAnalyzer()
        code = "result = cq.Workplane('XY')"
        error = "ValueError: no solid geometry created"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.NO_GEOMETRY

    def test_analyze_unknown_error(self):
        """Test analyzing unknown error."""
        analyzer = ErrorAnalyzer()
        code = "result = something()"
        error = "SomeWeirdError: unusual situation"

        analysis = analyzer.analyze(error, code)

        assert analysis.category == ErrorCategory.UNKNOWN

    def test_analyze_with_traceback(self):
        """Test analyzing error with traceback."""
        analyzer = ErrorAnalyzer()
        code = "result = box.fillet(10)"
        error = "ValueError: fillet failed"
        traceback = """Traceback (most recent call last):
  File "<string>", line 5, in <module>
  File "cadquery/cq.py", line 100, in fillet
ValueError: fillet failed"""

        analysis = analyzer.analyze(error, code, traceback)

        assert analysis.category == ErrorCategory.FILLET_ERROR
        assert (
            "error_line" in analysis.context or analysis.context.get("error_line") == 5
        )

    def test_confidence_high_for_specific_errors(self):
        """Test high confidence for specific error types."""
        analyzer = ErrorAnalyzer()

        # Syntax errors should have high confidence
        analysis = analyzer.analyze("SyntaxError: invalid syntax", "code")
        assert analysis.confidence >= 0.8

    def test_confidence_low_for_unknown(self):
        """Test low confidence for unknown errors."""
        analyzer = ErrorAnalyzer()

        analysis = analyzer.analyze("WeirdError: something happened", "code")
        assert analysis.confidence <= 0.5


# =============================================================================
# FeedbackIteration Tests
# =============================================================================


class TestFeedbackIteration:
    """Tests for FeedbackIteration dataclass."""

    def test_feedback_iteration_success(self):
        """Test successful iteration."""
        iteration = FeedbackIteration(
            iteration=1,
            code="result = box",
            result=ExecutionResult(success=True),
        )

        assert iteration.success is True
        assert iteration.iteration == 1

    def test_feedback_iteration_failure(self):
        """Test failed iteration."""
        iteration = FeedbackIteration(
            iteration=2,
            code="result = broken",
            result=ExecutionResult(success=False, error="Error"),
            error_analysis=ErrorAnalysis(
                category=ErrorCategory.SYNTAX_ERROR,
                message="Error",
                root_cause="Bad syntax",
                suggested_fix="Fix it",
            ),
        )

        assert iteration.success is False
        assert iteration.error_analysis is not None

    def test_feedback_iteration_with_fix(self):
        """Test iteration with fix applied."""
        iteration = FeedbackIteration(
            iteration=3,
            code="result = fixed_code",
            result=ExecutionResult(success=True),
            fix_applied="Reduced fillet radius",
        )

        assert iteration.fix_applied is not None


# =============================================================================
# FeedbackLoopResult Tests
# =============================================================================


class TestFeedbackLoopResult:
    """Tests for FeedbackLoopResult dataclass."""

    def test_feedback_loop_result_success(self):
        """Test successful feedback loop result."""
        result = FeedbackLoopResult(
            success=True,
            final_code="result = working_code",
            final_result=ExecutionResult(success=True),
            iterations=[
                FeedbackIteration(
                    iteration=1,
                    code="result = working_code",
                    result=ExecutionResult(success=True),
                )
            ],
        )

        assert result.success is True
        assert result.total_iterations == 1

    def test_feedback_loop_result_multiple_iterations(self):
        """Test feedback loop with multiple iterations."""
        result = FeedbackLoopResult(
            success=True,
            final_code="result = fixed_code",
            final_result=ExecutionResult(success=True),
            iterations=[
                FeedbackIteration(
                    iteration=1,
                    code="result = broken",
                    result=ExecutionResult(success=False, error="Error"),
                    error_analysis=ErrorAnalysis(
                        category=ErrorCategory.FILLET_ERROR,
                        message="Fillet error",
                        root_cause="Too large",
                        suggested_fix="Reduce",
                    ),
                ),
                FeedbackIteration(
                    iteration=2,
                    code="result = fixed_code",
                    result=ExecutionResult(success=True),
                    fix_applied="Reduced fillet radius",
                ),
            ],
        )

        assert result.success is True
        assert result.total_iterations == 2

    def test_feedback_loop_result_error_categories(self):
        """Test error category tracking."""
        result = FeedbackLoopResult(
            success=False,
            final_code="result = still_broken",
            final_result=ExecutionResult(success=False, error="Error"),
            iterations=[
                FeedbackIteration(
                    iteration=1,
                    code="code1",
                    result=ExecutionResult(success=False),
                    error_analysis=ErrorAnalysis(
                        category=ErrorCategory.FILLET_ERROR,
                        message="",
                        root_cause="",
                        suggested_fix="",
                    ),
                ),
                FeedbackIteration(
                    iteration=2,
                    code="code2",
                    result=ExecutionResult(success=False),
                    error_analysis=ErrorAnalysis(
                        category=ErrorCategory.GEOMETRY_ERROR,
                        message="",
                        root_cause="",
                        suggested_fix="",
                    ),
                ),
            ],
        )

        categories = result.error_categories
        assert ErrorCategory.FILLET_ERROR in categories
        assert ErrorCategory.GEOMETRY_ERROR in categories
        assert len(categories) == 2

    def test_feedback_loop_result_geometry_valid_false(self):
        """geometry_valid=False and quality_warnings set when solid_count > 1."""
        result = FeedbackLoopResult(
            success=True,
            final_code="result = code_with_disconnected_solids",
            final_result=ExecutionResult(
                success=True,
                geometry_properties={"solid_count": 3},
            ),
            iterations=[],
            geometry_valid=False,
            quality_warnings=["Disconnected geometry: 3 solids (expected 1)"],
        )

        assert result.success is True
        assert result.geometry_valid is False
        assert len(result.quality_warnings) == 1
        assert "3 solids" in result.quality_warnings[0]

    def test_feedback_loop_result_geometry_valid_default_true(self):
        """geometry_valid defaults to True for single-solid results."""
        result = FeedbackLoopResult(
            success=True,
            final_code="result = good_code",
            final_result=ExecutionResult(success=True),
        )

        assert result.geometry_valid is True
        assert result.quality_warnings == []

    def test_feedback_loop_result_str(self):
        """Test string representation."""
        result = FeedbackLoopResult(
            success=True,
            final_code="code",
            final_result=ExecutionResult(success=True),
            iterations=[
                FeedbackIteration(
                    iteration=1,
                    code="code",
                    result=ExecutionResult(success=True),
                )
            ],
        )

        str_repr = str(result)
        assert "SUCCESS" in str_repr
        assert "iterations=1" in str_repr


# =============================================================================
# MockFeedbackLoopManager Tests
# =============================================================================


class TestMockFeedbackLoopManager:
    """Tests for MockFeedbackLoopManager."""

    def test_mock_manager_creation(self):
        """Test mock manager creation."""
        manager = MockFeedbackLoopManager()
        assert manager.run_count == 0

    def test_mock_manager_success(self):
        """Test successful mock run."""
        manager = MockFeedbackLoopManager()

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        retrieval_context = make_empty_retrieval_context()

        result = manager.run(code, retrieval_context)

        assert result.success is True
        assert result.total_iterations == 1
        assert manager.run_count == 1

    def test_mock_manager_no_result_variable(self):
        """Test mock run without result variable."""
        manager = MockFeedbackLoopManager()

        code = """
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
"""
        retrieval_context = make_empty_retrieval_context()

        result = manager.run(code, retrieval_context)

        assert result.success is False

    def test_mock_manager_syntax_error(self):
        """Test mock run with syntax error."""
        manager = MockFeedbackLoopManager()

        code = "result = cq.box(10, 10,"  # Incomplete

        retrieval_context = make_empty_retrieval_context()

        result = manager.run(code, retrieval_context)

        assert result.success is False
        assert "Syntax error" in result.final_result.error

    def test_mock_manager_run_single(self):
        """Test single execution without feedback loop."""
        manager = MockFeedbackLoopManager()

        code = """result = cq.Workplane("XY").box(10, 10, 10)"""
        result = manager.run_single(code)

        assert result.success is True
        assert manager.run_count == 1


# =============================================================================
# Error Pattern Matching Tests
# =============================================================================


class TestErrorPatterns:
    """Tests for error pattern matching."""

    def test_error_patterns_exist(self):
        """Test that error patterns are defined."""
        assert len(ERROR_PATTERNS) > 0

    def test_patterns_cover_common_errors(self):
        """Test patterns cover common error types."""
        # Get all categories from patterns
        pattern_categories = {cat for _, cat, _ in ERROR_PATTERNS}

        # Check important categories are covered
        assert ErrorCategory.SYNTAX_ERROR in pattern_categories
        assert ErrorCategory.NAME_ERROR in pattern_categories
        assert ErrorCategory.FILLET_ERROR in pattern_categories
        assert ErrorCategory.SELECTION_ERROR in pattern_categories

    def test_pattern_matching_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        analyzer = ErrorAnalyzer()

        # Test with different cases
        analysis1 = analyzer.analyze("SYNTAXERROR: invalid", "code")
        analysis2 = analyzer.analyze("syntaxerror: invalid", "code")

        assert analysis1.category == analysis2.category


# =============================================================================
# CADExecutor Gateway Tests
# =============================================================================


class TestCADExecutorWithGateway:
    """Tests for CADExecutor with ToolGateway injection."""

    def test_executor_accepts_gateway(self):
        """CADExecutor accepts optional gateway parameter."""
        from src.tools.gateway import ToolGateway

        gateway = ToolGateway()
        executor = CADExecutor(gateway=gateway)

        assert executor._gateway is gateway

    def test_executor_without_gateway_is_none(self):
        """CADExecutor without gateway has _gateway=None."""
        executor = CADExecutor()
        assert executor._gateway is None

    def test_executor_delegates_to_gateway(self):
        """execute() delegates to gateway when provided."""
        from unittest.mock import Mock

        from src.tools.gateway.protocol import ExecutionResult as GatewayResult

        mock_gateway = Mock()
        mock_gateway.execute.return_value = GatewayResult(
            success=True,
            geometry_props={"volume": 1000.0, "face_count": 6},
            step_path="/tmp/test.step",
        )

        executor = CADExecutor(gateway=mock_gateway)
        result = executor.execute(
            "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        )

        mock_gateway.execute.assert_called_once()
        assert result.success is True
        assert result.geometry_properties["volume"] == 1000.0
        assert result.step_path == "/tmp/test.step"

    def test_executor_gateway_error_propagation(self):
        """Gateway errors propagate through executor."""
        from unittest.mock import Mock

        from src.tools.gateway.protocol import (
            ErrorCategory as GatewayErrorCategory,
        )
        from src.tools.gateway.protocol import (
            ExecutionResult as GatewayResult,
        )

        mock_gateway = Mock()
        mock_gateway.execute.return_value = GatewayResult(
            success=False,
            error_category=GatewayErrorCategory.SYNTAX,
            error_message="SyntaxError: invalid syntax",
        )

        executor = CADExecutor(gateway=mock_gateway)
        result = executor.execute("result = cq.box(")

        assert result.success is False
        assert "SyntaxError" in result.error

    def test_executor_gateway_timeout_passthrough(self):
        """Timeout setting passed to gateway."""
        from unittest.mock import Mock

        from src.tools.gateway.protocol import ExecutionResult as GatewayResult

        mock_gateway = Mock()
        mock_gateway.execute.return_value = GatewayResult(
            success=True, geometry_props={}
        )

        executor = CADExecutor(timeout_seconds=60.0, gateway=mock_gateway)
        executor.execute("result = 1")

        call_kwargs = mock_gateway.execute.call_args[1]
        assert call_kwargs["timeout_seconds"] == 60.0

    def test_executor_without_gateway_uses_internal(self):
        """Without gateway, uses internal multiprocessing."""
        executor = CADExecutor()
        # Mock execution returns success for valid code with result var
        result = executor.execute("result = 1")

        # Should use internal path (no gateway call)
        # Result depends on whether CadQuery is available
        # Just verify it doesn't crash
        assert hasattr(result, "success")
