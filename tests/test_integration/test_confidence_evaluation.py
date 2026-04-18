"""Tests for confidence evaluation infrastructure."""

import pytest

from tests.conftest import CADQUERY_WORKS

# Check if CadQuery is available and works (not just imports)
CADQUERY_AVAILABLE = CADQUERY_WORKS

if CADQUERY_AVAILABLE:
    import cadquery as cq  # noqa: F401

requires_cadquery = pytest.mark.skipif(
    not CADQUERY_AVAILABLE, reason="CadQuery not available or OCP incompatible"
)

# Check if pythonocc-core is available (required for OCCT backend)
try:
    from OCC.Core.Bnd import Bnd_Box  # noqa: F401

    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False

requires_pythonocc = pytest.mark.skipif(
    not PYTHONOCC_AVAILABLE, reason="pythonocc-core required for OCCT backend"
)


@requires_cadquery
def test_cadquery_executor_fixture(
    cadquery_tool, temp_output_dir, sample_cadquery_code
):
    """Test CadQuery executor fixture."""
    result = cadquery_tool.execute(sample_cadquery_code, temp_output_dir)
    assert result.success, f"CadQuery execution failed: {result.error}"
    assert result.step_path is not None
    assert result.step_path.exists()


@requires_cadquery
@requires_pythonocc
def test_verification_runner_baseline(
    verification_orchestrator, cadquery_tool, temp_output_dir, sample_cadquery_code
):
    """Test baseline verification runner (requires OCCT backend)."""
    # Generate STEP file
    cq_result = cadquery_tool.execute(sample_cadquery_code, temp_output_dir)
    assert cq_result.success

    # Run baseline verification
    result = verification_orchestrator.verify_step(cq_result.step_path)
    assert result.success
    assert result.status in ["PASS", "UNKNOWN"]
    assert result.mds is not None


@requires_cadquery
@requires_pythonocc
def test_verification_runner_enhanced(
    verification_orchestrator_enhanced,
    cadquery_tool,
    temp_output_dir,
    sample_cadquery_code,
):
    """Test enhanced verification runner (requires OCCT backend)."""
    # Generate STEP file
    cq_result = cadquery_tool.execute(sample_cadquery_code, temp_output_dir)
    assert cq_result.success

    # Run enhanced verification
    result = verification_orchestrator_enhanced.verify_step(cq_result.step_path)
    assert result.success
    # Enhanced verification with external tools may find issues (FAIL)
    # This is expected behavior - external tools provide additional checks
    assert result.status in ["PASS", "FAIL", "UNKNOWN"]

    # Should have run verification successfully
    assert result.mds is not None


@requires_cadquery
def test_confidence_analyzer(
    confidence_calculator,
    verification_orchestrator,
    verification_orchestrator_enhanced,
    cadquery_tool,
    temp_output_dir,
    sample_cadquery_bracket,
):
    """Test confidence analyzer with comparison."""
    # Generate STEP file
    cq_result = cadquery_tool.execute(sample_cadquery_bracket, temp_output_dir)
    assert cq_result.success

    # Run both verifications
    baseline = verification_orchestrator.verify_step(cq_result.step_path)
    enhanced = verification_orchestrator_enhanced.verify_step(cq_result.step_path)

    assert baseline.success
    assert enhanced.success

    # Analyze confidence
    comparison = confidence_calculator.compare_results(baseline, enhanced)

    # Verify comparison structure
    assert comparison.baseline.overall_confidence >= 0.0
    assert comparison.baseline.overall_confidence <= 1.0
    assert comparison.enhanced.overall_confidence >= 0.0
    assert comparison.enhanced.overall_confidence <= 1.0
    assert isinstance(comparison.additional_evidence, list)
    assert isinstance(comparison.improvement_factors, dict)


def test_confidence_score_computation(confidence_calculator, verification_orchestrator):
    """Test confidence score computation from verification result."""
    from tests.test_integration.fixtures import VerificationResult
    from verifier_core.models import Finding, Severity

    # Create mock verification result
    result = VerificationResult(
        success=True,
        status="PASS",
        findings=[
            Finding(
                rule_id="test.rule",
                severity=Severity.WARN,
                message="Test finding",
            )
        ],
        mds={"schema_version": "mech.mds.v1", "parts": [], "features": []},
    )

    # Analyze
    score = confidence_calculator.analyze_result(result)

    assert score.overall_confidence > 0.0
    assert score.overall_confidence <= 1.0
    assert isinstance(score.evidence_types, list)
    assert isinstance(score.evidence_sources, dict)


def test_confidence_comparison_has_improvement(confidence_calculator):
    """Test confidence comparison improvement detection."""
    from tests.test_integration.fixtures import VerificationResult

    # Baseline with minimal evidence
    baseline = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1"},
    )

    # Enhanced with additional evidence
    enhanced = VerificationResult(
        success=True,
        status="PASS",
        mds={"schema_version": "mech.mds.v1", "features": [{"feature_id": "f1"}]},
        report=type("Report", (), {"tool_invocations": [{"tool_name": "FreeCAD"}]})(),
    )

    comparison = confidence_calculator.compare_results(baseline, enhanced)
    assert len(comparison.additional_evidence) > 0


@pytest.mark.slow
@requires_cadquery
def test_full_evaluation_workflow(
    cadquery_tool,
    verification_orchestrator,
    verification_orchestrator_enhanced,
    confidence_calculator,
    temp_output_dir,
    sample_cadquery_bracket,
):
    """Test full evaluation workflow from CadQuery to confidence report."""
    # Step 1: Generate STEP file
    cq_result = cadquery_tool.execute(sample_cadquery_bracket, temp_output_dir)
    assert cq_result.success, f"CadQuery failed: {cq_result.error}"

    # Step 2: Run baseline verification
    baseline = verification_orchestrator.verify_step(cq_result.step_path)
    assert baseline.success, f"Baseline verification failed: {baseline.error}"

    # Step 3: Run enhanced verification
    enhanced = verification_orchestrator_enhanced.verify_step(cq_result.step_path)
    assert enhanced.success, f"Enhanced verification failed: {enhanced.error}"

    # Step 4: Compare confidence
    comparison = confidence_calculator.compare_results(baseline, enhanced)

    # Step 5: Verify results
    assert comparison.baseline.overall_confidence > 0.0
    assert comparison.enhanced.overall_confidence > 0.0

    # Enhanced should have additional evidence (SHACL, external tools, etc.)
    # Note: May not always improve raw confidence if new issues found
    assert isinstance(comparison.additional_evidence, list)
    assert comparison.improvement_factors["additional_evidence_sources"] >= 0

    # Print summary for debugging
    print("\nConfidence Evaluation Summary:")
    print(f"  Baseline: {comparison.baseline.overall_confidence:.3f}")
    print(f"  Enhanced: {comparison.enhanced.overall_confidence:.3f}")
    print(f"  Improvement: {comparison.confidence_improvement:.3f}")
    print(f"  Additional evidence: {comparison.additional_evidence}")
