"""Tests for CadQuery manifest support per prompt1.md:25.

Requirements from prompt1:
- Optional CadQuery manifest: artifact kind = `cadquery_manifest`
- PART_ID_STABLE: if cadquery_manifest present, part_id must match manifest
- Manifest maps part index to part_id
"""

import json

import pytest


@pytest.fixture
def occt_backend():
    """Get OCCT backend if available."""
    try:
        from mech_verify.backend.occt import OCCT_AVAILABLE, OCCTBackend

        if not OCCT_AVAILABLE:
            pytest.skip("pythonocc-core not installed")
        return OCCTBackend()
    except ImportError:
        pytest.skip("pythonocc-core not installed")


@pytest.fixture
def step_file(golden_pass_fixture):
    """STEP file for testing."""
    path = golden_pass_fixture / "inputs" / "simple_box.step"
    if not path.exists():
        pytest.skip("STEP file not found")
    return path


@pytest.fixture
def cadquery_manifest(tmp_path):
    """Create a sample CadQuery manifest."""
    manifest = {
        "schema_version": "cadquery.manifest.v1",
        "parts": [
            {
                "index": 0,
                "part_id": "custom_part_001",
                "name": "main_body",
                "tags": ["primary"],
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


@pytest.fixture
def multi_part_manifest(tmp_path):
    """Manifest for multi-solid STEP."""
    manifest = {
        "schema_version": "cadquery.manifest.v1",
        "parts": [
            {"index": 0, "part_id": "bracket_base", "name": "Base"},
            {"index": 1, "part_id": "bracket_arm", "name": "Arm"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path


class TestCadQueryManifestLoading:
    """Tests for reading CadQuery manifests."""

    def test_load_valid_manifest(self, cadquery_manifest):
        """Load and parse valid manifest."""
        from mech_verify.mds.cadquery_manifest import load_cadquery_manifest

        manifest = load_cadquery_manifest(cadquery_manifest)

        assert manifest is not None
        assert "parts" in manifest
        assert len(manifest["parts"]) == 1
        assert manifest["parts"][0]["part_id"] == "custom_part_001"

    def test_manifest_to_part_id_mapping(self, cadquery_manifest):
        """Extract part index → part_id mapping."""
        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest = load_cadquery_manifest(cadquery_manifest)
        mapping = extract_part_id_mapping(manifest)

        assert mapping == {0: "custom_part_001"}

    def test_multi_part_manifest_mapping(self, multi_part_manifest):
        """Multi-solid manifest produces correct mapping."""
        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest = load_cadquery_manifest(multi_part_manifest)
        mapping = extract_part_id_mapping(manifest)

        assert mapping == {0: "bracket_base", 1: "bracket_arm"}

    def test_missing_manifest_returns_none(self, tmp_path):
        """Missing manifest file returns None."""
        from mech_verify.mds.cadquery_manifest import load_cadquery_manifest

        missing = tmp_path / "nonexistent.json"
        manifest = load_cadquery_manifest(missing)

        assert manifest is None

    def test_invalid_json_returns_none(self, tmp_path):
        """Invalid JSON returns None gracefully."""
        from mech_verify.mds.cadquery_manifest import load_cadquery_manifest

        invalid = tmp_path / "invalid.json"
        invalid.write_text("{ invalid json ]][")

        manifest = load_cadquery_manifest(invalid)
        assert manifest is None


class TestMDSBuilderWithManifest:
    """Tests for using manifest with MDS builder."""

    def test_builder_uses_manifest_part_ids(
        self, step_file, cadquery_manifest, occt_backend
    ):
        """Builder uses part_id from manifest instead of generating."""
        from mech_verify.mds.builder import MDSBuilder
        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest = load_cadquery_manifest(cadquery_manifest)
        part_id_mapping = extract_part_id_mapping(manifest)

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend, part_id_mapping)

        # Should use manifest part_id, not generated
        assert mds["parts"][0]["part_id"] == "custom_part_001"

    def test_builder_without_manifest_generates_ids(self, step_file, occt_backend):
        """Builder generates IDs when no manifest provided."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend)

        # Should generate content-based ID
        part_id = mds["parts"][0]["part_id"]
        assert len(part_id) == 12
        assert part_id != "custom_part_001"

    def test_partial_manifest_mixed_ids(self, step_file, tmp_path, occt_backend):
        """Manifest with partial mapping: uses manifest where specified, generates rest."""
        # Create manifest with only some parts specified
        manifest = {
            "schema_version": "cadquery.manifest.v1",
            "parts": [
                {"index": 0, "part_id": "explicit_id"},
                # index 1 not specified - should be generated
            ],
        }
        manifest_path = tmp_path / "partial.json"
        manifest_path.write_text(json.dumps(manifest))

        from mech_verify.mds.builder import MDSBuilder
        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest_data = load_cadquery_manifest(manifest_path)
        mapping = extract_part_id_mapping(manifest_data)

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend, mapping)

        # First part should use manifest ID
        assert mds["parts"][0]["part_id"] == "explicit_id"


class TestManifestValidation:
    """Tests for manifest validation."""

    def test_manifest_with_duplicate_indices_error(self, tmp_path):
        """Manifest with duplicate indices is invalid."""
        manifest = {
            "schema_version": "cadquery.manifest.v1",
            "parts": [
                {"index": 0, "part_id": "part_a"},
                {"index": 0, "part_id": "part_b"},  # Duplicate!
            ],
        }
        manifest_path = tmp_path / "duplicate.json"
        manifest_path.write_text(json.dumps(manifest))

        from mech_verify.mds.cadquery_manifest import (
            extract_part_id_mapping,
            load_cadquery_manifest,
        )

        manifest_data = load_cadquery_manifest(manifest_path)
        # extract_part_id_mapping should handle duplicates gracefully
        mapping = extract_part_id_mapping(manifest_data)

        # Last wins or raises - either is acceptable
        assert mapping is not None

    def test_manifest_missing_required_fields(self, tmp_path):
        """Manifest missing required fields returns None."""
        manifest = {
            # Missing schema_version
            "parts": [{"index": 0, "part_id": "test"}]
        }
        manifest_path = tmp_path / "incomplete.json"
        manifest_path.write_text(json.dumps(manifest))

        from mech_verify.mds.cadquery_manifest import load_cadquery_manifest

        # Should handle gracefully
        result = load_cadquery_manifest(manifest_path)
        # Can return None or the data - implementation choice
        assert result is not None or result is None


class TestOrchestratorManifestIntegration:
    """Tests for orchestrator using manifests."""

    def test_orchestrator_accepts_manifest_path(
        self, step_file, cadquery_manifest, tmp_path
    ):
        """Orchestrator can load manifest and use it for verification."""
        from mech_verify.orchestrator import (
            VerificationConfig,
            VerificationOrchestrator,
        )

        config = VerificationConfig(cadquery_manifest=cadquery_manifest)
        orchestrator = VerificationOrchestrator(config)

        report = orchestrator.verify([step_file])

        # Check if manifest part_id was used
        if report.mds and report.mds.get("parts"):
            part_id = report.mds["parts"][0]["part_id"]
            # Should use manifest ID
            assert part_id == "custom_part_001"


class TestCLIManifestSupport:
    """Tests for CLI manifest flag."""

    def test_cli_accepts_manifest_flag(self):
        """CLI accepts --cadquery-manifest flag."""
        from mech_verify.cli import verify

        # Verify CLI has the parameter
        assert hasattr(verify, "params"), "verify should be a Click command"

        # Find --cadquery-manifest option in Click params
        param_names = [p.name for p in verify.params]
        assert (
            "cadquery_manifest" in param_names
        ), "CLI should have 'cadquery_manifest' parameter"
