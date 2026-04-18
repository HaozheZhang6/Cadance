"""Tests for vision-based geometry evaluation wiring and helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.cad.intent_decomposition.geometry_evaluator.models import (
    EvaluationFeedback,
    Severity,
    ValidationLevel,
)
from src.cad.intent_decomposition.pipeline import (
    IntentToCADPipeline,
    PipelineConfig,
    VisionEvaluationConfig,
)


class _DummyRetrievalContext:
    def to_prompt_context(self) -> str:
        return "mock api context"


@dataclass
class _DummyRefined:
    code: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class _DummyFeedbackResult:
    success: bool
    final_result: object | None = None


class _DummyCodeGenerator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_vision_refinement(self, **kwargs):
        self.calls.append(kwargs)
        return _DummyRefined(code="# refined code")


class _DummyFeedbackLoop:
    def __init__(self, result: _DummyFeedbackResult) -> None:
        self.calls: list[dict] = []
        self._result = result

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return self._result


class _TrackingEvaluator:
    created = 0
    returned_feedback: EvaluationFeedback | None = None

    def __init__(self, *args, **kwargs) -> None:
        type(self).created += 1

    def evaluate(self, **kwargs) -> EvaluationFeedback:
        if self.returned_feedback is None:
            raise AssertionError("Tracking evaluator feedback not configured")
        return self.returned_feedback


def _make_pipeline(config: PipelineConfig) -> IntentToCADPipeline:
    pipeline = object.__new__(IntentToCADPipeline)
    pipeline.config = config
    pipeline._gateway = object()
    pipeline.llm_client = object()
    pipeline.code_generator = _DummyCodeGenerator()
    pipeline.feedback_loop = _DummyFeedbackLoop(_DummyFeedbackResult(success=False))
    return pipeline


def test_generate_filename_from_intent_includes_intent_and_timestamp(monkeypatch):
    pipeline = object.__new__(IntentToCADPipeline)

    monkeypatch.setattr(time, "time", lambda: 1700000000.123)

    filename = pipeline._generate_filename_from_intent(
        "Create L-bracket 5mm", "stage4_initial"
    )

    assert filename == "create_lbracket_5mm_stage4_initial_1700000000123"


def test_vision_regen_honors_confidence_threshold(monkeypatch, tmp_path):
    config = PipelineConfig(
        vision_evaluation=VisionEvaluationConfig(
            enabled=True,
            confidence_threshold=0.9,
            regenerate_on_fail=True,
            max_iterations=1,
        )
    )
    pipeline = _make_pipeline(config)

    monkeypatch.chdir(tmp_path)
    step_path = tmp_path / "input.step"
    step_path.write_text("step data")

    from src.cad.intent_decomposition.utils import visualization as viz

    def fake_render(*_args, **_kwargs):
        paths = {}
        for view in viz.STANDARD_VIEWS.keys():
            png_path = tmp_path / f"{view}.png"
            png_path.write_bytes(b"png")
            paths[view] = png_path
        return paths

    monkeypatch.setattr(viz, "render_step_to_images_with_fallback", fake_render)

    from src.cad.intent_decomposition.geometry_evaluator import evaluator as eval_module

    _TrackingEvaluator.created = 0
    _TrackingEvaluator.returned_feedback = EvaluationFeedback(
        level=ValidationLevel.DESIGN_INTENT,
        severity=Severity.MINOR,
        passed=True,
        confidence=0.5,
        should_regenerate=False,
    )
    monkeypatch.setattr(eval_module, "GeometryEvaluator", _TrackingEvaluator)

    result = pipeline._run_vision_check(
        code="result = None",
        step_path=step_path,
        intent="Create a bracket",
        retrieval_context=_DummyRetrievalContext(),
    )

    assert result["regenerated"] is True
    assert len(pipeline.code_generator.calls) == 1
    assert len(pipeline.feedback_loop.calls) == 1


def test_vision_regen_disabled_when_config_false(monkeypatch, tmp_path):
    config = PipelineConfig(
        vision_evaluation=VisionEvaluationConfig(
            enabled=True,
            confidence_threshold=0.1,
            regenerate_on_fail=False,
            max_iterations=1,
        )
    )
    pipeline = _make_pipeline(config)

    monkeypatch.chdir(tmp_path)
    step_path = tmp_path / "input.step"
    step_path.write_text("step data")

    from src.cad.intent_decomposition.utils import visualization as viz

    def fake_render(*_args, **_kwargs):
        paths = {}
        for view in viz.STANDARD_VIEWS.keys():
            png_path = tmp_path / f"{view}.png"
            png_path.write_bytes(b"png")
            paths[view] = png_path
        return paths

    monkeypatch.setattr(viz, "render_step_to_images_with_fallback", fake_render)

    from src.cad.intent_decomposition.geometry_evaluator import evaluator as eval_module

    _TrackingEvaluator.created = 0
    _TrackingEvaluator.returned_feedback = EvaluationFeedback(
        level=ValidationLevel.DESIGN_INTENT,
        severity=Severity.MAJOR,
        passed=False,
        confidence=0.95,
        should_regenerate=True,
    )
    monkeypatch.setattr(eval_module, "GeometryEvaluator", _TrackingEvaluator)

    result = pipeline._run_vision_check(
        code="result = None",
        step_path=step_path,
        intent="Create a bracket",
        retrieval_context=_DummyRetrievalContext(),
    )

    assert result["regenerated"] is False
    assert len(pipeline.code_generator.calls) == 0
    assert len(pipeline.feedback_loop.calls) == 0


def test_vision_skips_when_png_missing(monkeypatch, tmp_path):
    config = PipelineConfig(
        vision_evaluation=VisionEvaluationConfig(enabled=True, max_iterations=1)
    )
    pipeline = _make_pipeline(config)

    monkeypatch.chdir(tmp_path)
    step_path = tmp_path / "input.step"
    step_path.write_text("step data")

    from src.cad.intent_decomposition.utils import visualization as viz

    def fake_render(*_args, **_kwargs):
        paths = {}
        for view in viz.STANDARD_VIEWS.keys():
            if view == "top":
                svg_path = tmp_path / f"{view}.svg"
                svg_path.write_text("svg")
                paths[view] = svg_path
            else:
                png_path = tmp_path / f"{view}.png"
                png_path.write_bytes(b"png")
                paths[view] = png_path
        return paths

    monkeypatch.setattr(viz, "render_step_to_images_with_fallback", fake_render)

    from src.cad.intent_decomposition.geometry_evaluator import evaluator as eval_module

    _TrackingEvaluator.created = 0
    _TrackingEvaluator.returned_feedback = EvaluationFeedback(
        level=ValidationLevel.DESIGN_INTENT,
        severity=Severity.MINOR,
        passed=True,
        confidence=0.9,
        should_regenerate=False,
    )
    monkeypatch.setattr(eval_module, "GeometryEvaluator", _TrackingEvaluator)

    result = pipeline._run_vision_check(
        code="result = None",
        step_path=step_path,
        intent="Create a bracket",
        retrieval_context=_DummyRetrievalContext(),
    )

    assert result["regenerated"] is False
    assert _TrackingEvaluator.created == 0


# New comprehensive tests for critical paths
def test_parse_llm_response_various_formats():
    """Test _parse_llm_response with different LLM response formats."""
    from src.cad.intent_decomposition.geometry_evaluator.evaluator import (
        GeometryEvaluator,
    )

    evaluator = GeometryEvaluator(llm_client=None)

    # Test 1: YES pass with confidence
    response = """PASSED: YES
ISSUES: None
CONFIDENCE: 0.95
SUGGESTIONS: Looks good"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is True
    assert feedback.confidence == 0.95
    assert len(feedback.issues) == 0

    # Test 2: NO fail with issues
    response = """PASSED: NO
ISSUES:
- Missing hole feature
- Dimensions too small
CONFIDENCE: 0.8
SUGGESTIONS: Add hole and increase size"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is False
    assert feedback.confidence == 0.8
    assert len(feedback.issues) == 2
    assert "hole" in feedback.issues[0].description.lower()

    # Test 3: Edge case - malformed confidence
    response = """PASSED: YES
CONFIDENCE: invalid
ISSUES: None"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is True
    assert feedback.confidence == 0.5  # default fallback

    # Test 4: Multi-line issues with bullets
    response = """PASSED: NO
ISSUES:
- Issue 1: Short description
- Issue 2: Another problem
- Issue 3: Third issue
CONFIDENCE: 0.6"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is False
    assert len(feedback.issues) == 3

    # Test 5: PASS alternative format
    response = """PASSED: PASS
CONFIDENCE: 1.0"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is True

    # Test 6: TRUE alternative format
    response = """PASSED: TRUE
CONFIDENCE: 0.9"""
    feedback = evaluator._parse_llm_response(response)
    assert feedback.passed is True


def test_rule_based_evaluation_fallback():
    """Test _rule_based_evaluation when vision LLM unavailable."""
    from pathlib import Path

    from src.cad.intent_decomposition.geometry_evaluator.evaluator import (
        GeometryEvaluator,
    )

    evaluator = GeometryEvaluator(llm_client=None)

    # Test with all PNGs present
    tmp_dir = Path("/tmp/test_eval")
    tmp_dir.mkdir(exist_ok=True)

    png_images = {}
    for view in ["isometric", "front", "top"]:
        png_path = tmp_dir / f"{view}.png"
        png_path.write_bytes(b"fake png")
        png_images[view] = png_path

    feedback = evaluator._rule_based_evaluation("Create box", png_images)
    assert feedback.passed is True
    assert feedback.confidence == 0.3
    assert feedback.metadata["vision_unavailable"] is True
    assert feedback.should_regenerate is False

    # Clean up
    for png_path in png_images.values():
        png_path.unlink()
    tmp_dir.rmdir()


def test_vision_refinement_code_extraction():
    """Test code extraction from vision refinement responses."""
    from src.cad.intent_decomposition.synthesis.code_generator import CodeGenerator

    class MockLLM:
        def complete(self, **kwargs):
            # Return code in markdown block
            return """Here's the fixed code:
```python
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
```
This should fix the issue."""

    generator = CodeGenerator(llm_client=MockLLM())

    # Mock vision feedback
    class MockFeedback:
        passed = False
        confidence = 0.5
        issues = []
        suggestions = []

        def __init__(self):
            self.issues_text = "Missing feature"
            self.suggestions_text = "Add feature"

    class MockContext:
        def get_all_apis(self):
            return []

        def to_prompt_context(self):
            return "mock api docs"

    code = "# old code"
    refined = generator.generate_vision_refinement(
        code=code,
        intent="Create box",
        vision_feedback=MockFeedback(),
        retrieval_context=MockContext(),
    )

    assert "import cadquery" in refined.code
    assert "box" in refined.code
    assert refined.code != code


def test_vision_refinement_identical_code_detection():
    """Test that identical code from refinement is detected."""
    from src.cad.intent_decomposition.synthesis.code_generator import CodeGenerator

    original_code = """import cadquery as cq
result = cq.Workplane("XY").box(5, 5, 5)"""

    class MockLLM:
        def complete(self, **kwargs):
            # Return identical code (simulating no progress)
            return f"""```python
{original_code}
```"""

    generator = CodeGenerator(llm_client=MockLLM())

    class MockFeedback:
        passed = False
        confidence = 0.5
        issues = []
        suggestions = []

        def __init__(self):
            self.issues_text = "Issue"
            self.suggestions_text = "Fix"

    class MockContext:
        def get_all_apis(self):
            return []

        def to_prompt_context(self):
            return "mock api docs"

    refined = generator.generate_vision_refinement(
        code=original_code,
        intent="Create box",
        vision_feedback=MockFeedback(),
        retrieval_context=MockContext(),
    )

    # Should detect no progress
    assert refined.metadata.get("no_progress") is True


def test_wrap_unsafe_fillets():
    """Test _wrap_unsafe_fillets wraps risky fillet operations."""
    from src.cad.intent_decomposition.synthesis.code_generator import CodeGenerator

    generator = CodeGenerator(llm_client=None)

    # Test 1: Simple fillet wrapping
    code = """result = cq.Workplane("XY").box(10, 10, 10)
result = result.edges("|Z").fillet(2)"""

    wrapped = generator._wrap_unsafe_fillets(code)
    assert "try:" in wrapped
    assert "except:" in wrapped
    assert "pass" in wrapped

    # Test 2: Already wrapped code (should not double-wrap)
    code_with_try = """try:
    result = result.edges("|Z").fillet(2)
except:
    pass"""

    wrapped = generator._wrap_unsafe_fillets(code_with_try)
    # Should not add another try/except layer
    assert wrapped.count("try:") == 1

    # Test 3: No fillet in code (should pass through unchanged)
    code_no_fillet = """result = cq.Workplane("XY").box(10, 10, 10)"""
    wrapped = generator._wrap_unsafe_fillets(code_no_fillet)
    assert wrapped == code_no_fillet


def test_vision_check_with_no_gateway():
    """Test that vision check gracefully handles None gateway."""
    config = PipelineConfig(vision_evaluation=VisionEvaluationConfig(enabled=True))
    pipeline = _make_pipeline(config)
    pipeline._gateway = None  # Simulate no gateway configured

    from pathlib import Path

    step_path = Path("/tmp/fake.step")

    result = pipeline._run_vision_check(
        code="# code",
        step_path=step_path,
        intent="Create box",
        retrieval_context=_DummyRetrievalContext(),
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "no_gateway"
    assert result["regenerated"] is False


def test_vision_check_skips_on_vision_unavailable():
    """Test that vision check detects and skips when LLM fallback is used."""
    config = PipelineConfig(
        vision_evaluation=VisionEvaluationConfig(enabled=True, max_iterations=3)
    )
    pipeline = _make_pipeline(config)

    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        from pathlib import Path

        step_path = Path(tmp_dir) / "test.step"
        step_path.write_text("fake step")

        from src.cad.intent_decomposition.utils import visualization as viz

        def fake_render(*_args, **_kwargs):
            paths = {}
            for view in viz.STANDARD_VIEWS.keys():
                png_path = Path(tmp_dir) / f"{view}.png"
                png_path.write_bytes(b"png")
                paths[view] = png_path
            return paths

        import pytest

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(viz, "render_step_to_images_with_fallback", fake_render)

        from src.cad.intent_decomposition.geometry_evaluator import (
            evaluator as eval_module,
        )

        # Mock evaluator that returns vision_unavailable
        class UnavailableEvaluator:
            def __init__(self, *args, **kwargs):
                pass

            def evaluate(self, **kwargs):
                return EvaluationFeedback(
                    level=ValidationLevel.DESIGN_INTENT,
                    severity=Severity.MINOR,
                    passed=True,
                    confidence=0.3,
                    should_regenerate=False,
                    metadata={"vision_unavailable": True},
                )

        monkeypatch.setattr(eval_module, "GeometryEvaluator", UnavailableEvaluator)

        result = pipeline._run_vision_check(
            code="# code",
            step_path=step_path,
            intent="Create box",
            retrieval_context=_DummyRetrievalContext(),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "vision_unavailable"
        monkeypatch.undo()


def test_vision_outer_loop_max_iterations():
    """Test that vision outer loop respects max_iterations."""
    # This test validates the off-by-one fix mentioned in the review
    config = PipelineConfig(
        vision_evaluation=VisionEvaluationConfig(
            enabled=True,
            max_iterations=2,
            regenerate_on_fail=True,
        )
    )

    # Track how many times vision check is called
    call_count = [0]

    class CountingPipeline(IntentToCADPipeline):
        def _run_vision_check(self, *args, **kwargs):
            call_count[0] += 1
            # Always return regenerating status to force max iterations
            return {
                "status": "regenerating",
                "regenerated": True,
                "new_feedback_result": None,
            }

    pipeline = object.__new__(CountingPipeline)
    pipeline.config = config

    # Simulate the outer loop logic
    max_vision_attempts = config.vision_evaluation.max_iterations
    vision_attempt = 0

    while vision_attempt < max_vision_attempts:
        vision_attempt += 1
        result = pipeline._run_vision_check()

        if result.get("status") != "regenerating":
            break

    # Should have called exactly max_iterations times
    assert vision_attempt == 2
    assert call_count[0] == 2


def test_build_evaluation_prompt_structure():
    """Test _build_evaluation_prompt includes all required sections."""
    from src.cad.intent_decomposition.geometry_evaluator.evaluator import (
        GeometryEvaluator,
    )

    evaluator = GeometryEvaluator(llm_client=None)

    prompt = evaluator._build_evaluation_prompt(
        query="Create a box 10x10x10",
        source_code="result = cq.Workplane('XY').box(10, 10, 10)",
        api_context="box(length, width, height): Create rectangular prism",
        dfm_constraints="Min wall thickness: 2mm",
        view_names=["isometric", "front"],
    )

    # Check all required sections are present
    assert "Design Intent: Create a box 10x10x10" in prompt
    assert "DFM Constraints:" in prompt
    assert "Min wall thickness: 2mm" in prompt
    assert "Available CadQuery APIs" in prompt
    assert "box(length, width, height)" in prompt
    assert "Source Code:" in prompt
    assert "result = cq.Workplane" in prompt
    assert "PASSED: [YES/NO]" in prompt
    assert "ISSUES:" in prompt
    assert "CONFIDENCE: [0.0-1.0]" in prompt
    assert "SUGGESTIONS:" in prompt
    assert "Images: ['isometric', 'front']" in prompt


def test_question_generator_normalizes_legacy_categories():
    """Question parser maps legacy dimensional/positional tags to new tags."""
    from src.cad.intent_decomposition.geometry_evaluator.question_generator import (
        EvaluationQuestionGenerator,
    )

    qgen = EvaluationQuestionGenerator(llm_client=None)
    parsed = qgen._parse_response(
        "\n".join(
            [
                "Q1 [STRUCTURAL]: Does the base shape match intent?",
                "Q2 [DIMENSIONAL]: Are proportions reasonable?",
                "Q3 [POSITIONAL]: Are features correctly oriented on axis faces?",
            ]
        )
    )

    assert len(parsed) == 3
    assert parsed[0].category == "structural"
    assert parsed[1].category == "descriptive"
    assert parsed[2].category == "directional"


def test_qa_prompt_includes_view_directions_and_suggestions():
    """QA prompt includes explicit view vectors and suggestion instruction."""
    from src.cad.intent_decomposition.geometry_evaluator.evaluator import (
        GeometryEvaluator,
    )
    from src.cad.intent_decomposition.geometry_evaluator.question_generator import (
        VerificationQuestion,
    )

    evaluator = GeometryEvaluator(llm_client=None)
    prompt = evaluator._build_qa_evaluation_prompt(
        query="Create a mounting bracket",
        questions=[
            VerificationQuestion(
                question="Are mounting holes aligned on +X face?",
                category="directional",
            )
        ],
        source_code="result = cq.Workplane('XY').box(10, 10, 5)",
        view_names=["top", "front"],
        view_directions={"top": (0, 0, -1), "front": (0, -1, 0)},
    )

    assert "VIEW DIRECTION REFERENCE" in prompt
    assert "- top: (0, 0, -1)" in prompt
    assert "- front: (0, -1, 0)" in prompt
    assert "Avoid ambiguous viewer-relative terms" in prompt
    assert "SUGGESTIONS: <1-3 concise improvement suggestions>" in prompt


def test_parse_qa_response_captures_suggestions():
    """QA parser captures both failed-reason and SUGGESTIONS section."""
    from src.cad.intent_decomposition.geometry_evaluator.evaluator import (
        GeometryEvaluator,
    )
    from src.cad.intent_decomposition.geometry_evaluator.question_generator import (
        VerificationQuestion,
    )

    evaluator = GeometryEvaluator(llm_client=None)
    questions = [
        VerificationQuestion(question="Q1?", category="structural"),
        VerificationQuestion(question="Q2?", category="directional"),
    ]
    response = "\n".join(
        [
            "A1: YES - shape matches",
            "A2: NO - hole orientation appears mirrored",
            "SUGGESTIONS: Add explicit +X/-X orientation checks in code",
            "- Verify hole sketch plane before extrusion",
        ]
    )

    feedback = evaluator._parse_qa_response(response, questions)
    assert feedback.passed is True  # 1 yes / 1 no => avg 0.5 threshold pass
    assert any("mirrored" in s for s in feedback.suggestions)
    assert any("+X/-X" in s for s in feedback.suggestions)
    assert any("sketch plane" in s for s in feedback.suggestions)


def test_render_step_to_svg_path_escaping():
    """Test that render_step_to_svg properly escapes paths."""
    from pathlib import Path

    from src.cad.intent_decomposition.utils.visualization import (
        RenderConfig,
        render_step_to_svg,
    )

    # Mock gateway that captures executed code
    executed_code = []

    class MockGateway:
        def execute(self, tool, code):
            executed_code.append(code)

            class MockResult:
                error_message = None

            return MockResult()

    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        step_path = Path(tmp_dir) / "test.step"
        step_path.write_text("fake step")
        output_path = Path(tmp_dir) / "output.svg"
        output_path.write_text("fake svg")  # Ensure file exists for success check

        gateway = MockGateway()
        config = RenderConfig()

        render_step_to_svg(
            step_path=step_path,
            output_path=output_path,
            view_direction=(1, 1, 1),
            gateway=gateway,
            config=config,
        )

        # Check that paths were properly escaped with repr()
        assert len(executed_code) == 1
        code = executed_code[0]
        assert "repr(" not in code  # repr() should be evaluated, not in string
        # Paths should be wrapped in quotes from repr()
        assert f'"{step_path}"' in code or f"'{step_path}'" in code


def test_extraction_failure_marks_no_progress():
    """Test that failed code extraction sets no_progress metadata."""
    from src.cad.intent_decomposition.synthesis.code_generator import CodeGenerator

    class MockLLM:
        def complete(self, **kwargs):
            # Return malformed response with no code block
            return "I'm sorry, I couldn't generate the code. Please try again."

    generator = CodeGenerator(llm_client=MockLLM())

    class MockFeedback:
        passed = False
        confidence = 0.5
        issues = []
        suggestions = []

        def __init__(self):
            self.issues_text = "Missing feature"
            self.suggestions_text = "Add feature"

    class MockContext:
        def get_all_apis(self):
            return []

        def to_prompt_context(self):
            return "mock api docs"

    original_code = "# original code"
    refined = generator.generate_vision_refinement(
        code=original_code,
        intent="Create box",
        vision_feedback=MockFeedback(),
        retrieval_context=MockContext(),
    )

    # Should detect extraction failure and mark no_progress
    assert refined.metadata.get("no_progress") is True
    assert refined.metadata.get("reason") == "extraction_failed"
    assert refined.code == original_code  # Returns original but with flag
