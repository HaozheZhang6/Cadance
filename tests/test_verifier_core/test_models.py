"""Tests for verifier_core.models module and snapshot test for VerificationReport."""

import pytest

from verifier_core.models import (
    ArtifactRef,
    Domain,
    Evidence,
    Finding,
    Severity,
    Status,
    ToolInvocation,
    Unknown,
    VerificationReport,
    VerificationRequest,
)
from verifier_core.validation import validate_unknown, validate_verification_report


class TestArtifactRef:
    """Tests for ArtifactRef model."""

    def test_create_with_path(self):
        """Create ArtifactRef with path."""
        ref = ArtifactRef(kind="board", path="/path/to/board.kicad_pcb")
        assert ref.kind == "board"
        assert ref.path == "/path/to/board.kicad_pcb"
        assert ref.artifact_id is not None

    def test_create_with_uri(self):
        """Create ArtifactRef with URI."""
        ref = ArtifactRef(kind="step", uri="file:///models/part.step")
        assert ref.uri == "file:///models/part.step"

    def test_requires_uri_or_path(self):
        """ArtifactRef requires either uri or path."""
        with pytest.raises(ValueError, match="uri.*path"):
            ArtifactRef(kind="test")

    def test_to_dict(self):
        """ArtifactRef serializes to dict."""
        ref = ArtifactRef(
            kind="cds",
            path="/path/design.json",
            sha256="abc123",
            role="input",
        )
        d = ref.to_dict()
        assert d["kind"] == "cds"
        assert d["path"] == "/path/design.json"
        assert d["sha256"] == "abc123"
        assert d["role"] == "input"


class TestFinding:
    """Tests for Finding model."""

    def test_create_basic_finding(self):
        """Create basic finding."""
        f = Finding(
            rule_id="test_rule",
            severity=Severity.ERROR,
            message="Test error",
        )
        assert f.rule_id == "test_rule"
        assert f.severity == Severity.ERROR
        assert f.finding_id is not None

    def test_severity_from_string(self):
        """Severity can be set from string."""
        f = Finding(
            rule_id="test",
            severity="ERROR",  # type: ignore
            message="Test",
        )
        assert f.severity == Severity.ERROR

    def test_to_dict(self):
        """Finding serializes to dict."""
        f = Finding(
            rule_id="clearance_check",
            severity=Severity.WARN,
            message="Clearance below minimum",
            object_ref="eda://board/U1",
            measured_value={"value": 0.15, "unit": "mm"},
            limit={"value": 0.2, "unit": "mm"},
            tags=["drc"],
        )
        d = f.to_dict()
        assert d["rule_id"] == "clearance_check"
        assert d["severity"] == "WARN"
        assert d["object_ref"] == "eda://board/U1"
        assert d["measured_value"]["value"] == 0.15


class TestUnknown:
    """Tests for Unknown model."""

    def test_create_unknown(self):
        """Create unknown marker."""
        u = Unknown(
            summary="Missing footprint",
            impact="Cannot verify clearances",
            resolution_plan="Add footprint to library",
        )
        assert u.summary == "Missing footprint"
        assert u.unknown_id is not None

    def test_to_dict(self):
        """Unknown serializes to dict."""
        u = Unknown(
            summary="Test",
            impact="Impact",
            resolution_plan="Plan",
            blocking=True,
            escalation_tier=2,
        )
        d = u.to_dict()
        assert d["blocking"] is True
        assert d["escalation_tier"] == 2


class TestFindingSourceSpecIds:
    """Tests for Finding.source_spec_ids traceability field."""

    def test_default_empty(self):
        f = Finding(rule_id="r1", severity=Severity.ERROR, message="m")
        assert f.source_spec_ids == []

    def test_set_source_spec_ids(self):
        f = Finding(
            rule_id="r1",
            severity=Severity.ERROR,
            message="m",
            source_spec_ids=["S1.1.1", "S2.1"],
        )
        assert f.source_spec_ids == ["S1.1.1", "S2.1"]

    def test_to_dict_omits_when_empty(self):
        f = Finding(rule_id="r1", severity=Severity.ERROR, message="m")
        d = f.to_dict()
        assert "source_spec_ids" not in d

    def test_to_dict_includes_when_set(self):
        f = Finding(
            rule_id="r1",
            severity=Severity.ERROR,
            message="m",
            source_spec_ids=["S1.1.1"],
        )
        d = f.to_dict()
        assert d["source_spec_ids"] == ["S1.1.1"]


class TestUnknownSourceSpecIds:
    """Tests for Unknown.source_spec_ids traceability field."""

    def test_default_empty(self):
        u = Unknown(summary="s", impact="i", resolution_plan="p")
        assert u.source_spec_ids == []

    def test_set_source_spec_ids(self):
        u = Unknown(
            summary="s",
            impact="i",
            resolution_plan="p",
            source_spec_ids=["S3.2"],
        )
        assert u.source_spec_ids == ["S3.2"]

    def test_to_dict_omits_when_empty(self):
        u = Unknown(summary="s", impact="i", resolution_plan="p")
        d = u.to_dict()
        assert "source_spec_ids" not in d

    def test_to_dict_includes_when_set(self):
        u = Unknown(
            summary="s",
            impact="i",
            resolution_plan="p",
            source_spec_ids=["S1.1.1", "S2.1"],
        )
        d = u.to_dict()
        assert d["source_spec_ids"] == ["S1.1.1", "S2.1"]


class TestEvidence:
    """Tests for Evidence model."""

    def test_create_evidence(self):
        """Create evidence record."""
        e = Evidence(
            evidence_id="ev123",
            kind="drc_result",
            provenance={"tool_name": "kicad", "tool_version": "7.0.0"},
            domain=Domain.EDA,
        )
        assert e.evidence_id == "ev123"
        assert e.domain == Domain.EDA

    def test_to_dict(self):
        """Evidence serializes to dict."""
        e = Evidence(
            evidence_id="ev1",
            kind="test",
            provenance={"tool_name": "test"},
            domain="eda",  # type: ignore
        )
        d = e.to_dict()
        assert d["domain"] == "eda"


class TestToolInvocation:
    """Tests for ToolInvocation model."""

    def test_create_invocation(self):
        """Create tool invocation."""
        ti = ToolInvocation(
            tool_name="kicad-cli",
            command="kicad-cli pcb drc",
            exit_code=0,
        )
        assert ti.tool_name == "kicad-cli"
        assert ti.invocation_id is not None


class TestVerificationRequest:
    """Tests for VerificationRequest model."""

    def test_create_request(self):
        """Create verification request."""
        req = VerificationRequest(
            domain=Domain.EDA,
            tier=0,
            artifacts=[ArtifactRef(kind="board", path="/path/board.kicad_pcb")],
        )
        assert req.domain == Domain.EDA
        assert req.tier == 0
        assert req.request_id is not None

    def test_to_dict(self):
        """Request serializes to dict."""
        req = VerificationRequest(
            domain="mech",  # type: ignore
            tier=1,
            artifacts=[ArtifactRef(kind="step", path="/path/part.step")],
        )
        d = req.to_dict()
        assert d["domain"] == "mech"
        assert d["tier"] == 1


class TestVerificationReport:
    """Tests for VerificationReport model."""

    def test_create_report(self):
        """Create verification report."""
        req = VerificationRequest(
            domain=Domain.EDA,
            tier=0,
            artifacts=[ArtifactRef(kind="board", path="/path/board.kicad_pcb")],
        )
        report = VerificationReport(
            request=req,
            status=Status.PASS,
            findings=[],
            unknowns=[],
            evidence=[],
        )
        assert report.status == Status.PASS
        assert report.report_id is not None

    def test_to_dict(self):
        """Report serializes to dict."""
        req = VerificationRequest(
            domain=Domain.MECH,
            tier=1,
            artifacts=[ArtifactRef(kind="step", path="/path/part.step")],
        )
        report = VerificationReport(
            request=req,
            status=Status.FAIL,
            findings=[
                Finding(
                    rule_id="stress_check",
                    severity=Severity.ERROR,
                    message="Stress exceeds limit",
                )
            ],
            unknowns=[],
            evidence=[
                Evidence(
                    evidence_id="ev1",
                    kind="fea_result",
                    provenance={"tool_name": "ansys"},
                )
            ],
        )
        d = report.to_dict()
        assert d["status"] == "FAIL"
        assert len(d["findings"]) == 1
        assert len(d["evidence"]) == 1


class TestVerificationReportSchemaConformance:
    """Snapshot test: verify VerificationReport conforms to schema."""

    def test_report_conforms_to_schema(self):
        """Generated VerificationReport should conform to schema."""
        # Build a complete report
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
                message="Clearance 0.15mm below minimum 0.2mm",
                object_refs=["eda://board/U1/pad1", "eda://board/R5/pad2"],
                measured_value={"value": 0.15, "unit": "mm"},
                limit={"value": 0.2, "unit": "mm"},
                tags=["drc", "manufacturing"],
            ),
            Finding(
                rule_id="silkscreen_overlap",
                severity=Severity.WARN,
                message="Silkscreen overlaps pad",
                object_ref="eda://board/C3",
                suggested_fix="Move silkscreen text",
            ),
        ]

        unknowns = [
            Unknown(
                summary="Missing thermal via specification",
                impact="Cannot verify thermal path",
                resolution_plan="Add thermal via requirements to design rules",
                blocking=False,
                created_by_rule_id="thermal_check",
            )
        ]

        evidence = [
            Evidence(
                evidence_id="ev001",
                kind="drc_run",
                domain=Domain.EDA,
                provenance={
                    "tool_name": "kicad-cli",
                    "tool_version": "7.0.0",
                    "run_id": "abc123",
                },
                inputs=[ArtifactRef(kind="board", path="/path/board.kicad_pcb")],
            )
        ]

        tool_invocations = [
            ToolInvocation(
                tool_name="kicad-cli",
                tool_version="7.0.0",
                command="kicad-cli pcb drc board.kicad_pcb",
                exit_code=1,
                started_at="2024-01-15T10:00:00Z",
                ended_at="2024-01-15T10:00:05Z",
            )
        ]

        report = VerificationReport(
            request=req,
            status=Status.FAIL,
            findings=findings,
            unknowns=unknowns,
            evidence=evidence,
            tool_invocations=tool_invocations,
            summary={
                "total_findings": 2,
                "errors": 1,
                "warnings": 1,
                "unknowns": 1,
            },
        )

        # Serialize to dict
        report_dict = report.to_dict()

        # Validate against schema
        errors = validate_verification_report(report_dict)

        # This is the snapshot test - the report should conform to schema
        assert len(errors) == 0, f"Schema validation errors: {errors}"

        # Additional assertions on structure
        assert report_dict["status"] == "FAIL"
        assert report_dict["request"]["domain"] == "eda"
        assert report_dict["request"]["tier"] == 0
        assert len(report_dict["findings"]) == 2
        assert len(report_dict["unknowns"]) == 1
        assert len(report_dict["evidence"]) == 1

    def test_minimal_report_conforms_to_schema(self):
        """Minimal valid report should conform to schema."""
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


class TestAdapterConversionSchemaConformance:
    """Tests for EDA adapter conversion schema conformance."""

    def test_core_finding_to_eda_dict_structure(self):
        """Core Finding converted to EDA dict should have expected structure."""
        from verifier_core.adapters.eda import core_finding_to_eda

        core_finding = Finding(
            rule_id="clearance_check",
            severity=Severity.ERROR,
            message="Clearance below minimum",
            object_refs=["eda://board/U1/pad1", "eda://board/R5/pad2"],
            measured_value={"value": 0.15, "unit": "mm"},
            suggested_fix="Increase spacing",
            tags=["drc"],
        )

        eda_dict = core_finding_to_eda(core_finding)

        # Check required fields
        assert "id" in eda_dict
        assert eda_dict["rule_id"] == "clearance_check"
        assert eda_dict["severity"] == "error"
        assert eda_dict["message"] == "Clearance below minimum"
        assert "object_refs" in eda_dict
        assert eda_dict["remediation"] == "Increase spacing"

    def test_core_finding_severity_mapping(self):
        """Core severity should map correctly to EDA severity."""
        from verifier_core.adapters.eda import core_finding_to_eda

        # Test ERROR -> error
        f_error = Finding(rule_id="r1", severity=Severity.ERROR, message="Error")
        assert core_finding_to_eda(f_error)["severity"] == "error"

        # Test WARN -> warning
        f_warn = Finding(rule_id="r2", severity=Severity.WARN, message="Warn")
        assert core_finding_to_eda(f_warn)["severity"] == "warning"

        # Test INFO -> info
        f_info = Finding(rule_id="r3", severity=Severity.INFO, message="Info")
        assert core_finding_to_eda(f_info)["severity"] == "info"

    def test_create_unknown_from_finding(self):
        """Unknown created from Finding should be schema-valid."""
        from verifier_core.adapters.eda import create_unknown_from_finding

        finding = Finding(
            rule_id="thermal_check",
            severity=Severity.UNKNOWN,
            message="Cannot determine thermal path without specifications",
            object_ref="eda://board/U5",
        )

        unknown = create_unknown_from_finding(
            finding,
            impact="Thermal verification incomplete",
            resolution_plan="Add thermal requirements to spec",
        )

        errors = validate_unknown(unknown.to_dict())
        assert len(errors) == 0, f"Unknown schema errors: {errors}"

        assert unknown.summary == finding.message
        assert unknown.object_ref == "eda://board/U5"
        assert unknown.created_by_rule_id == "thermal_check"

    def test_core_evidence_to_eda_dict_structure(self):
        """Core Evidence converted to EDA dict should have expected structure."""
        from verifier_core.adapters.eda import core_evidence_to_eda

        core_evidence = Evidence(
            evidence_id="ev123",
            kind="drc_result",
            domain=Domain.EDA,
            provenance={
                "tool_name": "kicad-cli",
                "tool_version": "7.0.0",
                "timestamp": "2024-01-15T10:00:00Z",
                "input_files": ["/path/board.kicad_pcb"],
                "input_hashes": {"/path/board.kicad_pcb": "sha256:abc"},
                "settings": {"units": "mm"},
            },
        )

        eda_dict = core_evidence_to_eda(core_evidence)

        # Check structure
        assert eda_dict["verification_id"] == "ev123"
        assert "provenance" in eda_dict
        assert eda_dict["provenance"]["tool_id"] == "kicad-cli"
        assert eda_dict["provenance"]["tool_version"] == "7.0.0"

    def test_uri_to_object_ref_dict_parsing(self):
        """URI strings should parse correctly to ObjectRef dict."""
        from verifier_core.adapters.eda import _uri_to_object_ref_dict

        # Standard EDA URI
        result = _uri_to_object_ref_dict("eda://board/U1")
        assert result["object_type"] == "board"
        assert result["object_id"] == "U1"

        # EDA URI with refdes
        result = _uri_to_object_ref_dict("eda://component/R5/pad1")
        assert result["object_type"] == "component"
        assert result["object_id"] == "R5"
        assert result["refdes"] == "pad1"

        # Non-EDA URI fallback
        result = _uri_to_object_ref_dict("mech://part/bracket")
        assert result["object_type"] == "unknown"
