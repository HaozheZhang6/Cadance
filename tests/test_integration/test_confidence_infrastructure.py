"""Tests for confidence evaluation infrastructure (no CadQuery dependency)."""

import pytest

from mech_verify.orchestrator import VerificationConfig
from tests.test_integration.fixtures import (
    ConfidenceAnalyzer,
    VerificationResult,
    VerificationRunner,
)
from verifier_core.models import Finding, Severity, Unknown


def test_verification_runner_creation():
    """Test verification runner can be created."""
    config = VerificationConfig()
    runner = VerificationRunner(config)
    assert runner is not None
    assert runner.config is not None


def test_confidence_analyzer_creation():
    """Test confidence analyzer can be created."""
    analyzer = ConfidenceAnalyzer()
    assert analyzer is not None
    assert analyzer.classifier is not None


def test_verification_result_properties():
    """Test VerificationResult properties."""
    result = VerificationResult(
        success=True,
        status="PASS",
        findings=[
            Finding(
                rule_id="test.blocker", severity=Severity.BLOCKER, message="Blocker"
            ),
            Finding(rule_id="test.error", severity=Severity.ERROR, message="Error"),
            Finding(rule_id="test.warn", severity=Severity.WARN, message="Warning"),
        ],
        unknowns=[
            Unknown(
                summary="Unknown1",
                impact="Impact",
                resolution_plan="Plan",
                blocking=True,
            ),
            Unknown(
                summary="Unknown2",
                impact="Impact",
                resolution_plan="Plan",
                blocking=False,
            ),
        ],
    )

    assert result.has_blockers
    assert result.has_errors
    assert result.has_warnings
    assert result.has_blocking_unknowns

    counts = result.count_findings_by_severity()
    assert counts["BLOCKER"] == 1
    assert counts["ERROR"] == 1
    assert counts["WARN"] == 1


def test_confidence_score_basic():
    """Test confidence score computation for basic result."""
    analyzer = ConfidenceAnalyzer()

    result = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1", "parts": [], "features": []},
    )

    score = analyzer.analyze_result(result)
    assert 0.0 <= score.overall_confidence <= 1.0
    assert "geometry_analysis" in score.evidence_types
    assert "geometry" in score.evidence_sources


def test_confidence_score_with_failures():
    """Test confidence score with blockers and unknowns."""
    analyzer = ConfidenceAnalyzer()

    result = VerificationResult(
        success=True,
        status="FAIL",
        findings=[
            Finding(
                rule_id="test.blocker", severity=Severity.BLOCKER, message="Blocker"
            )
        ],
        unknowns=[
            Unknown(
                summary="Unknown",
                impact="Impact",
                resolution_plan="Plan",
                blocking=True,
            )
        ],
        mds={"schema_version": "mech.mds.v1"},
    )

    score = analyzer.analyze_result(result)
    # Should have penalties applied
    assert score.overall_confidence < 1.0
    assert score.has_blockers
    assert score.has_blocking_unknowns


def test_confidence_score_with_evidence():
    """Test confidence score with multiple evidence sources."""
    analyzer = ConfidenceAnalyzer()

    # Create mock report with tool invocations
    class MockReport:
        def __init__(self):
            self.tool_invocations = [
                {"tool_name": "OCCT"},
                {"tool_name": "FreeCAD"},
                {"tool_name": "SFA"},
            ]

    result = VerificationResult(
        success=True,
        status="PASS",
        findings=[
            Finding(rule_id="mech.shacl.test", severity=Severity.INFO, message="SHACL"),
            Finding(rule_id="mech.dfm.hole", severity=Severity.WARN, message="DFM"),
            Finding(
                rule_id="mech.assembly.clearance",
                severity=Severity.INFO,
                message="Assembly",
            ),
        ],
        mds={
            "schema_version": "mech.mds.v1",
            "features": [{"feature_id": "f1"}],
            "pmi": {"has_semantic_pmi": True},
        },
        report=MockReport(),
    )

    score = analyzer.analyze_result(result)
    assert score.overall_confidence > 0.0
    assert len(score.evidence_types) > 1
    assert "external_tool:FreeCAD" in score.evidence_types
    assert "shacl_validation" in score.evidence_types
    assert "dfm_rules" in score.evidence_types
    assert "assembly_checks" in score.evidence_types
    assert "semantic_pmi" in score.evidence_types


def test_confidence_comparison():
    """Test confidence comparison between baseline and enhanced."""
    analyzer = ConfidenceAnalyzer()

    # Baseline (minimal evidence)
    baseline = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1"},
    )

    # Enhanced (more evidence)
    class MockReport:
        def __init__(self):
            self.tool_invocations = [
                {"tool_name": "OCCT"},
                {"tool_name": "FreeCAD"},
            ]

    enhanced = VerificationResult(
        success=True,
        status="PASS",
        findings=[
            Finding(rule_id="mech.shacl.test", severity=Severity.INFO, message="SHACL"),
        ],
        mds={
            "schema_version": "mech.mds.v1",
            "features": [{"feature_id": "f1"}],
        },
        report=MockReport(),
    )

    comparison = analyzer.compare_results(baseline, enhanced)

    assert comparison.baseline.overall_confidence > 0.0
    assert comparison.enhanced.overall_confidence > 0.0
    assert len(comparison.additional_evidence) > 0
    assert "external_tool:FreeCAD" in comparison.additional_evidence
    assert "shacl_validation" in comparison.additional_evidence
    assert comparison.improvement_factors["additional_evidence_sources"] > 0


def test_confidence_comparison_improvement_detection():
    """Test improvement detection in confidence comparison."""
    analyzer = ConfidenceAnalyzer()

    baseline = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1"},
    )

    # Enhanced with higher confidence
    class MockReport:
        def __init__(self):
            self.tool_invocations = [
                {"tool_name": "OCCT"},
                {"tool_name": "FreeCAD"},
            ]

    enhanced = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1", "features": [{"feature_id": "f1"}]},
        report=MockReport(),
    )

    comparison = analyzer.compare_results(baseline, enhanced)

    # Should have additional evidence
    assert len(comparison.additional_evidence) > 0
    assert comparison.improvement_factors["additional_evidence_sources"] > 0


def test_confidence_score_describe():
    """Test confidence score human-readable description."""
    from tests.test_integration.fixtures import ConfidenceScore

    # Very high confidence
    score = ConfidenceScore(overall_confidence=0.95)
    desc = score.describe()
    assert "Very high" in desc or "high" in desc.lower()

    # Low confidence
    score = ConfidenceScore(overall_confidence=0.25)
    desc = score.describe()
    assert "low" in desc.lower()


def test_verification_runner_compare_results():
    """Test verification runner comparison method."""
    runner = VerificationRunner()

    baseline = VerificationResult(
        success=True,
        status="PASS",
        findings=[],
        unknowns=[],
    )

    enhanced = VerificationResult(
        success=True,
        status="PASS",
        findings=[Finding(rule_id="test", severity=Severity.WARN, message="Test")],
        unknowns=[],
    )

    comparison = runner.compare_results(baseline, enhanced)

    assert comparison["baseline_status"] == "PASS"
    assert comparison["enhanced_status"] == "PASS"
    assert comparison["additional_findings"]["WARN"] == 1


def test_confidence_analyzer_with_real_step_file(golden_pass_project):
    """Test confidence analyzer with real STEP file from test suite."""
    # Find a STEP file in test suite
    inputs_dir = golden_pass_project / "inputs"
    if not inputs_dir.exists():
        pytest.skip("Test suite inputs not available")

    step_files = list(inputs_dir.glob("*.step")) + list(inputs_dir.glob("*.stp"))
    if not step_files:
        pytest.skip("No STEP files in test suite")

    step_file = step_files[0]

    # Run baseline verification
    baseline_runner = VerificationRunner(
        VerificationConfig(
            validate_schema=False,
            shacl=False,
            use_external_tools=False,
        )
    )
    baseline = baseline_runner.verify_step(step_file)

    # Run enhanced verification
    enhanced_runner = VerificationRunner(
        VerificationConfig(
            validate_schema=True,
            shacl=True,
            use_external_tools=False,  # Don't require external tools
        )
    )
    enhanced = enhanced_runner.verify_step(step_file)

    # Analyze confidence
    analyzer = ConfidenceAnalyzer()
    comparison = analyzer.compare_results(baseline, enhanced)

    # Verify basic structure
    assert comparison.baseline.overall_confidence >= 0.0
    assert comparison.enhanced.overall_confidence >= 0.0
    assert isinstance(comparison.additional_evidence, list)
    assert isinstance(comparison.improvement_factors, dict)

    print(f"\nConfidence Analysis for {step_file.name}:")
    print(f"  Baseline: {comparison.baseline.overall_confidence:.3f}")
    print(f"  Enhanced: {comparison.enhanced.overall_confidence:.3f}")
    print(f"  Improvement: {comparison.confidence_improvement:.3f}")
    print(f"  Additional evidence: {comparison.additional_evidence}")
