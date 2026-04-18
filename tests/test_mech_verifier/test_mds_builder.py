"""Tests for MDS (Mechanical Design Snapshot) builder.

These tests verify the MDS builder correctly extracts geometry
from STEP files and produces valid MDS JSON.
"""

from pathlib import Path

import pytest

from .conftest import load_mds


class TestMDSStructure:
    """Tests for MDS JSON structure."""

    def test_mds_has_required_fields(self, golden_pass_fixture: Path):
        """MDS has schema_version, domain, parts fields."""
        mds = load_mds(golden_pass_fixture)
        assert "schema_version" in mds
        assert "domain" in mds
        assert mds["domain"] == "mech"

    def test_mds_parts_have_required_fields(self, golden_pass_fixture: Path):
        """Each part has part_id, name, object_ref."""
        mds = load_mds(golden_pass_fixture)
        assert "parts" in mds
        for part in mds["parts"]:
            assert "part_id" in part
            assert "name" in part
            assert "object_ref" in part

    def test_part_id_is_deterministic(self, golden_pass_fixture: Path):
        """Same input produces same part_id on repeated loads."""
        mds1 = load_mds(golden_pass_fixture)
        mds2 = load_mds(golden_pass_fixture)
        assert mds1["parts"][0]["part_id"] == mds2["parts"][0]["part_id"]


class TestMDSObjectRef:
    """Tests for object reference formatting."""

    def test_object_ref_format_part(self, golden_pass_fixture: Path):
        """Part object_ref matches mech://part/<id> pattern."""
        mds = load_mds(golden_pass_fixture)
        part = mds["parts"][0]
        assert "object_ref" in part
        assert part["object_ref"].startswith("mech://part/")

    def test_feature_object_ref_format(self, golden_pass_fixture: Path):
        """Feature object_refs are well-formed."""
        mds = load_mds(golden_pass_fixture)
        # New schema: features are top-level
        features = mds.get("features", [])
        for feature in features:
            assert "object_ref" in feature
            assert "mech://" in feature["object_ref"]


class TestMDSGeometry:
    """Tests for geometry extraction."""

    def test_bounding_box_present(self, golden_pass_fixture: Path):
        """Parts have bounding box in mass_props."""
        mds = load_mds(golden_pass_fixture)
        part = mds["parts"][0]
        # New schema: bbox is in mass_props
        assert "mass_props" in part
        assert "bbox" in part["mass_props"]
        bbox = part["mass_props"]["bbox"]
        assert "min_pt" in bbox
        assert "max_pt" in bbox
        assert len(bbox["min_pt"]) == 3
        assert len(bbox["max_pt"]) == 3

    def test_volume_positive(self, golden_pass_fixture: Path):
        """Valid parts have positive volume."""
        mds = load_mds(golden_pass_fixture)
        part = mds["parts"][0]
        # New schema: volume in mass_props
        assert "mass_props" in part
        assert part["mass_props"]["volume"] > 0

    def test_mass_props_present(self, golden_pass_fixture: Path):
        """Parts have mass_props with volume."""
        mds = load_mds(golden_pass_fixture)
        part = mds["parts"][0]
        assert "mass_props" in part
        mass_props = part["mass_props"]
        assert "volume" in mass_props


class TestMDSFeatures:
    """Tests for DFM feature extraction."""

    def test_holes_extracted(self, golden_pass_fixture: Path):
        """Holes are extracted with diameter and depth."""
        mds = load_mds(golden_pass_fixture)
        # New schema: features are top-level
        features = mds.get("features", [])
        holes = [f for f in features if f.get("feature_type") == "hole"]
        if holes:
            for hole in holes:
                assert "diameter" in hole
                assert "depth" in hole
                assert hole["diameter"] > 0

    def test_fillets_extracted(self, small_fillet_fixture: Path):
        """Fillets are extracted with radius."""
        mds = load_mds(small_fillet_fixture)
        # New schema: features are top-level
        features = mds.get("features", [])
        fillets = [f for f in features if f.get("feature_type") == "fillet"]
        if fillets:
            for fillet in fillets:
                assert "radius" in fillet
                assert fillet["radius"] > 0


class TestBuildFromSTEP:
    """Tests for building MDS from STEP files."""

    @pytest.fixture
    def step_file(self, golden_pass_fixture: Path) -> Path:
        """Get path to STEP file for testing."""
        return golden_pass_fixture / "inputs" / "simple_box.step"

    @pytest.fixture
    def occt_backend(self):
        """Get OCCT backend if available."""
        try:
            from mech_verify.backend.occt import OCCT_AVAILABLE, OCCTBackend

            if not OCCT_AVAILABLE:
                pytest.skip("pythonocc-core not installed")
            return OCCTBackend()
        except ImportError:
            pytest.skip("pythonocc-core not installed")

    def test_build_from_step_returns_valid_mds(self, step_file: Path, occt_backend):
        """MDS from STEP has required fields."""
        if not step_file.exists():
            pytest.skip(f"STEP file not found: {step_file}")

        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend)

        # Check required fields
        assert "schema_version" in mds
        assert "domain" in mds
        assert mds["domain"] == "mech"
        assert "parts" in mds
        assert len(mds["parts"]) >= 1

        # Check part fields
        part = mds["parts"][0]
        assert "part_id" in part
        assert "object_ref" in part
        assert "mass_props" in part
        assert part["mass_props"]["volume"] > 0

    def test_part_id_is_deterministic_from_step(self, step_file: Path, occt_backend):
        """Same STEP produces same part_id."""
        if not step_file.exists():
            pytest.skip(f"STEP file not found: {step_file}")

        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds1 = builder.build_from_step(step_file, occt_backend)
        mds2 = builder.build_from_step(step_file, occt_backend)

        assert mds1["parts"][0]["part_id"] == mds2["parts"][0]["part_id"]

    def test_bounding_box_from_step(self, step_file: Path, occt_backend):
        """STEP extraction includes bounding box."""
        if not step_file.exists():
            pytest.skip(f"STEP file not found: {step_file}")

        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend)

        part = mds["parts"][0]
        assert "mass_props" in part
        assert "bbox" in part["mass_props"]

        bbox = part["mass_props"]["bbox"]
        assert "min_pt" in bbox
        assert "max_pt" in bbox

        # Box should have positive dimensions
        min_pt = bbox["min_pt"]
        max_pt = bbox["max_pt"]
        for i in range(3):
            assert max_pt[i] >= min_pt[i]


class TestMDSBuilderMergeOpsProgram:
    """Tests for merge_ops_program method."""

    @pytest.fixture
    def base_mds(self):
        """Create a base MDS dict for testing."""
        return {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [{"path": "/test/part.step", "kind": "step_part"}],
            "parts": [
                {
                    "part_id": "abc123",
                    "name": "test_part",
                    "object_ref": "mech://part/abc123",
                    "mass_props": {
                        "volume": 1000.0,
                        "surface_area": 600.0,
                        "center_of_mass": [5.0, 5.0, 5.0],
                        "bbox": {
                            "min_pt": [0.0, 0.0, 0.0],
                            "max_pt": [10.0, 10.0, 10.0],
                        },
                    },
                }
            ],
            "assemblies": [],
            "features": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }

    @pytest.fixture
    def ops_program_file(self, tmp_path):
        """Create a temporary ops program file."""
        import json

        ops_program = {
            "schema_version": "1.0",
            "name": "test_part",
            "operations": [
                {
                    "primitive": "hole_simple",
                    "parameters": [
                        {"name": "diameter", "value": 5.0},
                        {"name": "depth", "value": 10.0},
                    ],
                },
                {
                    "primitive": "fillet",
                    "parameters": [
                        {"name": "radius", "value": 2.0},
                    ],
                },
                {
                    "primitive": "shell",
                    "parameters": [
                        {"name": "thickness", "value": 1.5},
                    ],
                },
            ],
        }

        ops_path = tmp_path / "ops_program.json"
        ops_path.write_text(json.dumps(ops_program))
        return ops_path

    def test_merge_ops_program_adds_artifact(self, base_mds, ops_program_file):
        """merge_ops_program adds ops program to source_artifacts."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        assert len(merged["source_artifacts"]) == 2
        ops_artifact = merged["source_artifacts"][1]
        assert ops_artifact["kind"] == "ops_program"

    def test_merge_ops_program_extracts_holes(self, base_mds, ops_program_file):
        """merge_ops_program extracts hole features from operations."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        holes = [f for f in merged["features"] if f["feature_type"] == "hole"]
        assert len(holes) == 1
        assert holes[0]["diameter"] == 5.0
        assert holes[0]["depth"] == 10.0
        assert holes[0]["from_ops_program"] is True

    def test_merge_ops_program_extracts_fillets(self, base_mds, ops_program_file):
        """merge_ops_program extracts fillet features from operations."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        fillets = [f for f in merged["features"] if f["feature_type"] == "fillet"]
        assert len(fillets) == 1
        assert fillets[0]["radius"] == 2.0
        assert fillets[0]["from_ops_program"] is True

    def test_merge_ops_program_extracts_shells(self, base_mds, ops_program_file):
        """merge_ops_program extracts shell features from operations."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        shells = [f for f in merged["features"] if f["feature_type"] == "shell"]
        assert len(shells) == 1
        assert shells[0]["min_wall_thickness"] == 1.5
        assert shells[0]["from_ops_program"] is True

    def test_merge_ops_program_creates_operation_graph(
        self, base_mds, ops_program_file
    ):
        """merge_ops_program creates operation_graph from ops program."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        assert "operation_graph" in merged
        assert merged["operation_graph"]["schema_version"] == "1.0"
        assert len(merged["operation_graph"]["ops"]) == 3

    def test_merge_ops_program_computes_ld_ratio(self, base_mds, ops_program_file):
        """merge_ops_program computes L/D ratio for holes."""
        from mech_verify.mds.builder import MDSBuilder

        builder = MDSBuilder()
        merged = builder.merge_ops_program(base_mds, ops_program_file)

        holes = [f for f in merged["features"] if f["feature_type"] == "hole"]
        assert len(holes) == 1
        # L/D ratio = depth/diameter = 10.0/5.0 = 2.0
        assert "ld_ratio" in holes[0]
        assert holes[0]["ld_ratio"] == 2.0


class TestMDSBuilderExtractFeatures:
    """Tests for feature extraction helper methods."""

    @pytest.fixture
    def builder(self):
        """Create MDS builder instance."""
        from mech_verify.mds.builder import MDSBuilder

        return MDSBuilder()

    @pytest.fixture
    def base_mds(self):
        """Create a base MDS dict for testing."""
        return {
            "parts": [{"part_id": "test123"}],
        }

    def test_extract_hole_feature_with_diameter(self, builder, base_mds):
        """_extract_hole_feature extracts hole with diameter."""
        op = {
            "primitive": "hole_simple",
            "parameters": [
                {"name": "diameter", "value": 8.0},
            ],
        }
        feature = builder._extract_hole_feature(base_mds, 0, op)

        assert feature is not None
        assert feature["feature_type"] == "hole"
        assert feature["diameter"] == 8.0
        assert feature["from_ops_program"] is True

    def test_extract_hole_feature_with_depth(self, builder, base_mds):
        """_extract_hole_feature extracts depth and computes L/D."""
        op = {
            "primitive": "hole_through",
            "parameters": [
                {"name": "diameter", "value": 4.0},
                {"name": "depth", "value": 12.0},
            ],
        }
        feature = builder._extract_hole_feature(base_mds, 0, op)

        assert feature is not None
        assert feature["depth"] == 12.0
        assert feature["ld_ratio"] == 3.0  # 12/4

    def test_extract_hole_feature_no_diameter(self, builder, base_mds):
        """_extract_hole_feature returns None without diameter."""
        op = {
            "primitive": "hole_simple",
            "parameters": [
                {"name": "depth", "value": 10.0},
            ],
        }
        feature = builder._extract_hole_feature(base_mds, 0, op)
        assert feature is None

    def test_extract_fillet_feature(self, builder, base_mds):
        """_extract_fillet_feature extracts fillet with radius."""
        op = {
            "primitive": "fillet",
            "parameters": [
                {"name": "radius", "value": 3.5},
            ],
        }
        feature = builder._extract_fillet_feature(base_mds, 1, op)

        assert feature is not None
        assert feature["feature_type"] == "fillet"
        assert feature["radius"] == 3.5
        assert feature["feature_id"] == "fillet_1"

    def test_extract_fillet_feature_no_radius(self, builder, base_mds):
        """_extract_fillet_feature returns None without radius."""
        op = {
            "primitive": "fillet",
            "parameters": [],
        }
        feature = builder._extract_fillet_feature(base_mds, 0, op)
        assert feature is None

    def test_extract_shell_feature(self, builder, base_mds):
        """_extract_shell_feature extracts shell with thickness."""
        op = {
            "primitive": "shell",
            "parameters": [
                {"name": "thickness", "value": 2.0},
            ],
        }
        feature = builder._extract_shell_feature(base_mds, 2, op)

        assert feature is not None
        assert feature["feature_type"] == "shell"
        assert feature["min_wall_thickness"] == 2.0
        assert feature["feature_id"] == "shell_2"

    def test_extract_shell_feature_no_thickness(self, builder, base_mds):
        """_extract_shell_feature returns None without thickness."""
        op = {
            "primitive": "shell",
            "parameters": [],
        }
        feature = builder._extract_shell_feature(base_mds, 0, op)
        assert feature is None


class TestMDSBuilderSourceSpecIds:
    """Tests for source_spec_ids propagation through merge_ops_program."""

    @pytest.fixture
    def base_mds(self):
        return {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "units": {"length": "mm", "angle": "deg"},
            "source_artifacts": [{"path": "/test/part.step", "kind": "step_part"}],
            "parts": [
                {
                    "part_id": "abc123",
                    "name": "test_part",
                    "object_ref": "mech://part/abc123",
                    "mass_props": {
                        "volume": 1000.0,
                        "surface_area": 600.0,
                        "center_of_mass": [5.0, 5.0, 5.0],
                        "bbox": {"min_pt": [0, 0, 0], "max_pt": [10, 10, 10]},
                    },
                }
            ],
            "assemblies": [],
            "features": [],
            "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
        }

    def test_hole_gets_source_spec_ids(self, base_mds, tmp_path):
        import json

        from mech_verify.mds.builder import MDSBuilder

        ops = {
            "schema_version": "1.0",
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [{"name": "diameter", "value": 6.0}],
                    "source_spec_ids": ["S1.1.1"],
                }
            ],
        }
        p = tmp_path / "ops.json"
        p.write_text(json.dumps(ops))
        merged = MDSBuilder().merge_ops_program(base_mds, p)
        holes = [f for f in merged["features"] if f["feature_type"] == "hole"]
        assert holes[0]["source_spec_ids"] == ["S1.1.1"]

    def test_fillet_gets_source_spec_ids(self, base_mds, tmp_path):
        import json

        from mech_verify.mds.builder import MDSBuilder

        ops = {
            "schema_version": "1.0",
            "operations": [
                {
                    "primitive": "fillet",
                    "parameters": [{"name": "radius", "value": 2.0}],
                    "source_spec_ids": ["S2.1"],
                }
            ],
        }
        p = tmp_path / "ops.json"
        p.write_text(json.dumps(ops))
        merged = MDSBuilder().merge_ops_program(base_mds, p)
        fillets = [f for f in merged["features"] if f["feature_type"] == "fillet"]
        assert fillets[0]["source_spec_ids"] == ["S2.1"]

    def test_shell_gets_source_spec_ids(self, base_mds, tmp_path):
        import json

        from mech_verify.mds.builder import MDSBuilder

        ops = {
            "schema_version": "1.0",
            "operations": [
                {
                    "primitive": "shell",
                    "parameters": [{"name": "thickness", "value": 1.5}],
                    "source_spec_ids": ["S3.1"],
                }
            ],
        }
        p = tmp_path / "ops.json"
        p.write_text(json.dumps(ops))
        merged = MDSBuilder().merge_ops_program(base_mds, p)
        shells = [f for f in merged["features"] if f["feature_type"] == "shell"]
        assert shells[0]["source_spec_ids"] == ["S3.1"]

    def test_no_source_spec_ids_omitted(self, base_mds, tmp_path):
        import json

        from mech_verify.mds.builder import MDSBuilder

        ops = {
            "schema_version": "1.0",
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [{"name": "diameter", "value": 6.0}],
                }
            ],
        }
        p = tmp_path / "ops.json"
        p.write_text(json.dumps(ops))
        merged = MDSBuilder().merge_ops_program(base_mds, p)
        holes = [f for f in merged["features"] if f["feature_type"] == "hole"]
        assert holes[0].get("source_spec_ids", []) == []


class TestMDSBuilderHelpers:
    """Tests for MDS builder helper functions."""

    def test_compute_file_sha256(self, tmp_path):
        """_compute_file_sha256 produces deterministic hash."""
        from mech_verify.mds.builder import _compute_file_sha256

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = _compute_file_sha256(test_file)
        hash2 = _compute_file_sha256(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    def test_generate_part_id_deterministic(self):
        """_generate_part_id is deterministic for same inputs."""
        from mech_verify.mds.builder import _generate_part_id

        id1 = _generate_part_id("abc123", 0)
        id2 = _generate_part_id("abc123", 0)
        id3 = _generate_part_id("abc123", 1)

        assert id1 == id2
        assert id1 != id3
        assert len(id1) == 12  # First 12 chars of SHA256

    def test_build_object_ref(self):
        """_build_object_ref formats correct URI."""
        from mech_verify.mds.builder import _build_object_ref

        ref = _build_object_ref("abc123")
        assert ref == "mech://part/abc123"
