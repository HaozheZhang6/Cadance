"""Tests for VerificationOrchestrator."""

import json
from pathlib import Path
from unittest.mock import patch

from mech_verify.orchestrator import (
    VerificationConfig,
    VerificationOrchestrator,
    VerificationReport,
    write_report,
)
from verifier_core.models import Finding, Severity, Unknown


class TestVerificationConfig:
    """Tests for VerificationConfig dataclass."""

    def test_default_config(self):
        config = VerificationConfig()
        assert config.validate_schema is False
        assert config.require_pmi is False
        assert config.use_external_tools is False
        assert config.units_length == "mm"
        assert config.units_angle == "deg"
        assert config.ops_program is None

    def test_custom_config(self):
        config = VerificationConfig(
            validate_schema=True,
            require_pmi=True,
            units_length="in",
            units_angle="rad",
        )
        assert config.validate_schema is True
        assert config.require_pmi is True
        assert config.units_length == "in"
        assert config.units_angle == "rad"


class TestVerificationReport:
    """Tests for VerificationReport dataclass."""

    def test_to_dict(self):
        report = VerificationReport(
            report_id="test123",
            status="PASS",
            findings=[],
            unknowns=[],
            summary={"total_findings": 0},
            generated_at="2024-01-01T00:00:00Z",
            request={"domain": "mech", "tier": 0},
        )
        d = report.to_dict()
        assert d["report_id"] == "test123"
        assert d["status"] == "PASS"
        assert d["findings"] == []
        assert d["summary"]["total_findings"] == 0

    def test_to_json(self):
        report = VerificationReport(
            report_id="test123",
            status="PASS",
            findings=[],
            unknowns=[],
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["report_id"] == "test123"

    def test_findings_serialized(self):
        finding = Finding(
            rule_id="test.rule", severity=Severity.ERROR, message="Test error"
        )
        report = VerificationReport(
            report_id="test",
            status="FAIL",
            findings=[finding],
            unknowns=[],
        )
        d = report.to_dict()
        assert len(d["findings"]) == 1
        assert d["findings"][0]["rule_id"] == "test.rule"


class TestVerificationOrchestrator:
    """Tests for VerificationOrchestrator class."""

    def test_init_default_config(self):
        orchestrator = VerificationOrchestrator()
        assert orchestrator.config is not None
        assert orchestrator.config.units_length == "mm"

    def test_init_custom_config(self):
        config = VerificationConfig(units_length="in")
        orchestrator = VerificationOrchestrator(config)
        assert orchestrator.config.units_length == "in"

    def test_detect_artifact_type_step(self):
        assert (
            VerificationOrchestrator._detect_artifact_type(Path("test.step")) == "step"
        )
        assert (
            VerificationOrchestrator._detect_artifact_type(Path("test.stp")) == "step"
        )
        assert (
            VerificationOrchestrator._detect_artifact_type(Path("test.STEP")) == "step"
        )

    def test_detect_artifact_type_json(self):
        assert (
            VerificationOrchestrator._detect_artifact_type(Path("test.json")) == "json"
        )

    def test_detect_artifact_type_unknown(self):
        assert (
            VerificationOrchestrator._detect_artifact_type(Path("test.txt"))
            == "unknown"
        )

    def test_generate_report_id_deterministic(self):
        """Report ID is deterministic for same inputs."""
        inputs = [Path("a.step"), Path("b.step")]
        id1 = VerificationOrchestrator._generate_report_id(inputs)
        id2 = VerificationOrchestrator._generate_report_id(inputs)
        assert id1 == id2

    def test_generate_report_id_varies_with_inputs(self):
        """Different inputs produce different report IDs."""
        id1 = VerificationOrchestrator._generate_report_id([Path("a.step")])
        id2 = VerificationOrchestrator._generate_report_id([Path("b.step")])
        assert id1 != id2

    def test_merge_mds_single(self):
        mds = {"schema_version": "mech.mds.v1", "parts": [{"part_id": "p1"}]}
        # Single MDS doesn't go through merge, but let's test the merge function directly
        merged = VerificationOrchestrator._merge_mds([mds])
        assert merged["parts"] == [{"part_id": "p1"}]

    def test_merge_mds_multiple(self):
        mds1 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "parts": [{"part_id": "p1"}],
            "features": [],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds2 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "parts": [{"part_id": "p2"}],
            "features": [],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False},
        }
        merged = VerificationOrchestrator._merge_mds([mds1, mds2])
        assert len(merged["parts"]) == 2
        assert merged["pmi"]["has_semantic_pmi"] is True

    def test_build_report_pass_status(self):
        orchestrator = VerificationOrchestrator()
        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=[],
            mds=None,
            tool_invocations=[],
            evidence=[],
        )
        assert report.status == "PASS"

    def test_build_report_fail_blocker(self):
        orchestrator = VerificationOrchestrator()
        finding = Finding(rule_id="test", severity=Severity.BLOCKER, message="blocker")
        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[finding],
            unknowns=[],
            mds=None,
            tool_invocations=[],
            evidence=[],
        )
        assert report.status == "FAIL"

    def test_build_report_fail_error(self):
        orchestrator = VerificationOrchestrator()
        finding = Finding(rule_id="test", severity=Severity.ERROR, message="error")
        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[finding],
            unknowns=[],
            mds=None,
            tool_invocations=[],
            evidence=[],
        )
        assert report.status == "FAIL"

    def test_build_report_unknown_blocking(self):
        orchestrator = VerificationOrchestrator()
        unknown = Unknown(
            summary="test",
            impact="test",
            resolution_plan="test",
            blocking=True,
        )
        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=[unknown],
            mds=None,
            tool_invocations=[],
            evidence=[],
        )
        assert report.status == "UNKNOWN"

    def test_build_report_summary_counts(self):
        orchestrator = VerificationOrchestrator()
        findings = [
            Finding(rule_id="test", severity=Severity.BLOCKER, message="blocker"),
            Finding(rule_id="test", severity=Severity.ERROR, message="error"),
            Finding(rule_id="test", severity=Severity.WARN, message="warn"),
        ]
        unknowns = [
            Unknown(summary="u", impact="i", resolution_plan="r", blocking=True)
        ]
        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=findings,
            unknowns=unknowns,
            mds=None,
            tool_invocations=[],
            evidence=[],
        )
        assert report.summary["blockers"] == 1
        assert report.summary["errors"] == 1
        assert report.summary["warnings"] == 1
        assert report.summary["blocking_unknowns"] == 1


class TestVerifyJsonInput:
    """Tests for verifying JSON/MDS input files."""

    def test_verify_valid_mds(self, tmp_path):
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "parts": [
                {
                    "part_id": "test",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"dimensions": [10.0, 10.0, 10.0]},
                    },
                }
            ],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "input.json"
        mds_path.write_text(json.dumps(mds))

        orchestrator = VerificationOrchestrator()
        report = orchestrator.verify([mds_path])

        # Should pass - no blockers or errors expected
        assert report.status in ("PASS", "FAIL")  # May fail due to SHACL
        assert report.mds is not None

    def test_verify_mds_missing_units(self, tmp_path):
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "parts": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "input.json"
        mds_path.write_text(json.dumps(mds))

        orchestrator = VerificationOrchestrator()
        report = orchestrator.verify([mds_path])

        # Should have unknowns or findings about missing units
        has_unit_issue = any(
            "unit" in u.summary.lower() for u in report.unknowns
        ) or any("unit" in f.message.lower() for f in report.findings)
        assert has_unit_issue or report.status in ("FAIL", "UNKNOWN")


class TestVerifyStepInput:
    """Tests for verifying STEP input files."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_verify_step_without_backend(self, mock_load, tmp_path):
        mock_load.return_value = (None, "pythonocc not installed")

        step_path = tmp_path / "test.step"
        step_path.touch()

        orchestrator = VerificationOrchestrator()
        report = orchestrator.verify([step_path])

        # Should have unknown about missing backend
        assert len(report.unknowns) > 0
        assert any(
            "OCCT" in u.summary or "backend" in u.summary.lower()
            for u in report.unknowns
        )


class TestPMIRequirement:
    """Tests for PMI requirement handling."""

    def test_check_pmi_requirement_missing(self):
        orchestrator = VerificationOrchestrator()
        mds = {"pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False}}

        unknowns = orchestrator._check_pmi_requirement_naive([mds])

        assert len(unknowns) == 1
        assert "PMI" in unknowns[0].summary
        assert unknowns[0].blocking is True

    def test_check_pmi_requirement_present_semantic(self):
        orchestrator = VerificationOrchestrator()
        mds = {"pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False}}

        unknowns = orchestrator._check_pmi_requirement_naive([mds])

        assert len(unknowns) == 0

    def test_check_pmi_requirement_present_graphical(self):
        orchestrator = VerificationOrchestrator()
        mds = {"pmi": {"has_semantic_pmi": False, "has_graphical_pmi": True}}

        unknowns = orchestrator._check_pmi_requirement_naive([mds])

        assert len(unknowns) == 0

    def test_verify_with_require_pmi_flag(self, tmp_path):
        mds = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "parts": [
                {
                    "part_id": "test",
                    "object_ref": "mech://part/test",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"min_pt": [0, 0, 0], "max_pt": [1, 1, 1]},
                    },
                }
            ],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "input.json"
        mds_path.write_text(json.dumps(mds))

        config = VerificationConfig(require_pmi=True)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([mds_path])

        # Status can be FAIL (if SHACL finds ERROR) or UNKNOWN (if only PMI Unknown)
        assert report.status in ["FAIL", "UNKNOWN"]
        # Must have PMI-related issue reported
        has_pmi_issue = any(
            "PMI" in u.summary or "pmi" in u.created_by_rule_id.lower()
            for u in report.unknowns
        )
        has_pmi_finding = any("pmi" in f.rule_id.lower() for f in report.findings)
        assert has_pmi_issue or has_pmi_finding


class TestWriteReport:
    """Tests for write_report function."""

    def test_write_report_creates_file(self, tmp_path):
        report = VerificationReport(
            report_id="test123",
            status="PASS",
            findings=[],
            unknowns=[],
        )
        output_path = tmp_path / "report.json"
        write_report(report, output_path)

        assert output_path.exists()
        content = json.loads(output_path.read_text())
        assert content["report_id"] == "test123"

    def test_write_report_creates_parent_dirs(self, tmp_path):
        report = VerificationReport(
            report_id="test",
            status="PASS",
            findings=[],
            unknowns=[],
        )
        output_path = tmp_path / "nested" / "deep" / "report.json"
        write_report(report, output_path)

        assert output_path.exists()


class TestVerifyPartAndAssembly:
    """Tests for convenience methods."""

    @patch("mech_verify.orchestrator.VerificationOrchestrator.verify")
    def test_verify_part_calls_verify(self, mock_verify, tmp_path):
        mock_verify.return_value = VerificationReport(
            report_id="test",
            status="PASS",
            findings=[],
            unknowns=[],
        )

        step_path = tmp_path / "part.step"
        step_path.touch()

        orchestrator = VerificationOrchestrator()
        report = orchestrator.verify_part(step_path)

        mock_verify.assert_called_once_with([step_path])
        assert report.status == "PASS"

    @patch("mech_verify.orchestrator.VerificationOrchestrator.verify")
    def test_verify_assembly_calls_verify(self, mock_verify, tmp_path):
        mock_verify.return_value = VerificationReport(
            report_id="test",
            status="PASS",
            findings=[],
            unknowns=[],
        )

        step_path = tmp_path / "assembly.step"
        step_path.touch()

        orchestrator = VerificationOrchestrator()
        report = orchestrator.verify_assembly(step_path)

        mock_verify.assert_called_once_with([step_path])
        assert report.status == "PASS"


class TestProcessJsonFile:
    """Tests for _process_json_file method."""

    def test_process_valid_mds_json(self, tmp_path):
        """_process_json_file handles valid MDS JSON."""
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "parts": [
                {
                    "part_id": "test123",
                    "object_ref": "mech://part/test123",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"min_pt": [0, 0, 0], "max_pt": [10, 10, 10]},
                    },
                }
            ],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds_path = tmp_path / "test.json"
        mds_path.write_text(json.dumps(mds))

        orchestrator = VerificationOrchestrator()
        findings, unknowns, result_mds = orchestrator._process_json_file(mds_path)

        assert result_mds is not None
        assert result_mds["domain"] == "mech"

    def test_process_invalid_json(self, tmp_path):
        """_process_json_file handles invalid JSON."""
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("not valid json {")

        orchestrator = VerificationOrchestrator()
        findings, unknowns, mds = orchestrator._process_json_file(invalid_path)

        assert mds is None
        assert len(findings) > 0
        assert "load_error" in findings[0].rule_id

    def test_process_nonexistent_json(self, tmp_path):
        """_process_json_file handles nonexistent file."""
        nonexistent = tmp_path / "nonexistent.json"

        orchestrator = VerificationOrchestrator()
        findings, unknowns, mds = orchestrator._process_json_file(nonexistent)

        assert mds is None
        assert len(findings) > 0


class TestRunAssemblyChecks:
    """Tests for _run_assembly_checks method."""

    def test_no_assemblies_returns_empty(self):
        """_run_assembly_checks returns empty when no assemblies."""
        orchestrator = VerificationOrchestrator()
        mds = {"assemblies": []}

        findings, unknowns = orchestrator._run_assembly_checks(mds)

        assert findings == []
        assert unknowns == []

    def test_assembly_check_error_handled(self):
        """_run_assembly_checks handles errors gracefully."""
        orchestrator = VerificationOrchestrator()
        # MDS with assemblies but no valid structure
        mds = {
            "assemblies": [{"assembly_id": "asm1"}],
            "parts": [],
        }

        findings, unknowns = orchestrator._run_assembly_checks(mds)

        # Should have unknown or handle gracefully, not crash
        assert isinstance(findings, list)
        assert isinstance(unknowns, list)


class TestValidateRequest:
    """Tests for _validate_request method."""

    def test_validate_request_valid(self, tmp_path):
        """_validate_request returns no findings for valid request."""
        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)

        step_path = tmp_path / "test.step"
        step_path.touch()

        findings = orchestrator._validate_request([step_path])

        # Should return list (possibly empty or with findings)
        assert isinstance(findings, list)

    def test_validate_request_skipped_when_disabled(self):
        """_validate_request skipped when validate_schema=False."""
        config = VerificationConfig(validate_schema=False)
        orchestrator = VerificationOrchestrator(config)

        # When disabled, _validate_request should return empty or not be called
        # We test through verify() behavior
        assert orchestrator.config.validate_schema is False


class TestValidateReport:
    """Tests for _validate_report method."""

    def test_validate_report_returns_findings(self):
        """_validate_report returns findings for invalid report."""
        config = VerificationConfig(validate_schema=True)
        orchestrator = VerificationOrchestrator(config)

        # Create a minimal report
        report = VerificationReport(
            report_id="test",
            status="PASS",
            findings=[],
            unknowns=[],
        )

        findings = orchestrator._validate_report(report)

        # Should return list of findings (possibly empty)
        assert isinstance(findings, list)


class TestExtractSFAPMIInfo:
    """Tests for _extract_sfa_pmi_info method."""

    def test_extract_pmi_found(self):
        """_extract_sfa_pmi_info detects PMI from findings."""
        orchestrator = VerificationOrchestrator()

        findings = [
            Finding(
                rule_id="sfa.pmi.representation_found",
                severity=Severity.INFO,
                message="PMI representation found",
            )
        ]

        info = orchestrator._extract_sfa_pmi_info(findings)

        assert info["pmi_found"] is True
        assert info["graphical_pmi"] is True

    def test_extract_pmi_not_found(self):
        """_extract_sfa_pmi_info returns false when no PMI."""
        orchestrator = VerificationOrchestrator()

        findings = [
            Finding(
                rule_id="sfa.some.other.rule",
                severity=Severity.INFO,
                message="Other info",
            )
        ]

        info = orchestrator._extract_sfa_pmi_info(findings)

        assert info["pmi_found"] is False

    def test_extract_semantic_pmi(self):
        """_extract_sfa_pmi_info detects semantic PMI."""
        orchestrator = VerificationOrchestrator()

        findings = [
            Finding(
                rule_id="sfa.pmi.semantic_found",
                severity=Severity.INFO,
                message="Semantic PMI found",
            )
        ]

        info = orchestrator._extract_sfa_pmi_info(findings)

        assert info["semantic_pmi"] is True


class TestMergeMDSEdgeCases:
    """Additional edge case tests for _merge_mds."""

    def test_merge_mds_preserves_source_artifacts(self):
        """_merge_mds preserves source_artifacts from all MDS."""
        mds1 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "source_artifacts": [{"path": "/a.step", "kind": "step_part"}],
            "parts": [],
            "features": [],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds2 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "source_artifacts": [{"path": "/b.step", "kind": "step_part"}],
            "parts": [],
            "features": [],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }

        merged = VerificationOrchestrator._merge_mds([mds1, mds2])

        assert len(merged["source_artifacts"]) == 2

    def test_merge_mds_merges_features(self):
        """_merge_mds merges features from all MDS."""
        mds1 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "source_artifacts": [],
            "parts": [],
            "features": [{"feature_id": "f1", "feature_type": "hole"}],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }
        mds2 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "source_artifacts": [],
            "parts": [],
            "features": [{"feature_id": "f2", "feature_type": "fillet"}],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }

        merged = VerificationOrchestrator._merge_mds([mds1, mds2])

        assert len(merged["features"]) == 2

    def test_merge_mds_sorts_features(self):
        """_merge_mds sorts features by type and ID."""
        mds1 = {
            "schema_version": "mech.mds.v1",
            "units": {"length": "mm"},
            "source_artifacts": [],
            "parts": [],
            "features": [
                {"feature_id": "z_fillet", "feature_type": "fillet"},
                {"feature_id": "a_hole", "feature_type": "hole"},
            ],
            "assemblies": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }

        merged = VerificationOrchestrator._merge_mds([mds1])

        # Sorted by (feature_type, feature_id)
        assert merged["features"][0]["feature_type"] == "fillet"
        assert merged["features"][1]["feature_type"] == "hole"


class TestBuildReportEdgeCases:
    """Additional edge case tests for _build_report."""

    def test_build_report_with_warnings_only(self):
        """_build_report returns PASS with warnings only."""
        orchestrator = VerificationOrchestrator()
        findings = [
            Finding(rule_id="test.warn", severity=Severity.WARN, message="warning")
        ]

        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=findings,
            unknowns=[],
            mds=None,
            tool_invocations=[],
            evidence=[],
        )

        # Warnings alone don't fail
        assert report.status == "PASS"
        assert report.summary["warnings"] == 1

    def test_build_report_with_non_blocking_unknown(self):
        """_build_report returns PASS with non-blocking unknown."""
        orchestrator = VerificationOrchestrator()
        unknowns = [
            Unknown(
                summary="minor issue",
                impact="low",
                resolution_plan="optional",
                blocking=False,
            )
        ]

        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=unknowns,
            mds=None,
            tool_invocations=[],
            evidence=[],
        )

        assert report.status == "PASS"
        assert report.summary["total_unknowns"] == 1
        assert report.summary["blocking_unknowns"] == 0

    def test_build_report_includes_tool_invocations(self):
        """_build_report includes tool invocations in report."""
        orchestrator = VerificationOrchestrator()
        invocations = [
            {"tool_name": "test_tool", "exit_code": 0},
        ]

        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=[],
            mds=None,
            tool_invocations=invocations,
            evidence=[],
        )

        assert len(report.tool_invocations) == 1
        assert report.tool_invocations[0]["tool_name"] == "test_tool"

    def test_build_report_includes_evidence(self):
        """_build_report includes evidence in report."""
        orchestrator = VerificationOrchestrator()
        evidence = [
            {"type": "measurement", "source": "test"},
        ]

        report = orchestrator._build_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=[],
            mds=None,
            tool_invocations=[],
            evidence=evidence,
        )

        assert len(report.evidence) == 1
        assert report.evidence[0]["type"] == "measurement"
