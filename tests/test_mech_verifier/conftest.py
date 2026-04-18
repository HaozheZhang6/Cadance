"""Pytest fixtures for mech_verifier tests."""

import json
from pathlib import Path
from typing import Any

import pytest

TEST_PROJECTS = (
    Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
)

# Check if OCCT backend is available
try:
    from src.mech_verifier.mech_verify.backend.occt import OCCT_AVAILABLE
except ImportError:
    OCCT_AVAILABLE = False

requires_occt = pytest.mark.skipif(
    not OCCT_AVAILABLE,
    reason="pythonocc-core not installed (conda-only package)",
)


def load_mds(project_path: Path) -> dict[str, Any]:
    """Load MDS JSON from a test project."""
    mds_path = project_path / "inputs" / "mds.json"
    if not mds_path.exists():
        pytest.skip(f"MDS file not found: {mds_path}")
    with open(mds_path, encoding="utf-8") as f:
        return json.load(f)


def load_expected_findings(project_path: Path) -> dict[str, Any]:
    """Load expected_findings.json from a test project."""
    expected_path = project_path / "expected_findings.json"
    if not expected_path.exists():
        pytest.skip(f"expected_findings.json not found: {expected_path}")
    with open(expected_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def test_projects_root() -> Path:
    """Root directory for test projects."""
    if not TEST_PROJECTS.exists():
        pytest.skip("test_projects directory not found")
    return TEST_PROJECTS


@pytest.fixture
def golden_pass_fixture(test_projects_root: Path) -> Path:
    """Path to step_golden_pass fixture."""
    path = test_projects_root / "step_golden_pass"
    if not path.exists():
        pytest.skip("step_golden_pass fixture not found")
    return path


@pytest.fixture
def hole_too_small_fixture(test_projects_root: Path) -> Path:
    """Path to step_hole_too_small fixture."""
    path = test_projects_root / "step_hole_too_small"
    if not path.exists():
        pytest.skip("step_hole_too_small fixture not found")
    return path


@pytest.fixture
def high_ld_ratio_fixture(test_projects_root: Path) -> Path:
    """Path to step_high_ld_ratio fixture."""
    path = test_projects_root / "step_high_ld_ratio"
    if not path.exists():
        pytest.skip("step_high_ld_ratio fixture not found")
    return path


@pytest.fixture
def missing_units_fixture(test_projects_root: Path) -> Path:
    """Path to step_missing_units fixture."""
    path = test_projects_root / "step_missing_units"
    if not path.exists():
        pytest.skip("step_missing_units fixture not found")
    return path


@pytest.fixture
def small_fillet_fixture(test_projects_root: Path) -> Path:
    """Path to step_small_fillet fixture."""
    path = test_projects_root / "step_small_fillet"
    if not path.exists():
        pytest.skip("step_small_fillet fixture not found")
    return path


@pytest.fixture
def invalid_geometry_fixture(test_projects_root: Path) -> Path:
    """Path to step_invalid_geometry fixture."""
    path = test_projects_root / "step_invalid_geometry"
    if not path.exists():
        pytest.skip("step_invalid_geometry fixture not found")
    return path


@pytest.fixture
def assembly_clean_fixture(test_projects_root: Path) -> Path:
    """Path to step_assembly_clean fixture."""
    path = test_projects_root / "step_assembly_clean"
    if not path.exists():
        pytest.skip("step_assembly_clean fixture not found")
    return path


@pytest.fixture
def assembly_interference_fixture(test_projects_root: Path) -> Path:
    """Path to step_assembly_interference fixture."""
    path = test_projects_root / "step_assembly_interference"
    if not path.exists():
        pytest.skip("step_assembly_interference fixture not found")
    return path


@pytest.fixture
def assembly_clearance_fixture(test_projects_root: Path) -> Path:
    """Path to step_assembly_clearance fixture."""
    path = test_projects_root / "step_assembly_clearance"
    if not path.exists():
        pytest.skip("step_assembly_clearance fixture not found")
    return path


@pytest.fixture
def pmi_present_fixture(test_projects_root: Path) -> Path:
    """Path to step_pmi_present fixture."""
    path = test_projects_root / "step_pmi_present"
    if not path.exists():
        pytest.skip("step_pmi_present fixture not found")
    return path


@pytest.fixture
def pmi_absent_fixture(test_projects_root: Path) -> Path:
    """Path to step_pmi_absent fixture."""
    path = test_projects_root / "step_pmi_absent"
    if not path.exists():
        pytest.skip("step_pmi_absent fixture not found")
    return path
