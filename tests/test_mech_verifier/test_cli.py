"""Tests for mech-verify CLI."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from mech_verify.cli import (
    _build_verification_report,
    _detect_artifact_type,
    cli,
)
from verifier_core.models import Finding, Severity, Unknown


class TestDetectArtifactType:
    """Tests for artifact type detection."""

    def test_step_lowercase(self):
        assert _detect_artifact_type(Path("test.step")) == "step"

    def test_stp_extension(self):
        assert _detect_artifact_type(Path("test.stp")) == "step"

    def test_step_uppercase(self):
        assert _detect_artifact_type(Path("test.STEP")) == "step"

    def test_json(self):
        assert _detect_artifact_type(Path("test.json")) == "json"

    def test_unknown(self):
        assert _detect_artifact_type(Path("test.txt")) == "unknown"


class TestBuildVerificationReport:
    """Tests for report building."""

    def test_pass_no_findings(self):
        report = _build_verification_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=[],
        )
        assert report["status"] == "PASS"

    def test_fail_blocker(self):
        findings = [
            Finding(rule_id="test", severity=Severity.BLOCKER, message="blocker")
        ]
        report = _build_verification_report(
            inputs=[Path("test.step")],
            findings=findings,
            unknowns=[],
        )
        assert report["status"] == "FAIL"

    def test_fail_error(self):
        findings = [Finding(rule_id="test", severity=Severity.ERROR, message="error")]
        report = _build_verification_report(
            inputs=[Path("test.step")],
            findings=findings,
            unknowns=[],
        )
        assert report["status"] == "FAIL"

    def test_unknown_blocking(self):
        unknowns = [
            Unknown(
                summary="test",
                impact="test",
                resolution_plan="test",
                blocking=True,
            )
        ]
        report = _build_verification_report(
            inputs=[Path("test.step")],
            findings=[],
            unknowns=unknowns,
        )
        assert report["status"] == "UNKNOWN"

    def test_summary_counts(self):
        findings = [
            Finding(rule_id="test", severity=Severity.BLOCKER, message="blocker"),
            Finding(rule_id="test", severity=Severity.ERROR, message="error"),
            Finding(rule_id="test", severity=Severity.WARN, message="warn"),
        ]
        unknowns = [
            Unknown(summary="u", impact="i", resolution_plan="r", blocking=True)
        ]
        report = _build_verification_report(
            inputs=[Path("test.step")],
            findings=findings,
            unknowns=unknowns,
        )
        assert report["summary"]["blockers"] == 1
        assert report["summary"]["errors"] == 1
        assert report["summary"]["warnings"] == 1
        assert report["summary"]["blocking_unknowns"] == 1


class TestCLI:
    """Tests for CLI commands."""

    def test_no_inputs_error(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["verify", "-o", "./out"])
            assert result.exit_code != 0
            assert "No input files" in result.output

    def test_json_input_valid_mds(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
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
            Path("input.json").write_text(json.dumps(mds))

            result = runner.invoke(cli, ["verify", "input.json", "-o", "./out"])
            assert result.exit_code == 0
            assert Path("out/report.json").exists()
            assert Path("out/mds.json").exists()

    def test_json_input_missing_units(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
                "parts": [],
                "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            }
            Path("input.json").write_text(json.dumps(mds))

            result = runner.invoke(cli, ["verify", "input.json", "-o", "./out"])
            # Missing units causes non-PASS:
            # - With pyshacl: SHACL ERROR → exit 1 (FAIL)
            # - Without pyshacl: blocking Unknown → exit 2 (UNKNOWN)
            assert result.exit_code in (1, 2)

    def test_require_pmi_flag(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
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
            Path("input.json").write_text(json.dumps(mds))

            result = runner.invoke(
                cli, ["verify", "input.json", "-o", "./out", "--require-pmi"]
            )
            # Exit code 1 (FAIL) if SHACL produces ERROR, or 2 (UNKNOWN) if only PMI Unknown
            assert result.exit_code in (1, 2)

    @patch("mech_verify.orchestrator.VerificationOrchestrator._load_backend")
    def test_step_without_backend(self, mock_load):
        mock_load.return_value = (None, "pythonocc not installed")

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.step").touch()

            runner.invoke(cli, ["verify", "test.step", "-o", "./out"])
            # Should fail but not crash
            assert Path("out/report.json").exists()
            report = json.loads(Path("out/report.json").read_text())
            assert len(report["unknowns"]) > 0

    def test_output_creates_directory(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            mds = {
                "schema_version": "mech.mds.v1",
                "units": {"length": "mm"},
                "parts": [],
                "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            }
            Path("input.json").write_text(json.dumps(mds))

            runner.invoke(cli, ["verify", "input.json", "-o", "./nested/deep/out"])
            assert Path("nested/deep/out/report.json").exists()
