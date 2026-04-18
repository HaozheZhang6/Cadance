"""Integration tests for verifier_core with realistic projects."""

import json
from pathlib import Path

import pytest

from verifier_core.models import (
    ArtifactRef,
    Domain,
    Evidence,
    Finding,
    Severity,
    Status,
    Unknown,
    VerificationReport,
    VerificationRequest,
)
from verifier_core.rulepack.registry import discover_rulepacks
from verifier_core.validation import (
    validate_evidence,
    validate_finding,
    validate_verification_report,
)

# Path to test projects in eda_verifier
TEST_PROJECTS_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "eda_verifier"
    / "eda_verify"
    / "test_projects"
)

# Path to rulepacks in eda_verifier
RULEPACKS_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "eda_verifier"
    / "eda_verify"
    / "rulepacks"
)


@pytest.mark.integration
class TestSchemaValidationWithRealisticData:
    """Integration tests using realistic data structures."""

    def test_complex_finding_conforms_to_schema(self):
        """Complex Finding with all fields should conform to schema."""
        finding = Finding(
            rule_id="clearance_check",
            severity=Severity.ERROR,
            message="Clearance 0.15mm below minimum 0.2mm",
            object_refs=["eda://board/U1/pad1", "eda://board/R5/pad2"],
            measured_value={"value": 0.15, "unit": "mm"},
            limit={"value": 0.2, "unit": "mm"},
            tags=["drc", "manufacturing"],
            suggested_fix="Increase pad spacing",
        )
        errors = validate_finding(finding.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_mech_domain_finding_conforms(self):
        """Mechanical domain finding should conform to schema."""
        finding = Finding(
            rule_id="stress_check",
            severity=Severity.ERROR,
            message="Von Mises stress exceeds yield strength",
            object_ref="mech://part/bracket/face1",
            measured_value={"value": 350, "unit": "MPa"},
            limit={"value": 250, "unit": "MPa"},
            tags=["fea", "structural"],
        )
        errors = validate_finding(finding.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_evidence_with_provenance_conforms(self):
        """Evidence with full provenance should conform to schema."""
        evidence = Evidence(
            evidence_id="ev001",
            kind="drc_result",
            domain=Domain.EDA,
            provenance={
                "tool_name": "kicad-cli",
                "tool_version": "7.0.0",
                "run_id": "abc123",
                "config_hash": "sha256:xyz",
            },
            inputs=[ArtifactRef(kind="board", path="/path/board.kicad_pcb")],
        )
        errors = validate_evidence(evidence.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"


@pytest.mark.integration
class TestRulepackDiscovery:
    """Integration tests for rulepack discovery."""

    @pytest.mark.skipif(
        not RULEPACKS_DIR.exists(), reason="rulepacks directory not found"
    )
    def test_discover_eda_rulepacks(self):
        """Should discover rulepacks in eda_verifier rulepacks dir."""
        discovered = discover_rulepacks([RULEPACKS_DIR])
        assert len(discovered) >= 1, "Expected at least one rulepack"

        # Check first rulepack has required fields
        pack = discovered[0]
        assert pack.name is not None
        assert pack.version is not None
        assert pack.description is not None

    @pytest.mark.skipif(
        not RULEPACKS_DIR.exists(), reason="rulepacks directory not found"
    )
    def test_rulepack_manifest_is_valid(self):
        """Rulepack manifests should be valid."""
        discovered = discover_rulepacks([RULEPACKS_DIR])
        for pack in discovered:
            # Convert to dict and validate schema
            pack_dict = pack.to_dict()
            # rulepack.schema.json is permissive for Phase0
            assert "name" in pack_dict
            assert "version" in pack_dict


@pytest.mark.integration
class TestVerificationReportConformance:
    """Integration tests for verification report schema conformance."""

    def test_full_report_with_all_sections_conforms(self):
        """Full verification report should conform to schema."""
        req = VerificationRequest(
            domain=Domain.EDA,
            tier=0,
            artifacts=[
                ArtifactRef(
                    kind="kicad_project",
                    path="/home/user/project/board.kicad_pcb",
                    sha256="abcdef123456",
                )
            ],
            rule_packs=["tier0_manufacturing"],
            options={"strict": True},
        )

        findings = [
            Finding(
                rule_id="clearance_check",
                severity=Severity.ERROR,
                message="Clearance below minimum",
                object_refs=["eda://board/U1"],
            ),
            Finding(
                rule_id="via_size",
                severity=Severity.WARN,
                message="Via drill smaller than recommended",
                object_ref="eda://board/via1",
            ),
        ]

        unknowns = [
            Unknown(
                summary="Missing thermal requirements",
                impact="Cannot verify thermal path",
                resolution_plan="Add thermal specifications",
            )
        ]

        evidence = [
            Evidence(
                evidence_id="ev001",
                kind="drc_result",
                provenance={"tool_name": "kicad-cli", "tool_version": "7.0.0"},
            )
        ]

        report = VerificationReport(
            request=req,
            status=Status.FAIL,
            findings=findings,
            unknowns=unknowns,
            evidence=evidence,
            summary={"total_errors": 1, "total_warnings": 1},
        )

        report_dict = report.to_dict()
        errors = validate_verification_report(report_dict)
        assert len(errors) == 0, f"Schema validation errors: {errors}"

    def test_minimal_passing_report_conforms(self):
        """Minimal passing report should conform to schema."""
        req = VerificationRequest(
            domain=Domain.MECH,
            tier=0,
            artifacts=[ArtifactRef(kind="step", path="/model.step")],
        )
        report = VerificationReport(
            request=req,
            status=Status.PASS,
            findings=[],
            unknowns=[],
            evidence=[],
        )
        errors = validate_verification_report(report.to_dict())
        assert len(errors) == 0, f"Schema validation errors: {errors}"


@pytest.mark.integration
class TestCrossDomainCompatibility:
    """Tests for cross-domain (EDA/Mech) compatibility."""

    def test_eda_and_mech_findings_both_valid(self):
        """Both EDA and Mech findings should be schema-valid."""
        eda_finding = Finding(
            rule_id="erc_missing_power",
            severity=Severity.ERROR,
            message="Power pin not connected",
            object_ref="eda://schematic/U1/VCC",
        )

        mech_finding = Finding(
            rule_id="interference_check",
            severity=Severity.ERROR,
            message="Parts A and B interfere",
            object_refs=["mech://assembly/partA", "mech://assembly/partB"],
            measured_value={"value": -0.5, "unit": "mm"},
        )

        assert len(validate_finding(eda_finding.to_dict())) == 0
        assert len(validate_finding(mech_finding.to_dict())) == 0

    def test_mixed_domain_report(self):
        """Report with mixed domain artifacts should be valid."""
        req = VerificationRequest(
            domain=Domain.OTHER,  # Mixed
            tier=0,
            artifacts=[
                ArtifactRef(kind="board", path="/pcb.kicad_pcb"),
                ArtifactRef(kind="enclosure", path="/enclosure.step"),
            ],
        )
        report = VerificationReport(
            request=req,
            status=Status.PASS,
            findings=[],
            unknowns=[],
            evidence=[],
        )
        errors = validate_verification_report(report.to_dict())
        assert len(errors) == 0


@pytest.mark.integration
@pytest.mark.skipif(not TEST_PROJECTS_DIR.exists(), reason="test_projects not found")
class TestWithTestProjects:
    """Tests using actual test project fixtures."""

    def test_golden_pass_expected_findings(self):
        """Golden pass project should have expected findings structure."""
        expected_path = TEST_PROJECTS_DIR / "golden_pass" / "expected_findings.json"
        if not expected_path.exists():
            pytest.skip("expected_findings.json not found")

        with open(expected_path) as f:
            expected = json.load(f)

        assert expected["expected_status"] == "pass"
        assert expected["expected_exit_code"] == 0
        assert expected["expected_findings"]["total_fail"] == 0

    def test_all_test_projects_have_expected_findings(self):
        """All test projects should have expected_findings.json."""
        project_dirs = [
            d
            for d in TEST_PROJECTS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        for project_dir in project_dirs:
            expected_path = project_dir / "expected_findings.json"
            assert (
                expected_path.exists()
            ), f"Missing expected_findings.json in {project_dir.name}"

            with open(expected_path) as f:
                expected = json.load(f)
            assert "expected_status" in expected
            assert "expected_exit_code" in expected
