"""Evaluation harness for running CAD test suite."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.cad.comparator import ComparisonResult, GeometricComparator
from src.cad.metrics import compute_metrics
from src.tools.base import BaseTool


@dataclass
class TestCaseResult:
    """Result from running a single test case."""

    test_id: str
    level: int
    success: bool
    attempts: int
    comparison: ComparisonResult | None
    error: str | None
    execution_time_ms: float
    skills_tested: list[str] = field(default_factory=list)


class EvaluationHarness:
    """Runs evaluation suite against a CAD tool.

    Discovers test cases from the evaluation_suite directory,
    executes them against the provided tool, and compares results
    against ground truth specifications.
    """

    def __init__(
        self,
        tool: BaseTool,
        comparator: GeometricComparator | None = None,
        suite_path: Path | None = None,
    ):
        """Initialize evaluation harness.

        Args:
            tool: CAD tool to evaluate.
            comparator: Geometric comparator (default: 1% tolerance).
            suite_path: Path to evaluation_suite directory.
        """
        self.tool = tool
        self.comparator = comparator or GeometricComparator(tolerance=0.01)

        if suite_path is None:
            # Default to evaluation_suite in same directory as this file
            suite_path = Path(__file__).parent.parent / "evaluation_suite"

        self.suite_path = suite_path

    def discover_test_cases(self, split: str | None = None) -> list[Path]:
        """Discover all test case directories.

        Args:
            split: Optional split filter ("train" or "eval"). If None, returns all.

        Returns:
            List of paths to test case directories.
        """
        test_cases = []

        if not self.suite_path.exists():
            return test_cases

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
                if level_dir.is_dir():
                    for test_dir in sorted(level_dir.glob("L*")):
                        if test_dir.is_dir():
                            # Check for required files
                            spec_file = test_dir / "spec.json"
                            if spec_file.exists():
                                test_cases.append(test_dir)

        return test_cases

    def load_spec(self, test_case_path: Path) -> dict[str, Any]:
        """Load test case specification.

        Args:
            test_case_path: Path to test case directory.

        Returns:
            Specification dictionary.
        """
        spec_file = test_case_path / "spec.json"
        if not spec_file.exists():
            return {}

        with open(spec_file) as f:
            return json.load(f)

    def load_intent(self, test_case_path: Path) -> str:
        """Load test case intent description.

        Args:
            test_case_path: Path to test case directory.

        Returns:
            Intent string.
        """
        intent_file = test_case_path / "intent.txt"
        if not intent_file.exists():
            return ""

        return intent_file.read_text().strip()

    def load_ground_truth_code(self, test_case_path: Path) -> str:
        """Load ground truth CadQuery code.

        Args:
            test_case_path: Path to test case directory.

        Returns:
            Ground truth code string.
        """
        code_file = test_case_path / "ground_truth.py"
        if not code_file.exists():
            return ""

        return code_file.read_text()

    def run_single(self, test_case_path: Path) -> TestCaseResult:
        """Run a single test case.

        Args:
            test_case_path: Path to test case directory.

        Returns:
            TestCaseResult with execution results.
        """
        spec = self.load_spec(test_case_path)
        test_id = spec.get("id", test_case_path.name)
        level = spec.get("level", 0)
        skills = spec.get("skills_tested", [])

        start_time = time.time()

        try:
            # Load ground truth code
            code = self.load_ground_truth_code(test_case_path)

            if not code:
                return TestCaseResult(
                    test_id=test_id,
                    level=level,
                    success=False,
                    attempts=0,
                    comparison=None,
                    error="No ground_truth.py found",
                    execution_time_ms=0,
                    skills_tested=skills,
                )

            # Execute code with tool
            result = self.tool.execute({"code": code})

            if not result.success:
                elapsed = (time.time() - start_time) * 1000
                return TestCaseResult(
                    test_id=test_id,
                    level=level,
                    success=False,
                    attempts=1,
                    comparison=None,
                    error=result.error,
                    execution_time_ms=elapsed,
                    skills_tested=skills,
                )

            # Compare against spec
            comparison = self.comparator.compare(result.data, spec)

            elapsed = (time.time() - start_time) * 1000
            return TestCaseResult(
                test_id=test_id,
                level=level,
                success=comparison.overall_pass,
                attempts=1,
                comparison=comparison,
                error=None,
                execution_time_ms=elapsed,
                skills_tested=skills,
            )

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return TestCaseResult(
                test_id=test_id,
                level=level,
                success=False,
                attempts=1,
                comparison=None,
                error=str(e),
                execution_time_ms=elapsed,
                skills_tested=skills,
            )

    def run_level(self, level: int, split: str | None = None) -> list[TestCaseResult]:
        """Run all test cases at a given level.

        Args:
            level: Complexity level (1-4).
            split: Optional split filter ("train" or "eval"). If None, runs all.

        Returns:
            List of TestCaseResults.
        """
        results = []
        level_suffix = (
            "easy"
            if level == 1
            else "medium" if level == 2 else "hard" if level == 3 else "expert"
        )
        level_name = f"level_{level}_{level_suffix}"

        # Determine which split directories to search
        if split == "train":
            split_dirs = ["train"]
        elif split == "eval":
            split_dirs = ["eval"]
        else:
            split_dirs = ["train", "eval"]

        for split_name in split_dirs:
            level_dir = self.suite_path / split_name / level_name
            if not level_dir.exists():
                continue

            for test_dir in sorted(level_dir.glob("L*")):
                if test_dir.is_dir():
                    result = self.run_single(test_dir)
                    results.append(result)

        return results

    def run_suite(self, split: str | None = None) -> dict[int, list[TestCaseResult]]:
        """Run entire evaluation suite.

        Args:
            split: Optional split filter ("train" or "eval"). If None, runs all.

        Returns:
            Dictionary mapping level -> list of results.
        """
        results: dict[int, list[TestCaseResult]] = {}

        for test_case_path in self.discover_test_cases(split=split):
            result = self.run_single(test_case_path)
            level = result.level

            if level not in results:
                results[level] = []
            results[level].append(result)

        return results

    def generate_report(self, results: dict[int, list[TestCaseResult]]) -> str:
        """Generate summary report from results.

        Args:
            results: Dictionary mapping level -> results.

        Returns:
            Formatted report string.
        """
        lines = ["=" * 60, "CAD Evaluation Suite Report", "=" * 60, ""]

        # Flatten results for metrics
        all_results = []
        for level_results in results.values():
            for r in level_results:
                all_results.append(
                    {
                        "test_id": r.test_id,
                        "level": r.level,
                        "success": r.success,
                        "skills_tested": r.skills_tested,
                    }
                )

        metrics = compute_metrics(all_results)

        lines.append(f"Total Tests: {metrics.total_tests}")
        lines.append(f"Passed: {metrics.passed}")
        lines.append(f"Failed: {metrics.failed}")
        lines.append(f"Success Rate: {metrics.success_rate:.1%}")
        lines.append("")

        lines.append("By Level:")
        for level, stats in sorted(metrics.by_level.items()):
            lines.append(
                f"  Level {level}: {stats['passed']}/{stats['total']} "
                f"({stats['success_rate']:.1%})"
            )

        lines.append("")
        lines.append("By Skill:")
        for skill, stats in sorted(metrics.by_skill.items()):
            lines.append(
                f"  {skill}: {stats['passed']}/{stats['total']} "
                f"({stats['success_rate']:.1%})"
            )

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
