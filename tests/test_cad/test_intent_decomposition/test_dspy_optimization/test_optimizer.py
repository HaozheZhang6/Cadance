"""Tests for DSPy optimizer module."""

from unittest.mock import MagicMock, patch

from src.cad.intent_decomposition.dspy_optimization.config import (
    DSPyConfig,
    OptimizationMode,
)
from src.cad.intent_decomposition.dspy_optimization.optimizer import (
    DemoCandidate,
    OptimizationConfig,
    OptimizationResult,
)


class TestOptimizationConfig:
    """Tests for OptimizationConfig dataclass."""

    def test_default_values(self):
        """OptimizationConfig should have sensible defaults."""
        config = OptimizationConfig()
        assert config.max_bootstrapped_demos == 4
        assert config.max_labeled_demos == 8
        assert config.max_rounds == 1
        assert config.max_errors == 5
        assert config.auto == "light"

    def test_custom_values(self):
        """OptimizationConfig should accept custom values."""
        config = OptimizationConfig(
            max_bootstrapped_demos=10,
            max_labeled_demos=16,
            max_rounds=3,
            max_errors=10,
            auto="heavy",
        )
        assert config.max_bootstrapped_demos == 10
        assert config.max_labeled_demos == 16
        assert config.max_rounds == 3
        assert config.max_errors == 10
        assert config.auto == "heavy"


class TestOptimizationResult:
    """Tests for OptimizationResult dataclass."""

    def test_default_values(self):
        """OptimizationResult should have proper defaults."""
        result = OptimizationResult(
            stage="code_generation",
            success=True,
        )
        assert result.stage == "code_generation"
        assert result.success is True
        assert result.error is None
        assert result.train_score == 0.0
        assert result.dev_score == 0.0
        assert result.num_demos == 0
        assert result.optimized_module is None

    def test_to_dict(self):
        """to_dict should serialize result without module."""
        result = OptimizationResult(
            stage="code_generation",
            success=True,
            train_score=0.85,
            dev_score=0.80,
            num_demos=5,
            optimized_module=MagicMock(),  # Should not be in dict
        )
        d = result.to_dict()
        assert d["stage"] == "code_generation"
        assert d["success"] is True
        assert d["train_score"] == 0.85
        assert d["dev_score"] == 0.80
        assert d["num_demos"] == 5
        assert "optimized_module" not in d

    def test_failed_result(self):
        """Failed result should include error."""
        result = OptimizationResult(
            stage="decomposition",
            success=False,
            error="No training examples provided",
        )
        assert result.success is False
        assert result.error == "No training examples provided"


class TestDemoCandidate:
    """Tests for DemoCandidate dataclass."""

    def test_sort_key_curriculum_order(self):
        """sort_key should implement curriculum learning order."""
        # Hardest first (lowest IoU)
        easy = DemoCandidate(
            test_id="L1_01", level=1, baseline_iou=0.95, example=MagicMock()
        )
        medium = DemoCandidate(
            test_id="L2_01", level=2, baseline_iou=0.75, example=MagicMock()
        )
        hard = DemoCandidate(
            test_id="L3_01", level=3, baseline_iou=0.50, example=MagicMock()
        )

        # Sort should put hard (lowest IoU) first
        candidates = [easy, medium, hard]
        sorted_candidates = sorted(candidates, key=lambda c: c.sort_key)

        assert sorted_candidates[0].test_id == "L3_01"  # Hardest first
        assert sorted_candidates[1].test_id == "L2_01"
        assert sorted_candidates[2].test_id == "L1_01"

    def test_sort_key_level_tiebreaker(self):
        """For same IoU, lower level should come first."""
        l1 = DemoCandidate(
            test_id="L1_01", level=1, baseline_iou=0.80, example=MagicMock()
        )
        l2 = DemoCandidate(
            test_id="L2_01", level=2, baseline_iou=0.80, example=MagicMock()
        )

        candidates = [l2, l1]
        sorted_candidates = sorted(candidates, key=lambda c: c.sort_key)

        # Same IoU, L1 should come first (simpler concepts first)
        assert sorted_candidates[0].test_id == "L1_01"
        assert sorted_candidates[1].test_id == "L2_01"


class TestDSPyConfig:
    """Tests for DSPyConfig dataclass."""

    def test_default_mode_is_disabled(self):
        """Default mode should be DISABLED."""
        config = DSPyConfig()
        assert config.mode == OptimizationMode.DISABLED

    def test_is_enabled_property(self):
        """is_enabled should be True for non-disabled modes."""
        disabled_config = DSPyConfig(mode=OptimizationMode.DISABLED)
        baseline_config = DSPyConfig(mode=OptimizationMode.BASELINE)
        optimized_config = DSPyConfig(mode=OptimizationMode.OPTIMIZED)

        assert disabled_config.is_enabled is False
        assert baseline_config.is_enabled is True
        assert optimized_config.is_enabled is True

    def test_use_optimized_property(self):
        """use_optimized should only be True for OPTIMIZED mode."""
        disabled_config = DSPyConfig(mode=OptimizationMode.DISABLED)
        baseline_config = DSPyConfig(mode=OptimizationMode.BASELINE)
        optimized_config = DSPyConfig(mode=OptimizationMode.OPTIMIZED)

        assert disabled_config.use_optimized is False
        assert baseline_config.use_optimized is False
        assert optimized_config.use_optimized is True

    def test_string_path_conversion(self):
        """String paths should be converted to Path objects."""
        config = DSPyConfig(optimized_modules_path="some/path")
        from pathlib import Path

        assert isinstance(config.optimized_modules_path, Path)
        assert str(config.optimized_modules_path) == "some/path"


class TestCodeGenerationOptimizer:
    """Tests for CodeGenerationOptimizer class."""

    def test_optimize_no_examples_returns_error(self):
        """Optimization with no examples should return error."""
        with patch(
            "src.cad.intent_decomposition.dspy_optimization.optimizer._check_dspy_available"
        ):
            with patch(
                "src.cad.intent_decomposition.dspy_optimization.optimizer.CodeGenerationModule"
            ):
                from src.cad.intent_decomposition.dspy_optimization.optimizer import (
                    CodeGenerationOptimizer,
                )

                optimizer = CodeGenerationOptimizer()
                result = optimizer.optimize(train_examples=[])
                assert result.success is False
                assert "No training examples" in result.error

    def test_optimize_selects_demos(self):
        """Optimization should select demos from training set."""
        with patch(
            "src.cad.intent_decomposition.dspy_optimization.optimizer._check_dspy_available"
        ):
            with patch(
                "src.cad.intent_decomposition.dspy_optimization.optimizer.CodeGenerationModule"
            ) as mock_module_class:
                with patch(
                    "src.cad.intent_decomposition.dspy_optimization.optimizer.LabeledFewShot"
                ) as mock_optimizer_class:
                    from src.cad.intent_decomposition.dspy_optimization.optimizer import (
                        CodeGenerationOptimizer,
                    )

                    # Setup mocks
                    mock_module = MagicMock()
                    mock_module_class.return_value = mock_module

                    mock_optimizer = MagicMock()
                    mock_optimized = MagicMock()
                    mock_optimized.demos = [MagicMock(), MagicMock()]
                    mock_optimizer.compile.return_value = mock_optimized
                    mock_optimizer_class.return_value = mock_optimizer

                    # Create mock examples
                    mock_examples = [MagicMock() for _ in range(3)]

                    optimizer = CodeGenerationOptimizer()
                    result = optimizer.optimize(train_examples=mock_examples)

                    assert result.success is True
                    assert result.num_demos == 2
                    mock_optimizer.compile.assert_called_once()


class TestDecompositionOptimizer:
    """Tests for DecompositionOptimizer class."""

    def test_optimize_no_examples_returns_error(self):
        """Optimization with no examples should return error."""
        with patch(
            "src.cad.intent_decomposition.dspy_optimization.optimizer._check_dspy_available"
        ):
            with patch(
                "src.cad.intent_decomposition.dspy_optimization.optimizer.DecompositionModule"
            ):
                from src.cad.intent_decomposition.dspy_optimization.optimizer import (
                    DecompositionOptimizer,
                )

                optimizer = DecompositionOptimizer()
                result = optimizer.optimize(train_examples=[])
                assert result.success is False
                assert "No training examples" in result.error
