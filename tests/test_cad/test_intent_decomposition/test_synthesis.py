"""Tests for the synthesis module (code generation)."""

from src.cad.intent_decomposition.operations.operation_types import (
    CADOperation,
    OperationSequence,
)
from src.cad.intent_decomposition.operations.primitives import CADPrimitive
from src.cad.intent_decomposition.retrieval.api_catalog.cadquery_catalog import (
    CadQueryAPICatalog,
)
from src.cad.intent_decomposition.retrieval.retriever import (
    RetrievalContext,
)
from src.cad.intent_decomposition.synthesis.code_generator import (
    GeneratedCode,
    MockCodeGenerator,
)
from src.cad.intent_decomposition.synthesis.prompts import (
    CODE_GENERATION_PROMPTS,
    get_all_signatures_reference,
)


def make_empty_retrieval_context() -> RetrievalContext:
    """Helper to create an empty RetrievalContext for testing."""
    return RetrievalContext(operations=[], metadata={})


class TestGeneratedCode:
    """Tests for the GeneratedCode dataclass."""

    def test_generated_code_creation(self):
        """Test basic GeneratedCode creation."""
        code = GeneratedCode(
            code="import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
            explanation="Creates a simple box",
            confidence=0.85,
        )
        assert code.code is not None
        assert code.confidence == 0.85
        assert code.explanation == "Creates a simple box"

    def test_generated_code_str(self):
        """Test string representation."""
        code = GeneratedCode(
            code="import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
            confidence=0.85,
        )
        str_repr = str(code)
        assert "confidence=0.85" in str_repr
        assert "lines=2" in str_repr

    def test_is_valid_syntax_valid(self):
        """Test syntax validation with valid code."""
        code = GeneratedCode(
            code="import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
        )
        assert code.is_valid_syntax is True

    def test_is_valid_syntax_invalid(self):
        """Test syntax validation with invalid code."""
        code = GeneratedCode(
            code="import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, ",  # Missing closing
        )
        assert code.is_valid_syntax is False

    def test_has_result_variable_true(self):
        """Test result variable detection when present."""
        code = GeneratedCode(
            code="import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
        )
        assert code.has_result_variable is True

    def test_has_result_variable_false(self):
        """Test result variable detection when missing."""
        code = GeneratedCode(
            code="import cadquery as cq\nbox = cq.Workplane('XY').box(10, 10, 10)",
        )
        assert code.has_result_variable is False


class TestCodeGenerationPrompts:
    """Tests for code generation prompts."""

    def test_system_prompt_exists(self):
        """Test that system prompt exists and is non-empty."""
        assert CODE_GENERATION_PROMPTS.SYSTEM is not None
        assert len(CODE_GENERATION_PROMPTS.SYSTEM) > 100

    def test_system_prompt_content(self):
        """Test system prompt contains key concepts."""
        prompt = CODE_GENERATION_PROMPTS.SYSTEM
        assert "CadQuery" in prompt
        assert "result" in prompt.lower()

    def test_build_generation_prompt(self):
        """Test building a generation prompt."""
        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 10, "width": 10, "height": 10},
                )
            ]
        )

        retrieval_context = make_empty_retrieval_context()

        prompt = CODE_GENERATION_PROMPTS.build_generation_prompt(
            intent="Create a simple box",
            operations=operations,
            retrieval_context=retrieval_context,
        )

        assert "Create a simple box" in prompt
        assert "box" in prompt.lower()

    def test_build_error_correction_prompt(self):
        """Test building an error correction prompt."""
        code = "result = cq.Workplane('XY').box(10, 10)"
        error = "TypeError: box() missing required argument: 'height'"
        analysis = "Missing height argument in box() call"

        retrieval_context = make_empty_retrieval_context()

        prompt = CODE_GENERATION_PROMPTS.build_error_correction_prompt(
            code=code,
            error=error,
            analysis=analysis,
            retrieval_context=retrieval_context,
        )

        assert code in prompt
        assert error in prompt
        assert analysis in prompt

    def test_build_refinement_prompt(self):
        """Test building a geometry refinement prompt."""
        code = "result = cq.Workplane('XY').box(10, 10, 10)"
        current = {"volume": 1000.0}
        expected = {"volume": 2000.0}
        differences = "Volume: expected 2000.0, got 1000.0"

        prompt = CODE_GENERATION_PROMPTS.build_refinement_prompt(
            code=code,
            current_properties=current,
            expected_properties=expected,
            differences=differences,
        )

        assert code in prompt
        assert "2000.0" in prompt or "volume" in prompt.lower()


class TestMockCodeGenerator:
    """Tests for MockCodeGenerator."""

    def test_mock_generator_creation(self):
        """Test mock generator creation."""
        generator = MockCodeGenerator()
        assert generator.generate_count == 0

    def test_mock_generate_box(self):
        """Test mock generation for box operation."""
        generator = MockCodeGenerator()

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 20, "width": 15, "height": 10},
                )
            ]
        )

        retrieval_context = make_empty_retrieval_context()

        result = generator.generate(
            intent="Create a box",
            operations=operations,
            retrieval_context=retrieval_context,
        )

        assert result.code is not None
        assert "import cadquery as cq" in result.code
        assert "result" in result.code
        assert ".box(" in result.code
        assert "20" in result.code  # length
        assert generator.generate_count == 1

    def test_mock_generate_cylinder(self):
        """Test mock generation for cylinder operation."""
        generator = MockCodeGenerator()

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.CYLINDER,
                    description="Create a cylinder",
                    parameters={"height": 30, "radius": 5},
                )
            ]
        )

        retrieval_context = make_empty_retrieval_context()

        result = generator.generate(
            intent="Create a cylinder",
            operations=operations,
            retrieval_context=retrieval_context,
        )

        assert ".cylinder(" in result.code

    def test_mock_generate_with_hole(self):
        """Test mock generation for box with hole."""
        generator = MockCodeGenerator()

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 20, "width": 20, "height": 10},
                ),
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Add a hole",
                    parameters={"diameter": 5},
                    dependencies=[0],
                ),
            ]
        )

        retrieval_context = make_empty_retrieval_context()

        result = generator.generate(
            intent="Create a box with a hole",
            operations=operations,
            retrieval_context=retrieval_context,
        )

        assert ".box(" in result.code
        assert ".hole(" in result.code
        assert 'faces(">Z")' in result.code

    def test_mock_generate_fix(self):
        """Test mock fix generation returns original code."""
        generator = MockCodeGenerator()
        original_code = "result = cq.Workplane('XY').box(10, 10)"

        retrieval_context = make_empty_retrieval_context()

        result = generator.generate_fix(
            code=original_code,
            error="Some error",
            analysis="Some analysis",
            retrieval_context=retrieval_context,
        )

        assert result.code == original_code
        assert generator.generate_count == 1

    def test_mock_generate_refinement(self):
        """Test mock refinement returns original code."""
        generator = MockCodeGenerator()
        original_code = "result = cq.Workplane('XY').box(10, 10, 10)"

        result = generator.generate_refinement(
            code=original_code,
            current_properties={"volume": 1000.0},
            expected_properties={"volume": 2000.0},
            differences="Volume mismatch",
        )

        assert result.code == original_code
        assert generator.generate_count == 1


class TestCodeGeneratorTemperature:
    """Tests for CodeGenerator temperature passing."""

    def test_generate_passes_default_temperature(self):
        """generate() should pass DEFAULT_TEMPERATURE=0.2 to LLM."""
        from unittest.mock import MagicMock

        from src.cad.intent_decomposition.synthesis.code_generator import (
            CodeGenerator,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = (
            "```python\nimport cadquery as cq\n"
            "result = cq.Workplane('XY').box(10, 10, 10)\n```"
        )

        gen = CodeGenerator(mock_llm)
        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="box",
                    parameters={},
                )
            ]
        )

        gen.generate("box", operations, make_empty_retrieval_context())

        call_kwargs = mock_llm.complete.call_args[1]
        assert call_kwargs["temperature"] == 0.2

    def test_generate_fix_passes_default_temperature(self):
        """generate_fix() should pass DEFAULT_TEMPERATURE=0.2 to LLM."""
        from unittest.mock import MagicMock

        from src.cad.intent_decomposition.synthesis.code_generator import (
            CodeGenerator,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = (
            "```python\nresult = cq.Workplane('XY').box(10, 10, 10)\n```"
        )

        gen = CodeGenerator(mock_llm)
        gen.generate_fix(
            code="result = broken",
            error="SyntaxError",
            analysis="bad syntax",
            retrieval_context=make_empty_retrieval_context(),
        )

        call_kwargs = mock_llm.complete.call_args[1]
        assert call_kwargs["temperature"] == 0.2


class TestCodeGeneratorExtraction:
    """Tests for code extraction from LLM responses."""

    def test_extract_code_from_markdown_block(self):
        """Test extracting code from markdown code block."""
        generator = MockCodeGenerator()

        # The MockCodeGenerator doesn't have _extract_code, so we test
        # the generated code structure instead
        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 10, "width": 10, "height": 10},
                )
            ]
        )

        result = generator.generate(
            intent="Create a box",
            operations=operations,
            retrieval_context=make_empty_retrieval_context(),
        )

        # Verify the generated code is clean (no markdown)
        assert "```" not in result.code
        assert result.code.startswith("import cadquery")


class TestCodeGeneratorConfidence:
    """Tests for confidence estimation in code generation."""

    def test_mock_generator_confidence(self):
        """Test that mock generator provides reasonable confidence."""
        generator = MockCodeGenerator()

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.BOX,
                    description="Create a box",
                    parameters={"length": 10, "width": 10, "height": 10},
                )
            ]
        )

        result = generator.generate(
            intent="Create a box",
            operations=operations,
            retrieval_context=make_empty_retrieval_context(),
        )

        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence == 0.8  # Mock always returns 0.8

    def test_generated_code_with_assumptions(self):
        """Test generated code can include assumptions."""
        code = GeneratedCode(
            code="result = cq.Workplane('XY').box(10, 10, 10)",
            assumptions=["Assumed centered at origin", "Assumed default units (mm)"],
            confidence=0.7,
        )

        assert len(code.assumptions) == 2
        assert "origin" in code.assumptions[0]


class TestSignatureReference:
    """Tests for API signature reference generation."""

    def test_get_all_signatures_reference(self):
        """Test that signature reference includes all APIs."""
        catalog = CadQueryAPICatalog()
        reference = get_all_signatures_reference(catalog)

        # Should have header
        assert "API Quick Reference" in reference

        # Should include key API signatures
        assert "box" in reference
        assert "hole" in reference
        assert "transformed" in reference
        assert "Workplane" in reference

    def test_signature_reference_format(self):
        """Test that signatures are formatted correctly."""
        catalog = CadQueryAPICatalog()
        reference = get_all_signatures_reference(catalog)

        # Signatures should be in backticks
        assert "`Workplane." in reference

    def test_build_generation_prompt_with_catalog(self):
        """Test build_generation_prompt with catalog for signature reference."""
        catalog = CadQueryAPICatalog()

        operations = OperationSequence(
            operations=[
                CADOperation(
                    primitive=CADPrimitive.HOLE,
                    description="Create a hole",
                    parameters={"diameter": 5},
                )
            ]
        )

        retrieval_context = make_empty_retrieval_context()

        prompt = CODE_GENERATION_PROMPTS.build_generation_prompt(
            intent="Create a hole",
            operations=operations,
            retrieval_context=retrieval_context,
            catalog=catalog,
        )

        # Should include signature reference
        assert "API Quick Reference" in prompt
        assert "transformed" in prompt
