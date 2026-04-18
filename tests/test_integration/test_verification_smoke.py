"""
Smoke test for verification integration.

Tests basic integration without full CadQuery execution.
Uses pre-generated STEP files from test_projects.
"""

from pathlib import Path

import pytest

from src.mech_verifier.mech_verify.orchestrator import VerificationConfig
from tests.test_integration.fixtures import (
    ConfidenceAnalyzer,
    VerificationRunner,
)


@pytest.fixture
def test_step_file() -> Path:
    """Path to existing test STEP file."""
    test_projects = (
        Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
    )

    # Try to find any STEP file
    step_files = list(test_projects.glob("**/*.step")) + list(
        test_projects.glob("**/*.STEP")
    )

    if not step_files:
        pytest.skip("No test STEP files found")

    return step_files[0]


def test_baseline_verification(test_step_file: Path):
    """Test baseline verification runs successfully."""
    config = VerificationConfig(
        validate_schema=False,
        shacl=False,
        require_pmi=False,
        use_external_tools=False,
    )

    runner = VerificationRunner(config)
    result = runner.verify_step(test_step_file)

    assert result.success, f"Verification failed: {result.error}"
    assert result.status in ["PASS", "FAIL", "UNKNOWN"]
    print(f"\nBaseline verification status: {result.status}")
    print(f"Findings: {len(result.findings)}")
    print(f"Unknowns: {len(result.unknowns)}")


def test_enhanced_verification(test_step_file: Path):
    """Test enhanced verification with full checks."""
    config = VerificationConfig(
        validate_schema=True,
        shacl=True,
        require_pmi=False,
        use_external_tools=True,
    )

    runner = VerificationRunner(config)
    result = runner.verify_step(test_step_file, enable_shacl=True)

    assert result.success, f"Verification failed: {result.error}"
    assert result.status in ["PASS", "FAIL", "UNKNOWN"]
    print(f"\nEnhanced verification status: {result.status}")
    print(f"Findings: {len(result.findings)}")
    print(f"Unknowns: {len(result.unknowns)}")


def test_confidence_analysis(test_step_file: Path):
    """Test confidence analysis on verification results."""
    # Baseline
    baseline_config = VerificationConfig(
        validate_schema=False, shacl=False, require_pmi=False, use_external_tools=False
    )
    baseline_runner = VerificationRunner(baseline_config)
    baseline_result = baseline_runner.verify_step(test_step_file)

    # Enhanced
    enhanced_config = VerificationConfig(
        validate_schema=True, shacl=True, require_pmi=False, use_external_tools=True
    )
    enhanced_runner = VerificationRunner(enhanced_config)
    enhanced_result = enhanced_runner.verify_step(
        test_step_file, enable_shacl=True, use_external_tools=True
    )

    # Analyze
    analyzer = ConfidenceAnalyzer()
    baseline_score = analyzer.analyze_result(baseline_result)
    enhanced_score = analyzer.analyze_result(enhanced_result)
    comparison = analyzer.compare_results(baseline_result, enhanced_result)

    print(f"\nBaseline confidence: {baseline_score.overall_confidence:.3f}")
    print(f"  Evidence types: {baseline_score.evidence_types}")
    print(f"  Verified features: {baseline_score.verified_features}")

    print(f"\nEnhanced confidence: {enhanced_score.overall_confidence:.3f}")
    print(f"  Evidence types: {enhanced_score.evidence_types}")
    print(f"  Verified features: {enhanced_score.verified_features}")

    print(f"\nConfidence improvement: {comparison.confidence_improvement:+.3f}")
    print(f"  Additional evidence: {comparison.additional_evidence}")
    print(f"  Improvement factors: {comparison.improvement_factors}")

    assert baseline_score.overall_confidence >= 0.0
    assert enhanced_score.overall_confidence >= 0.0


def test_evaluation_suite_loading():
    """Test that evaluation suite can be loaded."""

    suite_dir = (
        Path(__file__).parent.parent
        / "test_tools"
        / "test_cadquery"
        / "evaluation_suite"
    )

    if not suite_dir.exists():
        pytest.skip("Evaluation suite not found")

    # Count test cases
    test_cases = []
    for level_dir in sorted(suite_dir.glob("level_*")):
        for case_dir in sorted(level_dir.iterdir()):
            if not case_dir.is_dir():
                continue

            intent_path = case_dir / "intent.txt"
            spec_path = case_dir / "spec.json"
            ground_truth_path = case_dir / "ground_truth.py"

            if all(p.exists() for p in [intent_path, spec_path, ground_truth_path]):
                test_cases.append(case_dir.name)

    print(f"\nFound {len(test_cases)} evaluation test cases:")
    by_level = {}
    for tc in test_cases:
        level = tc.split("_")[0]
        by_level.setdefault(level, []).append(tc)

    for level in sorted(by_level.keys()):
        print(f"  {level}: {len(by_level[level])} cases")

    assert len(test_cases) == 20, f"Expected 20 test cases, found {len(test_cases)}"
