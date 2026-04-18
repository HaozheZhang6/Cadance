"""Evaluation runner for Intent-to-CAD pipeline.

Runs the pipeline against the evaluation suite and measures performance
against ground truth specifications.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from src.cad.comparator import ComparisonResult, GeometricComparator
from src.cad.intent_decomposition.pipeline import (
    IntentToCADPipeline,
    MockIntentToCADPipeline,
    PipelineConfig,
    PipelineResult,
)
from src.cad.metrics import EvaluationMetrics, compute_metrics

if TYPE_CHECKING:
    from src.cad.intent_decomposition.observability import TraceCollector

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class EvalTestCase:
    """A single test case from the evaluation suite.

    Named EvalTestCase to avoid pytest collection warning.
    """

    path: Path
    test_id: str
    name: str
    level: int
    intent: str
    spec: dict[str, Any]
    skills_tested: list[str] = field(default_factory=list)
    complexity_score: int = 0
    split: str = "train"  # "train" or "eval"


@dataclass
class EvaluationResult:
    """Result from evaluating a single test case with the pipeline."""

    test_case: EvalTestCase
    pipeline_result: PipelineResult | None
    comparison: ComparisonResult | None
    success: bool
    error: str | None = None
    execution_time_ms: float = 0.0

    @property
    def test_id(self) -> str:
        return self.test_case.test_id

    @property
    def level(self) -> int:
        return self.test_case.level

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metrics computation."""
        return {
            "test_id": self.test_id,
            "level": self.level,
            "success": self.success,
            "skills_tested": self.test_case.skills_tested,
            "execution_time_ms": self.execution_time_ms,
            "pipeline_confidence": (
                self.pipeline_result.confidence if self.pipeline_result else 0.0
            ),
            "split": self.test_case.split,
        }


@dataclass
class EvaluationReport:
    """Full evaluation report with all results and metrics."""

    results: list[EvaluationResult]
    metrics: EvaluationMetrics
    total_duration_ms: float
    config: PipelineConfig
    split: str | None = None  # Which split was run ("train", "eval", or None for all)

    def summary(self) -> str:
        """Generate summary string."""
        split_label = f" ({self.split.upper()} split)" if self.split else ""
        lines = [
            "=" * 60,
            f"Intent-to-CAD Pipeline Evaluation Report{split_label}",
            "=" * 60,
            "",
            f"Total Tests: {self.metrics.total_tests}",
            f"Passed: {self.metrics.passed}",
            f"Failed: {self.metrics.failed}",
            f"Success Rate: {self.metrics.success_rate:.1%}",
            f"Total Duration: {self.total_duration_ms:.0f}ms",
            "",
            "By Level:",
        ]

        for level, stats in sorted(self.metrics.by_level.items()):
            lines.append(
                f"  Level {level}: {stats['passed']}/{stats['total']} "
                f"({stats['success_rate']:.1%})"
            )

        # Show metrics by split if running both splits
        if not self.split and self.results:
            by_split = self._compute_split_metrics()
            if by_split:
                lines.append("")
                lines.append("By Split:")
                for split_name, stats in sorted(by_split.items()):
                    lines.append(
                        f"  {split_name.upper()}: {stats['passed']}/{stats['total']} "
                        f"({stats['success_rate']:.1%})"
                    )

        if self.metrics.by_skill:
            lines.append("")
            lines.append("By Skill:")
            for skill, stats in sorted(self.metrics.by_skill.items()):
                lines.append(
                    f"  {skill}: {stats['passed']}/{stats['total']} "
                    f"({stats['success_rate']:.1%})"
                )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _compute_split_metrics(self) -> dict[str, dict[str, Any]]:
        """Compute metrics grouped by split."""
        by_split: dict[str, dict[str, Any]] = {}
        for result in self.results:
            split = result.test_case.split
            if split not in by_split:
                by_split[split] = {"total": 0, "passed": 0}
            by_split[split]["total"] += 1
            if result.success:
                by_split[split]["passed"] += 1

        # Compute success rates
        for split in by_split:
            total = by_split[split]["total"]
            passed = by_split[split]["passed"]
            by_split[split]["success_rate"] = passed / total if total > 0 else 0.0

        return by_split


# =============================================================================
# Evaluation Runner
# =============================================================================


class EvaluationRunner:
    """Runs the Intent-to-CAD pipeline against the evaluation suite.

    Discovers test cases, runs them through the pipeline, and compares
    results against ground truth specifications.

    Example:
        runner = EvaluationRunner(
            pipeline=IntentToCADPipeline(...),
            suite_path=Path("tests/test_tools/test_cadquery/evaluation_suite"),
        )

        # Run all levels
        report = runner.run_all()
        print(report.summary())

        # Run specific levels
        report = runner.run_levels([1, 2])
        print(f"Success rate: {report.metrics.success_rate:.1%}")

        # Run only train split (default for development)
        report = runner.run_all(split="train")

        # Run only eval split (for final evaluation)
        report = runner.run_all(split="eval")
    """

    def __init__(
        self,
        pipeline: IntentToCADPipeline | MockIntentToCADPipeline,
        suite_path: Path | None = None,
        comparator: GeometricComparator | None = None,
    ):
        """Initialize the evaluation runner.

        Args:
            pipeline: The Intent-to-CAD pipeline to evaluate.
            suite_path: Path to evaluation_suite directory.
            comparator: Geometric comparator (default: 1% tolerance).
        """
        self.pipeline = pipeline
        self.comparator = comparator or GeometricComparator(tolerance=0.01)

        if suite_path is None:
            suite_path = Path(__file__).parent / "evaluation_suite"
        self.suite_path = suite_path

        # Load manifest for split assignments
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        """Load the manifest.json file for split assignments.

        Returns:
            Manifest dictionary with split assignments, or empty dict if not found.
        """
        manifest_path = self.suite_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load manifest: {e}")
        return {}

    def discover_test_cases(
        self,
        levels: list[int] | None = None,
        split: str | None = None,
        test_ids: list[str] | None = None,
    ) -> list[EvalTestCase]:
        """Discover test cases from the evaluation suite.

        Searches in train/ and eval/ subdirectories based on split filter.

        Args:
            levels: Optional list of levels to include (1-4).
                   If None, includes all levels.
            split: Optional split filter ("train" or "eval").
                   If None, includes all splits.
            test_ids: Optional list of specific test IDs to include.
                   If provided, only returns tests matching these IDs.

        Returns:
            List of TestCase objects.
        """
        test_cases = []

        if not self.suite_path.exists():
            logger.warning(f"Suite path does not exist: {self.suite_path}")
            return test_cases

        level_names = {
            1: "level_1_easy",
            2: "level_2_medium",
            3: "level_3_hard",
            4: "level_4_expert",
        }

        # Determine which split directories to search
        if split == "train":
            split_dirs = ["train"]
        elif split == "eval":
            split_dirs = ["eval"]
        else:
            split_dirs = ["train", "eval"]

        for split_name in split_dirs:
            split_dir = self.suite_path / split_name
            if not split_dir.exists():
                continue

            for level_dir in sorted(split_dir.glob("level_*")):
                if not level_dir.is_dir():
                    continue

                # Extract level number
                level_num = None
                for num, name in level_names.items():
                    if name in level_dir.name:
                        level_num = num
                        break

                if level_num is None:
                    continue

                # Filter by level if specified
                if levels is not None and level_num not in levels:
                    continue

                for test_dir in sorted(level_dir.glob("L*")):
                    if not test_dir.is_dir():
                        continue

                    test_case = self._load_test_case(test_dir, split_name)
                    if test_case:
                        test_cases.append(test_case)

        # Filter by test_ids if provided
        if test_ids:
            test_ids_set = set(test_ids)
            test_cases = [tc for tc in test_cases if tc.test_id in test_ids_set]

        return test_cases

    def _load_test_case(self, test_dir: Path, split: str) -> EvalTestCase | None:
        """Load a test case from a directory.

        Args:
            test_dir: Path to test case directory.
            split: The split this test belongs to ("train" or "eval"),
                   determined by directory location.

        Returns:
            TestCase or None if invalid.
        """
        spec_file = test_dir / "spec.json"
        intent_file = test_dir / "intent.txt"

        if not spec_file.exists():
            logger.warning(f"No spec.json in {test_dir}")
            return None

        if not intent_file.exists():
            logger.warning(f"No intent.txt in {test_dir}")
            return None

        try:
            with open(spec_file) as f:
                spec = json.load(f)

            intent = intent_file.read_text().strip()

            test_id = spec.get("id", test_dir.name)

            return EvalTestCase(
                path=test_dir,
                test_id=test_id,
                name=spec.get("name", test_dir.name),
                level=spec.get("level", 0),
                intent=intent,
                spec=spec,
                skills_tested=spec.get("skills_tested", []),
                complexity_score=spec.get("complexity_score", 0),
                split=split,  # Determined by directory location
            )
        except Exception as e:
            logger.error(f"Failed to load test case from {test_dir}: {e}")
            return None

    def run_single(
        self,
        test_case: EvalTestCase,
        trace_collector: TraceCollector | None = None,
    ) -> EvaluationResult:
        """Run a single test case through the pipeline.

        Args:
            test_case: The test case to run.
            trace_collector: Optional TraceCollector for observability.
                If provided, trace data is recorded during execution.

        Returns:
            EvaluationResult with pipeline output and comparison.
        """
        start_time = time.time()

        try:
            # Run pipeline with intent
            # Note: ground_truth_geometry param kept for backward compatibility but unused
            pipeline_result = self.pipeline.run(
                intent=test_case.intent,
                ground_truth=test_case.spec,
                trace_collector=trace_collector,
            )

            elapsed = (time.time() - start_time) * 1000

            # Use pipeline's comparison if available, otherwise compare ourselves
            if pipeline_result.comparison_result:
                comparison = pipeline_result.comparison_result
            elif pipeline_result.geometry_properties:
                comparison = self.comparator.compare(
                    pipeline_result.geometry_properties,
                    test_case.spec,
                )
            else:
                comparison = None

            success = (
                pipeline_result.success
                and comparison is not None
                and comparison.overall_pass
            )

            return EvaluationResult(
                test_case=test_case,
                pipeline_result=pipeline_result,
                comparison=comparison,
                success=success,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Error running {test_case.test_id}: {e}")
            return EvaluationResult(
                test_case=test_case,
                pipeline_result=None,
                comparison=None,
                success=False,
                error=str(e),
                execution_time_ms=elapsed,
            )

    def run_levels(
        self, levels: list[int], split: str | None = None
    ) -> EvaluationReport:
        """Run evaluation on specific levels.

        Args:
            levels: List of levels to run (1-4).
            split: Optional split filter ("train" or "eval").

        Returns:
            EvaluationReport with results and metrics.
        """
        return self._run_evaluation(levels=levels, split=split)

    def run_all(self, split: str | None = None) -> EvaluationReport:
        """Run evaluation on all levels.

        Args:
            split: Optional split filter ("train" or "eval").

        Returns:
            EvaluationReport with results and metrics.
        """
        return self._run_evaluation(levels=None, split=split)

    def _run_evaluation(
        self,
        levels: list[int] | None,
        split: str | None = None,
    ) -> EvaluationReport:
        """Run evaluation and generate report.

        Args:
            levels: Optional list of levels to run.
            split: Optional split filter ("train" or "eval").

        Returns:
            EvaluationReport with all results.
        """
        start_time = time.time()

        # Discover test cases
        test_cases = self.discover_test_cases(levels=levels, split=split)
        logger.info(f"Discovered {len(test_cases)} test cases")

        # Run each test case
        results: list[EvaluationResult] = []
        for test_case in test_cases:
            logger.info(f"Running {test_case.test_id}: {test_case.name}")
            result = self.run_single(test_case)
            results.append(result)

            status = "PASS" if result.success else "FAIL"
            logger.info(
                f"  {status} ({result.execution_time_ms:.0f}ms, "
                f"confidence={result.pipeline_result.confidence if result.pipeline_result else 0:.2f})"
            )

        # Compute metrics
        metrics = compute_metrics([r.to_dict() for r in results])

        total_duration = (time.time() - start_time) * 1000

        # Get config from pipeline if available
        config = getattr(self.pipeline, "config", PipelineConfig())

        return EvaluationReport(
            results=results,
            metrics=metrics,
            total_duration_ms=total_duration,
            config=config,
            split=split,
        )


# =============================================================================
# Tests for Evaluation Runner
# =============================================================================


class TestEvaluationRunner:
    """Tests for the EvaluationRunner class."""

    @pytest.fixture
    def suite_path(self) -> Path:
        """Get the evaluation suite path."""
        return Path(__file__).parent / "evaluation_suite"

    @pytest.fixture
    def mock_pipeline(self) -> MockIntentToCADPipeline:
        """Create a mock pipeline for testing."""
        return MockIntentToCADPipeline()

    def test_runner_creation(self, mock_pipeline, suite_path):
        """Test runner creation."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        assert runner.pipeline is mock_pipeline
        assert runner.suite_path == suite_path

    def test_discover_test_cases_all(self, mock_pipeline, suite_path):
        """Test discovering all test cases."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases()

        # Should find 45 test cases (12 + 13 + 11 + 9)
        # L1: 12 train + 5 eval = 17
        # L2: 15 train + 5 eval = 20
        # L3: 13 train + 5 eval = 18
        # L4: 10 train + 5 eval = 15
        assert len(test_cases) == 70

    def test_discover_test_cases_level_1(self, mock_pipeline, suite_path):
        """Test discovering only level 1 test cases."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1])

        # L1: 12 train + 5 eval = 17
        assert len(test_cases) == 17
        assert all(tc.level == 1 for tc in test_cases)

    def test_discover_test_cases_multiple_levels(self, mock_pipeline, suite_path):
        """Test discovering multiple levels."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1, 2])

        # L1: 17, L2: 20 = 37 total
        assert len(test_cases) == 37
        assert all(tc.level in [1, 2] for tc in test_cases)

    def test_discover_test_cases_train_split(self, mock_pipeline, suite_path):
        """Test discovering only train split test cases."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(split="train")

        # 50 train samples total
        assert len(test_cases) == 50
        assert all(tc.split == "train" for tc in test_cases)

    def test_discover_test_cases_eval_split(self, mock_pipeline, suite_path):
        """Test discovering only eval split test cases."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(split="eval")

        # 20 eval samples total
        assert len(test_cases) == 20
        assert all(tc.split == "eval" for tc in test_cases)

    def test_discover_test_cases_level_and_split(self, mock_pipeline, suite_path):
        """Test combining level and split filters."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1], split="train")

        # L1 train: 12 samples
        assert len(test_cases) == 12
        assert all(tc.level == 1 for tc in test_cases)
        assert all(tc.split == "train" for tc in test_cases)

    def test_test_case_has_required_fields(self, mock_pipeline, suite_path):
        """Test that test cases have required fields."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1])

        for tc in test_cases:
            assert tc.test_id is not None
            assert tc.name is not None
            assert tc.level == 1
            assert tc.intent != ""
            assert "expected_volume" in tc.spec

    def test_run_single_with_mock(self, mock_pipeline, suite_path):
        """Test running a single test case with mock pipeline."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1])

        if test_cases:
            result = runner.run_single(test_cases[0])

            assert result.test_case == test_cases[0]
            assert result.pipeline_result is not None
            assert result.execution_time_ms > 0

    def test_run_levels(self, mock_pipeline, suite_path):
        """Test running specific levels."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        # Run only train split for L1 (12 samples)
        report = runner.run_levels([1], split="train")

        assert report.metrics.total_tests == 12
        assert len(report.results) == 12
        assert report.total_duration_ms > 0

    def test_evaluation_report_summary(self, mock_pipeline, suite_path):
        """Test report summary generation."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        report = runner.run_levels([1])

        summary = report.summary()

        assert "Intent-to-CAD Pipeline Evaluation Report" in summary
        assert "Total Tests:" in summary
        assert "Success Rate:" in summary
        assert "Level 1:" in summary

    def test_evaluation_result_to_dict(self, mock_pipeline, suite_path):
        """Test EvaluationResult to_dict method."""
        runner = EvaluationRunner(
            pipeline=mock_pipeline,
            suite_path=suite_path,
        )
        test_cases = runner.discover_test_cases(levels=[1])

        if test_cases:
            result = runner.run_single(test_cases[0])
            result_dict = result.to_dict()

            assert "test_id" in result_dict
            assert "level" in result_dict
            assert "success" in result_dict
            assert "skills_tested" in result_dict
            assert "execution_time_ms" in result_dict
            assert "pipeline_confidence" in result_dict


class TestEvalTestCase:
    """Tests for the EvalTestCase dataclass."""

    def test_test_case_creation(self):
        """Test EvalTestCase creation."""
        tc = EvalTestCase(
            path=Path("/test"),
            test_id="L1_01",
            name="Simple Box",
            level=1,
            intent="Create a box",
            spec={"expected_volume": 1000},
            skills_tested=["box"],
            complexity_score=5,
        )

        assert tc.test_id == "L1_01"
        assert tc.level == 1
        assert tc.skills_tested == ["box"]
        assert tc.split == "train"  # Default split

    def test_test_case_with_split(self):
        """Test EvalTestCase with explicit split."""
        tc = EvalTestCase(
            path=Path("/test"),
            test_id="L1_E01",
            name="Eval Cone",
            level=1,
            intent="Create a cone",
            spec={"expected_volume": 500},
            split="eval",
        )

        assert tc.test_id == "L1_E01"
        assert tc.split == "eval"


class TestEvaluationResult:
    """Tests for the EvaluationResult dataclass."""

    def test_evaluation_result_success(self):
        """Test successful evaluation result."""
        tc = EvalTestCase(
            path=Path("/test"),
            test_id="L1_01",
            name="Test",
            level=1,
            intent="Test",
            spec={},
        )

        result = EvaluationResult(
            test_case=tc,
            pipeline_result=None,
            comparison=None,
            success=True,
            execution_time_ms=100.0,
        )

        assert result.test_id == "L1_01"
        assert result.level == 1
        assert result.success is True

    def test_evaluation_result_failure(self):
        """Test failed evaluation result."""
        tc = EvalTestCase(
            path=Path("/test"),
            test_id="L1_02",
            name="Test",
            level=1,
            intent="Test",
            spec={},
        )

        result = EvaluationResult(
            test_case=tc,
            pipeline_result=None,
            comparison=None,
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"


class TestEvaluationReport:
    """Tests for the EvaluationReport dataclass."""

    def test_evaluation_report_creation(self):
        """Test EvaluationReport creation."""
        metrics = EvaluationMetrics(
            total_tests=10,
            passed=8,
            failed=2,
            success_rate=0.8,
            by_level={1: {"total": 10, "passed": 8, "success_rate": 0.8}},
            by_skill={},
        )

        report = EvaluationReport(
            results=[],
            metrics=metrics,
            total_duration_ms=1000.0,
            config=PipelineConfig(),
        )

        assert report.metrics.success_rate == 0.8
        assert report.total_duration_ms == 1000.0
