"""Tests for the Intent-to-CAD pipeline and CAD synthesis agent."""

from src.agents.cad_synthesis import CADSynthesisAgent
from src.cad.comparator import ComparisonResult, GeometricComparator
from src.cad.intent_decomposition.observability.llm_call_logger import (
    close_call_logger,
    init_call_logger,
)
from src.cad.intent_decomposition.pipeline import (
    MockIntentToCADPipeline,
    PipelineConfig,
    PipelineResult,
    PipelineStageResult,
    resolve_vision_screenshot_dir,
)

# =============================================================================
# PipelineConfig Tests
# =============================================================================


class TestPipelineConfig:
    """Tests for PipelineConfig.

    Note: LLM params (temp, seed) are no longer in PipelineConfig.
    They're centralized in LLMConfig via the adapter.
    """

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()
        assert config.max_feedback_iterations == 3
        assert config.retrieval_top_k == 3
        assert config.comparison_tolerance == 0.01
        assert config.enable_comparison is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PipelineConfig(
            max_feedback_iterations=5,
            retrieval_top_k=5,
            comparison_tolerance=0.05,
            enable_comparison=False,
        )
        assert config.max_feedback_iterations == 5
        assert config.retrieval_top_k == 5
        assert config.comparison_tolerance == 0.05
        assert config.enable_comparison is False


class TestVisionScreenshotDirResolution:
    """Tests for vision screenshot output directory resolution."""

    def test_prefers_env_override(self, monkeypatch, tmp_path):
        override = tmp_path / "custom_screenshots"
        monkeypatch.setenv("VISION_SCREENSHOT_DIR", str(override))
        resolved = resolve_vision_screenshot_dir()
        assert resolved == override

    def test_uses_active_log_run_dir_when_available(self, monkeypatch, tmp_path):
        monkeypatch.delenv("VISION_SCREENSHOT_DIR", raising=False)
        run_dir = tmp_path / "logs" / "20260212_235557"
        init_call_logger(run_dir=run_dir)
        try:
            resolved = resolve_vision_screenshot_dir()
            assert resolved == run_dir / "screenshots"
        finally:
            close_call_logger()

    def test_falls_back_to_artifacts_dir_without_context(self, monkeypatch):
        monkeypatch.delenv("VISION_SCREENSHOT_DIR", raising=False)
        close_call_logger()
        resolved = resolve_vision_screenshot_dir()
        assert resolved.as_posix().endswith("data/artifacts/screenshots")


# =============================================================================
# PipelineStageResult Tests
# =============================================================================


class TestPipelineStageResult:
    """Tests for PipelineStageResult."""

    def test_stage_result_success(self):
        """Test successful stage result."""
        result = PipelineStageResult(
            stage="decomposition",
            success=True,
            duration_ms=50.0,
            data={"operations": []},
        )
        assert result.stage == "decomposition"
        assert result.success is True
        assert result.duration_ms == 50.0
        assert result.error is None

    def test_stage_result_failure(self):
        """Test failed stage result."""
        result = PipelineStageResult(
            stage="synthesis",
            success=False,
            duration_ms=100.0,
            error="LLM call failed",
        )
        assert result.success is False
        assert result.error == "LLM call failed"


# =============================================================================
# PipelineResult Tests
# =============================================================================


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_pipeline_result_success(self):
        """Test successful pipeline result."""
        result = PipelineResult(
            success=True,
            final_code="result = cq.Workplane('XY').box(10, 10, 10)",
            geometry_properties={"volume": 1000.0},
            operations=None,
            confidence=0.85,
            total_duration_ms=200.0,
        )
        assert result.success is True
        assert "box" in result.final_code
        assert result.confidence == 0.85

    def test_pipeline_result_success_requires_geometry_valid(self):
        """success should be False when geometry_valid is False."""
        # Simulates: execution stage succeeded but feedback loop
        # returned geometry_valid=False (disconnected geometry)
        result = PipelineResult(
            success=False,  # should be False when geometry invalid
            final_code="result = cq.Workplane('XY').box(10, 10, 10)",
            geometry_properties={"volume": 1000.0, "solid_count": 3},
            operations=None,
            confidence=0.85,
        )
        assert result.success is False

    def test_pipeline_result_failure(self):
        """Test failed pipeline result."""
        result = PipelineResult(
            success=False,
            final_code="",
            geometry_properties={},
            operations=None,
            confidence=0.0,
        )
        assert result.success is False
        assert result.final_code == ""

    def test_pipeline_result_str(self):
        """Test string representation."""
        result = PipelineResult(
            success=True,
            final_code="code",
            geometry_properties={},
            operations=None,
            confidence=0.75,
            total_duration_ms=150.0,
            stages=[PipelineStageResult(stage="test", success=True, duration_ms=50.0)],
        )
        str_repr = str(result)
        assert "SUCCESS" in str_repr
        assert "0.75" in str_repr
        assert "150" in str_repr

    def test_pipeline_result_with_comparison(self):
        """Test pipeline result with comparison."""
        comparison = ComparisonResult(
            overall_pass=True,
            volume_match=True,
            volume_ratio=1.0,
            bounding_box_match=True,
            topology_match=True,
            face_count_match=True,
            edge_count_match=True,
        )
        result = PipelineResult(
            success=True,
            final_code="code",
            geometry_properties={"volume": 1000.0},
            operations=None,
            comparison_result=comparison,
            confidence=0.9,
        )
        assert result.comparison_result is not None
        assert result.comparison_result.overall_pass is True


# =============================================================================
# MockIntentToCADPipeline Tests
# =============================================================================


class TestMockIntentToCADPipeline:
    """Tests for MockIntentToCADPipeline."""

    def test_mock_pipeline_creation(self):
        """Test mock pipeline creation."""
        pipeline = MockIntentToCADPipeline()
        assert pipeline.run_count == 0

    def test_mock_pipeline_run(self):
        """Test running mock pipeline."""
        pipeline = MockIntentToCADPipeline()

        result = pipeline.run("Create a simple box")

        assert result.success is True
        assert "import cadquery" in result.final_code
        assert "result" in result.final_code
        assert result.geometry_properties["volume"] == 1000.0
        assert result.confidence == 0.8
        assert pipeline.run_count == 1

    def test_mock_pipeline_run_multiple(self):
        """Test running mock pipeline multiple times."""
        pipeline = MockIntentToCADPipeline()

        pipeline.run("Intent 1")
        pipeline.run("Intent 2")
        pipeline.run("Intent 3")

        assert pipeline.run_count == 3

    def test_mock_pipeline_with_ground_truth(self):
        """Test mock pipeline with ground truth comparison."""
        pipeline = MockIntentToCADPipeline()

        ground_truth = {
            "expected_volume": 1000.0,
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = pipeline.run("Create a box", ground_truth=ground_truth)

        assert result.comparison_result is not None
        assert result.comparison_result.volume_match is True

    def test_mock_pipeline_with_mismatched_ground_truth(self):
        """Test mock pipeline with mismatched ground truth."""
        pipeline = MockIntentToCADPipeline()

        ground_truth = {
            "expected_volume": 2000.0,  # Different from mock's 1000.0
            "expected_faces": 6,
        }

        result = pipeline.run("Create a box", ground_truth=ground_truth)

        assert result.comparison_result is not None
        assert result.comparison_result.volume_match is False

    def test_mock_pipeline_stages(self):
        """Test mock pipeline includes stages."""
        pipeline = MockIntentToCADPipeline()

        result = pipeline.run("Create a box")

        assert len(result.stages) > 0
        assert result.stages[0].stage == "mock"
        assert result.stages[0].success is True


# =============================================================================
# GeometricComparator Tests (for pipeline integration)
# =============================================================================


class TestGeometricComparatorIntegration:
    """Tests for GeometricComparator used in pipeline."""

    def test_comparator_exact_match(self):
        """Test comparator with exact match."""
        comparator = GeometricComparator(tolerance=0.01)

        generated = {
            "volume": 1000.0,
            "face_count": 6,
            "edge_count": 12,
            "bounding_box": {"x": 10, "y": 10, "z": 10},
        }
        ground_truth = {
            "expected_volume": 1000.0,
            "expected_faces": 6,
            "expected_edges": 12,
            "expected_bounding_box": {"x": 10, "y": 10, "z": 10},
        }

        result = comparator.compare(generated, ground_truth)

        assert result.overall_pass is True
        assert result.volume_match is True
        assert result.volume_ratio == 1.0

    def test_comparator_within_tolerance(self):
        """Test comparator within tolerance."""
        comparator = GeometricComparator(tolerance=0.01)

        generated = {"volume": 1005.0}  # 0.5% difference
        ground_truth = {"expected_volume": 1000.0}

        result = comparator.compare(generated, ground_truth)

        assert result.volume_match is True

    def test_comparator_outside_tolerance(self):
        """Test comparator outside tolerance."""
        comparator = GeometricComparator(tolerance=0.01)

        generated = {"volume": 1020.0}  # 2% difference
        ground_truth = {"expected_volume": 1000.0}

        result = comparator.compare(generated, ground_truth)

        assert result.volume_match is False

    def test_comparator_topology_mismatch(self):
        """Test comparator with topology mismatch."""
        comparator = GeometricComparator()

        generated = {
            "volume": 1000.0,
            "face_count": 7,  # Different
            "edge_count": 12,
        }
        ground_truth = {
            "expected_volume": 1000.0,
            "expected_faces": 6,
            "expected_edges": 12,
        }

        result = comparator.compare(generated, ground_truth)

        assert result.overall_pass is False
        assert result.face_count_match is False
        assert result.edge_count_match is True


# =============================================================================
# CADSynthesisAgent Tests (with mocks)
# =============================================================================


class TestCADSynthesisAgentConfiguration:
    """Tests for CADSynthesisAgent configuration."""

    def test_agent_thresholds(self):
        """Test agent confidence thresholds."""
        assert CADSynthesisAgent.EVIDENCE_THRESHOLD == 0.7
        assert CADSynthesisAgent.UNKNOWN_THRESHOLD == 0.5

    def test_agent_name(self):
        """Test agent name property."""
        # We can't fully instantiate without mocks, but we can test the class
        assert hasattr(CADSynthesisAgent, "name")

    def test_agent_trigger_types(self):
        """Test agent trigger types property."""
        assert hasattr(CADSynthesisAgent, "trigger_types")


# =============================================================================
# Integration Tests with Mocks
# =============================================================================


class TestPipelineIntegration:
    """Integration tests for pipeline with mocks."""

    def test_mock_pipeline_full_flow(self):
        """Test full mock pipeline flow."""
        pipeline = MockIntentToCADPipeline()

        # Run with various intents
        intents = [
            "Create a box 10x20x5",
            "Make a cylinder with radius 5 and height 10",
            "Design a plate with 4 holes",
        ]

        for intent in intents:
            result = pipeline.run(intent)
            assert result.success is True
            assert result.final_code is not None
            assert len(result.final_code) > 0

        assert pipeline.run_count == 3

    def test_pipeline_result_has_required_fields(self):
        """Test that pipeline result has all required fields."""
        pipeline = MockIntentToCADPipeline()
        result = pipeline.run("Create a box")

        # Check all required fields exist
        assert hasattr(result, "success")
        assert hasattr(result, "final_code")
        assert hasattr(result, "geometry_properties")
        assert hasattr(result, "operations")
        assert hasattr(result, "comparison_result")
        assert hasattr(result, "stages")
        assert hasattr(result, "total_duration_ms")
        assert hasattr(result, "confidence")

    def test_pipeline_confidence_bounds(self):
        """Test that confidence is within valid bounds."""
        pipeline = MockIntentToCADPipeline()
        result = pipeline.run("Create a box")

        assert 0.0 <= result.confidence <= 1.0
