"""End-to-end tests for CadQuery workflow integration.

Tests the complete pipeline:
1. CadQuery generates STEP + manifest.json
2. mech-verify loads with --cadquery-manifest flag
3. Part IDs use manifest values (stable across regeneration)
4. Verification passes with proper DFM checks
"""

import json
from pathlib import Path

import pytest

from .conftest import requires_occt

pytestmark = requires_occt


@pytest.fixture
def cadquery_project():
    """CadQuery test project with STEP + manifest."""
    return (
        Path(__file__).parent.parent.parent
        / "src"
        / "mech_verifier"
        / "test_projects"
        / "cadquery_golden_pass"
    )


@pytest.fixture
def cadquery_step(cadquery_project):
    """STEP file from CadQuery test project."""
    step_path = cadquery_project / "inputs" / "bracket.step"
    if not step_path.exists():
        pytest.skip(f"CadQuery STEP not found: {step_path}")
    return step_path


@pytest.fixture
def cadquery_manifest(cadquery_project):
    """Manifest file from CadQuery test project."""
    manifest_path = cadquery_project / "inputs" / "manifest.json"
    if not manifest_path.exists():
        pytest.skip(f"CadQuery manifest not found: {manifest_path}")
    return manifest_path


class TestCadQueryFormatAcceptance:
    """Format acceptance tests for CadQuery-generated artifacts."""

    def test_manifest_format_valid(self, cadquery_manifest):
        """CadQuery manifest has valid schema."""
        from mech_verify.mds.cadquery_manifest import load_cadquery_manifest

        manifest = load_cadquery_manifest(cadquery_manifest)

        assert manifest is not None, "Manifest should load successfully"
        assert manifest["schema_version"] == "cadquery.manifest.v1"
        assert "parts" in manifest
        assert len(manifest["parts"]) >= 1

    def test_manifest_has_stable_part_ids(self, cadquery_manifest):
        """Manifest provides stable semantic part_ids."""
        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest = load_cadquery_manifest(cadquery_manifest)
        mapping = extract_part_id_mapping(manifest)

        assert 0 in mapping, "Manifest should map index 0"
        part_id = mapping[0]
        assert (
            part_id == "bracket_mounting_v1"
        ), f"Expected stable part_id, got {part_id}"
        assert len(part_id) > 8, "Part ID should be semantic, not short hash"

    def test_manifest_has_metadata(self, cadquery_manifest):
        """Manifest includes design parameters and tags."""
        with open(cadquery_manifest) as f:
            manifest = json.load(f)

        part = manifest["parts"][0]
        assert "name" in part
        assert "tags" in part
        assert isinstance(part["tags"], list)
        assert len(part["tags"]) > 0

    def test_step_file_valid(self, cadquery_step):
        """CadQuery-generated STEP file is valid."""
        content = cadquery_step.read_text()

        assert content.startswith("ISO-10303-21")
        assert "HEADER" in content
        assert "DATA" in content
        assert "END-ISO-10303-21" in content

    def test_step_has_geometry(self, cadquery_step):
        """STEP file contains valid geometry entities."""
        content = cadquery_step.read_text()

        # Check for essential STEP entities
        assert (
            "MANIFOLD_SOLID_BREP" in content
            or "ADVANCED_BREP_SHAPE_REPRESENTATION" in content
        )
        assert "CARTESIAN_POINT" in content
        assert "DIRECTION" in content


class TestCadQueryWorkflowIntegration:
    """Integration tests for full CadQuery → mech-verify workflow."""

    def test_orchestrator_uses_manifest_part_id(self, cadquery_step, cadquery_manifest):
        """Orchestrator uses manifest part_id instead of generating hash."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        report = orchestrator.verify([cadquery_step])

        # Check part_id comes from manifest
        assert report.mds is not None
        assert len(report.mds["parts"]) >= 1
        part_id = report.mds["parts"][0]["part_id"]
        assert (
            part_id == "bracket_mounting_v1"
        ), f"Should use manifest part_id, got {part_id}"

    def test_verification_passes_golden_case(self, cadquery_step, cadquery_manifest):
        """CadQuery golden pass case produces PASS status."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        report = orchestrator.verify([cadquery_step])

        # Should pass - no DFM violations
        assert report.status == "PASS", f"Expected PASS, got {report.status}"
        assert (
            len(
                [f for f in report.findings if f.severity.value in ["BLOCKER", "ERROR"]]
            )
            == 0
        )

    def test_mds_has_source_artifacts(self, cadquery_step, cadquery_manifest):
        """MDS includes source_artifacts with STEP path."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        report = orchestrator.verify([cadquery_step])

        assert report.mds is not None
        assert "source_artifacts" in report.mds
        artifacts = report.mds["source_artifacts"]
        assert len(artifacts) >= 1
        assert artifacts[0]["kind"] == "step_part"
        assert "bracket.step" in artifacts[0]["path"]

    def test_part_id_stable_across_runs(self, cadquery_step, cadquery_manifest):
        """Part ID remains stable across multiple verification runs."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        # Run verification twice
        report1 = orchestrator.verify([cadquery_step])
        report2 = orchestrator.verify([cadquery_step])

        part_id1 = report1.mds["parts"][0]["part_id"]
        part_id2 = report2.mds["parts"][0]["part_id"]

        assert part_id1 == part_id2 == "bracket_mounting_v1"

    def test_without_manifest_generates_hash_id(self, cadquery_step):
        """Without manifest, generates content-based hash part_id."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        # No manifest provided
        config = VerificationConfig()
        orchestrator = VerificationOrchestrator(config)

        report = orchestrator.verify([cadquery_step])

        part_id = report.mds["parts"][0]["part_id"]
        # Hash-based IDs are 12 chars, alphanumeric
        assert len(part_id) == 12, f"Expected 12-char hash, got {part_id}"
        assert part_id != "bracket_mounting_v1", "Should NOT use manifest ID"


class TestCadQueryCLIIntegration:
    """CLI tests for CadQuery manifest flag."""

    def test_cli_with_manifest_flag(self, cadquery_step, cadquery_manifest, tmp_path):
        """CLI accepts --cadquery-manifest and uses stable part_id."""
        from click.testing import CliRunner

        from mech_verify.cli import verify

        runner = CliRunner()
        output_dir = tmp_path / "output"

        result = runner.invoke(
            verify,
            [
                str(cadquery_step),
                "--cadquery-manifest",
                str(cadquery_manifest),
                "-o",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert (output_dir / "report.json").exists()
        assert (output_dir / "mds.json").exists()

        # Check MDS has manifest part_id
        with open(output_dir / "mds.json") as f:
            mds = json.load(f)
        assert mds["parts"][0]["part_id"] == "bracket_mounting_v1"

    def test_cli_without_manifest_flag(self, cadquery_step, tmp_path):
        """CLI without --cadquery-manifest generates hash part_id."""
        from click.testing import CliRunner

        from mech_verify.cli import verify

        runner = CliRunner()
        output_dir = tmp_path / "output"

        result = runner.invoke(
            verify,
            [
                str(cadquery_step),
                "-o",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0
        with open(output_dir / "mds.json") as f:
            mds = json.load(f)

        part_id = mds["parts"][0]["part_id"]
        assert len(part_id) == 12  # Hash-based
        assert part_id != "bracket_mounting_v1"


class TestCadQueryDeterminism:
    """Test deterministic output with CadQuery manifests."""

    def test_report_id_deterministic(self, cadquery_step, cadquery_manifest):
        """Report ID is deterministic for same input files."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        report1 = orchestrator.verify([cadquery_step])
        report2 = orchestrator.verify([cadquery_step])

        # Report ID based on input file paths - should be same
        assert report1.report_id == report2.report_id

    def test_mds_stable_json_serialization(
        self, cadquery_step, cadquery_manifest, tmp_path
    ):
        """MDS JSON is stable (byte-for-byte identical across runs)."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        # Generate MDS twice
        mds1_path = tmp_path / "mds1.json"
        mds2_path = tmp_path / "mds2.json"

        report1 = orchestrator.verify([cadquery_step])
        with open(mds1_path, "w") as f:
            json.dump(report1.mds, f, indent=2, sort_keys=True)

        report2 = orchestrator.verify([cadquery_step])
        with open(mds2_path, "w") as f:
            json.dump(report2.mds, f, indent=2, sort_keys=True)

        # Should be byte-identical (excluding timestamp fields)
        mds1_content = mds1_path.read_text()
        mds2_content = mds2_path.read_text()
        assert mds1_content == mds2_content


class TestCadQueryExpectedFindings:
    """Test against expected findings from test project."""

    def test_matches_expected_findings(
        self, cadquery_project, cadquery_step, cadquery_manifest
    ):
        """Verification result matches expected_findings.json."""
        expected_path = cadquery_project / "expected_findings.json"
        if not expected_path.exists():
            pytest.skip("No expected_findings.json")

        with open(expected_path) as f:
            expected = json.load(f)

        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)
        report = orchestrator.verify([cadquery_step])

        # Check status
        expected_status = expected.get("expected_status", "pass").upper()
        assert (
            report.status == expected_status
        ), f"Expected {expected_status}, got {report.status}"

        # Check findings count
        expected_findings = expected.get("expected_findings", [])
        assert len(report.findings) == len(
            expected_findings
        ), f"Expected {len(expected_findings)} findings, got {len(report.findings)}"

        # Check unknowns count
        expected_unknowns = expected.get("expected_unknowns", [])
        assert len(report.unknowns) == len(
            expected_unknowns
        ), f"Expected {len(expected_unknowns)} unknowns, got {len(report.unknowns)}"
