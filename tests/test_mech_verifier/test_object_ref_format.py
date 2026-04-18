"""Test that all MDS fixtures use consistent object_ref format.

Canonical formats:
- mech://part/<id>
- mech://part/<id>/feature/<feature_id>
- mech://assembly/<id>

Old/invalid formats to reject:
- mech://feature/hole/<id>  (feature type in URI)
- mech://part/<id>/feature/hole/<id>  (feature type segment)
"""

import json
import re
from pathlib import Path

import pytest

# Root of test_projects directory
TEST_PROJECTS_ROOT = (
    Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
)

# Canonical object_ref patterns
CANONICAL_PATTERNS = [
    # mech://part/<id>
    re.compile(r"^mech://part/[a-zA-Z0-9_-]+$"),
    # mech://part/<id>/feature/<feature_id>
    re.compile(r"^mech://part/[a-zA-Z0-9_-]+/feature/[a-zA-Z0-9_-]+$"),
    # mech://assembly/<id>
    re.compile(r"^mech://assembly/[a-zA-Z0-9_-]+$"),
]

# Old format patterns that should NOT be used
OLD_FORMAT_PATTERNS = [
    # feature type in top-level URI (e.g., mech://feature/hole/<id>)
    re.compile(r"^mech://feature/\w+/"),
    # feature type segment after /feature/ (e.g., /feature/hole/<id>)
    re.compile(r"/feature/(?:hole|fillet|chamfer|thread|pocket|slot|boss|rib)/"),
]


def is_valid_object_ref(ref: str) -> bool:
    """Check if an object_ref matches one of the canonical patterns."""
    return any(pattern.match(ref) for pattern in CANONICAL_PATTERNS)


def uses_old_format(ref: str) -> bool:
    """Check if an object_ref uses the old format with feature type."""
    return any(pattern.search(ref) for pattern in OLD_FORMAT_PATTERNS)


def collect_object_refs(data: dict, refs: list[str], path: str = "") -> None:
    """Recursively collect all object_ref values from a JSON structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "object_ref" and isinstance(value, str):
                refs.append((value, path))
            else:
                collect_object_refs(value, refs, f"{path}.{key}" if path else key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            collect_object_refs(item, refs, f"{path}[{i}]")


def find_all_mds_files() -> list[Path]:
    """Find all mds.json and expected_mds.json files in test_projects."""
    mds_files = []
    for pattern in ["**/mds.json", "**/expected_mds.json"]:
        mds_files.extend(TEST_PROJECTS_ROOT.glob(pattern))
    return sorted(mds_files)


def get_all_object_refs() -> list[tuple[str, Path, str]]:
    """Get all object_ref values from all MDS fixture files.

    Returns list of (object_ref, file_path, json_path) tuples.
    """
    all_refs = []
    for mds_file in find_all_mds_files():
        with open(mds_file) as f:
            data = json.load(f)
        refs: list[tuple[str, str]] = []
        collect_object_refs(data, refs)
        for ref, json_path in refs:
            all_refs.append((ref, mds_file, json_path))
    return all_refs


class TestObjectRefFormat:
    """Tests for object_ref format consistency."""

    def test_all_mds_files_exist(self):
        """Verify we found MDS fixture files to test."""
        mds_files = find_all_mds_files()
        assert len(mds_files) > 0, "No MDS fixture files found in test_projects/"

    def test_object_refs_match_canonical_format(self):
        """Verify all object_refs use canonical format."""
        all_refs = get_all_object_refs()
        assert len(all_refs) > 0, "No object_ref values found in MDS fixtures"

        invalid_refs = []
        for ref, file_path, json_path in all_refs:
            if not is_valid_object_ref(ref):
                relative_path = file_path.relative_to(TEST_PROJECTS_ROOT.parent)
                invalid_refs.append(f"  {relative_path}:{json_path} = {ref}")

        if invalid_refs:
            pytest.fail(
                f"Found {len(invalid_refs)} object_ref(s) not matching canonical format:\n"
                + "\n".join(invalid_refs)
            )

    def test_no_old_format_with_feature_type(self):
        """Verify no object_refs use old format with feature type segment."""
        all_refs = get_all_object_refs()

        old_format_refs = []
        for ref, file_path, json_path in all_refs:
            if uses_old_format(ref):
                relative_path = file_path.relative_to(TEST_PROJECTS_ROOT.parent)
                old_format_refs.append(f"  {relative_path}:{json_path} = {ref}")

        if old_format_refs:
            pytest.fail(
                f"Found {len(old_format_refs)} object_ref(s) using old format with feature type:\n"
                + "\n".join(old_format_refs)
                + "\n\nExpected format: mech://part/<id>/feature/<feature_id>"
                + "\nNot: mech://part/<id>/feature/hole/<id>"
            )

    def test_canonical_format_examples(self):
        """Test the validation logic with known examples."""
        # Valid canonical formats
        assert is_valid_object_ref("mech://part/abc123")
        assert is_valid_object_ref("mech://part/my_part")
        assert is_valid_object_ref("mech://part/my-part")
        assert is_valid_object_ref("mech://part/abc/feature/hole_0")
        assert is_valid_object_ref("mech://part/abc/feature/geo_hole_1")
        assert is_valid_object_ref("mech://assembly/my_assembly")

        # Invalid formats
        assert not is_valid_object_ref("mech://feature/hole/abc")
        assert not is_valid_object_ref("mech://part/abc/feature/hole/123")
        assert not is_valid_object_ref("mech://invalid/abc")

    def test_old_format_detection(self):
        """Test detection of old format patterns."""
        # Should detect old formats
        assert uses_old_format("mech://feature/hole/abc")
        assert uses_old_format("mech://part/abc/feature/hole/123")
        assert uses_old_format("mech://part/abc/feature/fillet/xyz")

        # Should NOT flag canonical formats
        assert not uses_old_format("mech://part/abc")
        assert not uses_old_format("mech://part/abc/feature/hole_0")
        assert not uses_old_format("mech://assembly/my_asm")
