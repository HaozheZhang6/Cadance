"""Tests for content-based part_id generation per prompt1.md:46.

Requirements from prompt1:
- part_id must be based on artifact SHA256 + index (not file path)
- Same content in different locations should produce same part_id
- Moving/renaming file should not change part_id
"""

import shutil
from pathlib import Path

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
def step_file_copy(tmp_path, golden_pass_fixture):
    """Create a copy of a STEP file in a different location."""
    original = golden_pass_fixture / "inputs" / "simple_box.step"
    if not original.exists():
        pytest.skip("STEP file not found")

    # Copy to different path
    copy_path = tmp_path / "different_location" / "renamed_file.step"
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(original, copy_path)

    return original, copy_path


class TestContentBasedPartId:
    """Tests for content-based part_id generation."""

    def test_same_content_same_part_id(self, step_file_copy, occt_backend):
        """Same STEP content produces same part_id regardless of path."""
        from mech_verify.mds.builder import MDSBuilder

        original, copy = step_file_copy

        builder = MDSBuilder()
        mds_original = builder.build_from_step(original, occt_backend)
        mds_copy = builder.build_from_step(copy, occt_backend)

        # Same content should produce same part_id
        original_id = mds_original["parts"][0]["part_id"]
        copy_id = mds_copy["parts"][0]["part_id"]

        assert original_id == copy_id, (
            f"part_id should be content-based (SHA256), not path-based. "
            f"Original: {original_id}, Copy: {copy_id}"
        )

    def test_part_id_independent_of_filename(self, step_file_copy, occt_backend):
        """part_id does not depend on filename."""
        from mech_verify.mds.builder import MDSBuilder

        original, renamed = step_file_copy

        builder = MDSBuilder()
        mds_original = builder.build_from_step(original, occt_backend)
        mds_renamed = builder.build_from_step(renamed, occt_backend)

        # Files have different names but same content
        assert original.name != renamed.name
        assert original != renamed

        # Should still have same part_id
        assert mds_original["parts"][0]["part_id"] == mds_renamed["parts"][0]["part_id"]

    def test_part_id_independent_of_directory(self, step_file_copy, occt_backend):
        """part_id does not depend on directory path."""
        from mech_verify.mds.builder import MDSBuilder

        original, copy = step_file_copy

        builder = MDSBuilder()
        mds_original = builder.build_from_step(original, occt_backend)
        mds_copy = builder.build_from_step(copy, occt_backend)

        # Files in different directories
        assert original.parent != copy.parent

        # Should have same part_id
        assert mds_original["parts"][0]["part_id"] == mds_copy["parts"][0]["part_id"]

    def test_part_id_includes_solid_index(self, occt_backend):
        """Multi-solid STEP: part_id includes index for uniqueness."""
        from mech_verify.mds.builder import MDSBuilder

        # Use assembly STEP which has multiple solids

        test_projects = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mech_verifier"
            / "test_projects"
        )
        assembly_step = test_projects / "step_asm_clean" / "inputs" / "assembly.step"

        if not assembly_step.exists():
            pytest.skip("Assembly STEP fixture not found")

        builder = MDSBuilder()
        mds = builder.build_from_step(assembly_step, occt_backend)

        # Should have multiple parts with different IDs
        assert len(mds["parts"]) >= 2
        part_ids = [p["part_id"] for p in mds["parts"]]

        # All part IDs should be unique (index distinguishes them)
        assert len(part_ids) == len(set(part_ids)), "part_ids should be unique"

        # All should be 12-char SHA256 prefixes
        for part_id in part_ids:
            assert len(part_id) == 12
            assert all(c in "0123456789abcdef" for c in part_id)


class TestPartIdDeterminism:
    """Tests for part_id determinism."""

    def test_repeated_loads_same_id(self, golden_pass_fixture, occt_backend):
        """Loading same file multiple times produces same part_id."""
        from mech_verify.mds.builder import MDSBuilder

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        builder = MDSBuilder()
        mds1 = builder.build_from_step(step_file, occt_backend)
        mds2 = builder.build_from_step(step_file, occt_backend)
        mds3 = builder.build_from_step(step_file, occt_backend)

        id1 = mds1["parts"][0]["part_id"]
        id2 = mds2["parts"][0]["part_id"]
        id3 = mds3["parts"][0]["part_id"]

        assert id1 == id2 == id3

    def test_part_id_is_sha256_prefix(self, golden_pass_fixture, occt_backend):
        """part_id is a SHA256 prefix (12 chars)."""
        from mech_verify.mds.builder import MDSBuilder

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend)

        part_id = mds["parts"][0]["part_id"]

        # SHA256 prefix: 12 hex characters
        assert len(part_id) == 12
        assert all(c in "0123456789abcdef" for c in part_id)


class TestGeneratePartIdFunction:
    """Tests for _generate_part_id function directly."""

    def test_generate_part_id_from_content(self):
        """_generate_part_id should use content hash, not path."""
        from mech_verify.mds.builder import _generate_part_id

        # Same content hash should produce same part_id
        content_hash = "abc123def456"
        part_id_1 = _generate_part_id(content_hash, 0)
        part_id_2 = _generate_part_id(content_hash, 0)

        assert part_id_1 == part_id_2

        # Different indices should produce different part_ids
        part_id_idx0 = _generate_part_id(content_hash, 0)
        part_id_idx1 = _generate_part_id(content_hash, 1)

        assert part_id_idx0 != part_id_idx1

        # Different content should produce different part_ids
        different_hash = "xyz789"
        part_id_different = _generate_part_id(different_hash, 0)

        assert part_id_different != part_id_1

        # All should be 12-char SHA256 prefixes
        for pid in [part_id_1, part_id_idx0, part_id_idx1, part_id_different]:
            assert len(pid) == 12
            assert all(c in "0123456789abcdef" for c in pid)


class TestBackwardCompatibility:
    """Tests to ensure changes don't break existing functionality."""

    def test_existing_fixtures_still_work(self, golden_pass_fixture, occt_backend):
        """Existing test fixtures continue to work after change."""
        from mech_verify.mds.builder import MDSBuilder

        step_file = golden_pass_fixture / "inputs" / "simple_box.step"
        if not step_file.exists():
            pytest.skip("STEP file not found")

        builder = MDSBuilder()
        mds = builder.build_from_step(step_file, occt_backend)

        # Should still produce valid MDS
        assert "parts" in mds
        assert len(mds["parts"]) > 0
        assert "part_id" in mds["parts"][0]
        assert "object_ref" in mds["parts"][0]
