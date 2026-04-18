"""Tests for DSPy optimization data extraction module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cad.intent_decomposition.dspy_optimization.data_extraction import (
    ExtractionStats,
    TraceLoader,
    TraceToExampleConverter,
)


class TestExtractionStats:
    """Tests for ExtractionStats dataclass."""

    def test_success_rate_zero_total(self):
        """Success rate with zero total should be 0.0."""
        stats = ExtractionStats(total_traces=0)
        assert stats.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Success rate should be calculated correctly."""
        stats = ExtractionStats(total_traces=10, successful_traces=8)
        assert stats.success_rate == 0.8

    def test_str_representation(self):
        """String representation should contain key info."""
        stats = ExtractionStats(
            total_traces=10,
            successful_traces=8,
            failed_traces=2,
            decomposition_examples=5,
            code_generation_examples=5,
            error_correction_examples=0,
        )
        s = str(stats)
        assert "total_traces=10" in s
        assert "successful=8" in s
        assert "80.0%" in s


class TestTraceLoader:
    """Tests for TraceLoader class."""

    def test_init_with_path(self):
        """TraceLoader should accept path as string or Path."""
        loader = TraceLoader("/some/path")
        assert loader.traces_dir == Path("/some/path")

    def test_get_latest_run_dir_returns_none_when_empty(self):
        """get_latest_run_dir should return None for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = TraceLoader(tmpdir)
            result = loader.get_latest_run_dir()
            assert result is None

    def test_get_latest_run_dir_follows_symlink(self):
        """get_latest_run_dir should follow 'latest' symlink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a run directory
            run_dir = tmppath / "2025_01_01_120000"
            run_dir.mkdir()

            # Create latest symlink
            latest = tmppath / "latest"
            latest.symlink_to(run_dir.name)

            loader = TraceLoader(tmpdir)
            result = loader.get_latest_run_dir()
            # Result should resolve to the same directory
            assert result.name == run_dir.name

    def test_load_traces_from_run_handles_missing_dir(self):
        """load_traces_from_run should return empty list for missing dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = TraceLoader(tmpdir)
            result = loader.load_traces_from_run()
            assert result == []

    def test_load_traces_from_run_loads_json_files(self):
        """load_traces_from_run should load trace JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a run directory with a trace file
            run_dir = tmppath / "run_001"
            run_dir.mkdir()

            # Create minimal trace file (matches expected PipelineTrace structure)
            trace_data = {
                "test_id": "L1_01",
                "test_name": "Simple Box",
                "level": 1,
                "intent": "Create a box",
                "overall_success": True,
                "timestamp": "2025-01-01T12:00:00",
                "total_duration_ms": 100.0,
            }
            trace_file = run_dir / "L1_01.json"
            trace_file.write_text(json.dumps(trace_data))

            loader = TraceLoader(tmpdir)
            with patch.object(loader, "get_latest_run_dir", return_value=run_dir):
                traces = loader.load_traces_from_run()

            assert len(traces) == 1
            assert traces[0].test_id == "L1_01"


class TestTraceToExampleConverter:
    """Tests for TraceToExampleConverter class."""

    def test_init_default_threshold(self):
        """Converter should have default IoU threshold of 0.9."""
        converter = TraceToExampleConverter()
        assert converter.iou_threshold == 0.9

    def test_init_custom_threshold(self):
        """Converter should accept custom IoU threshold."""
        converter = TraceToExampleConverter(iou_threshold=0.8)
        assert converter.iou_threshold == 0.8

    def test_is_successful_with_high_iou(self):
        """Trace with IoU >= threshold should be successful."""
        converter = TraceToExampleConverter(iou_threshold=0.9)

        # Create mock trace with high IoU
        mock_trace = MagicMock()
        mock_trace.comparison = MagicMock()
        mock_trace.comparison.iou_score = 0.95
        mock_trace.overall_success = True

        assert converter.is_successful(mock_trace) is True

    def test_is_successful_with_low_iou(self):
        """Trace with IoU < threshold should not be successful."""
        converter = TraceToExampleConverter(iou_threshold=0.9)

        # Create mock trace with low IoU
        mock_trace = MagicMock()
        mock_trace.comparison = MagicMock()
        mock_trace.comparison.iou_score = 0.5
        mock_trace.overall_success = False

        assert converter.is_successful(mock_trace) is False

    def test_is_successful_no_comparison(self):
        """Trace without comparison data should not be successful."""
        converter = TraceToExampleConverter()

        mock_trace = MagicMock()
        mock_trace.comparison = None

        assert converter.is_successful(mock_trace) is False

    def test_extract_decomposition_examples(self):
        """extract_decomposition_examples should create DSPy Examples."""
        with patch(
            "src.cad.intent_decomposition.dspy_optimization.data_extraction.dspy"
        ) as mock_dspy:
            # Setup mock Example class
            mock_example = MagicMock()
            mock_example.with_inputs.return_value = mock_example
            mock_dspy.Example.return_value = mock_example

            converter = TraceToExampleConverter()

            # Create a mock successful trace
            mock_trace = MagicMock()
            mock_trace.intent = "Create a box"
            mock_trace.test_id = "L1_01"
            mock_trace.comparison = MagicMock()
            mock_trace.comparison.iou_score = 0.95
            mock_trace.overall_success = True
            mock_trace.decomposition = MagicMock()
            mock_trace.decomposition.success = True
            mock_trace.decomposition.operations = [{"primitive": "box"}]
            mock_trace.decomposition.overall_confidence = 0.9
            mock_trace.decomposition.ambiguities = []

            examples = converter.extract_decomposition_examples([mock_trace])

            assert len(examples) == 1
            mock_dspy.Example.assert_called()

    def test_extract_code_generation_examples(self):
        """extract_code_generation_examples should create DSPy Examples."""
        with patch(
            "src.cad.intent_decomposition.dspy_optimization.data_extraction.dspy"
        ) as mock_dspy:
            # Setup mock Example class
            mock_example = MagicMock()
            mock_example.with_inputs.return_value = mock_example
            mock_dspy.Example.return_value = mock_example

            converter = TraceToExampleConverter()

            # Create a mock successful trace with all required attributes
            mock_trace = MagicMock()
            mock_trace.intent = "Create a box"
            mock_trace.test_id = "L1_01"
            mock_trace.comparison = MagicMock()
            mock_trace.comparison.iou_score = 0.95
            mock_trace.overall_success = True
            mock_trace.decomposition = MagicMock()
            mock_trace.decomposition.operations = [{"primitive": "box"}]
            mock_trace.retrieval = MagicMock()
            mock_trace.retrieval.operation_retrievals = []
            mock_trace.synthesis = MagicMock()
            mock_trace.synthesis.success = True
            mock_trace.synthesis.generated_code = "result = cq.Workplane().box(1,1,1)"
            mock_trace.final_code = "result = cq.Workplane().box(1,1,1)"

            examples = converter.extract_code_generation_examples([mock_trace])

            assert len(examples) == 1
            mock_dspy.Example.assert_called()
