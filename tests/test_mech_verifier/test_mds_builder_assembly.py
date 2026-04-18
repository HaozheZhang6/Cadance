"""Tests for MDS builder assembly integration (TDD)."""

from pathlib import Path

import pytest

from src.mech_verifier.mech_verify.mds.builder import MDSBuilder

from .conftest import requires_occt

pytestmark = requires_occt

try:
    from src.mech_verifier.mech_verify.backend.occt import OCCTBackend
except ImportError:
    OCCTBackend = None


@pytest.fixture
def builder():
    """Create MDS builder instance."""
    return MDSBuilder()


@pytest.fixture
def backend():
    """Create OCCT backend instance."""
    return OCCTBackend()


def test_build_single_part_no_assemblies(builder, backend):
    """Single-part STEP → assemblies[] stays empty."""
    single_part = Path(
        "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
    )
    mds = builder.build_from_step(single_part, backend)

    assert "assemblies" in mds
    assert len(mds["assemblies"]) == 0
    assert len(mds["parts"]) >= 1


def test_build_assembly_populates_array(builder, backend):
    """Multi-solid STEP → assemblies[] populated."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    mds = builder.build_from_step(asm_path, backend)

    assert "assemblies" in mds
    assert len(mds["assemblies"]) == 1
    assert len(mds["parts"]) >= 2

    asm = mds["assemblies"][0]
    assert "assembly_id" in asm
    assert "name" in asm
    assert "object_ref" in asm
    assert "occurrences" in asm
    assert len(asm["occurrences"]) >= 2


def test_assembly_occurrences_reference_parts(builder, backend):
    """Assembly occurrences link to parts[] via part_id."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    mds = builder.build_from_step(asm_path, backend)

    if len(mds["assemblies"]) == 0:
        pytest.skip("No assembly detected")

    asm = mds["assemblies"][0]
    part_ids = {p["part_id"] for p in mds["parts"]}

    for occ in asm["occurrences"]:
        assert "part_id" in occ
        assert "occurrence_id" in occ
        assert "transform" in occ
        assert "bbox" in occ
        # Occurrence references valid part
        assert occ["part_id"] in part_ids


def test_assembly_id_deterministic(builder, backend):
    """Assembly IDs consistent across builds."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )

    mds1 = builder.build_from_step(asm_path, backend)
    mds2 = builder.build_from_step(asm_path, backend)

    if len(mds1["assemblies"]) == 0:
        pytest.skip("No assembly detected")

    asm_id_1 = mds1["assemblies"][0]["assembly_id"]
    asm_id_2 = mds2["assemblies"][0]["assembly_id"]

    assert asm_id_1 == asm_id_2
    assert len(asm_id_1) == 12  # SHA256[:12]


def test_assembly_occurrences_have_shapes(builder, backend):
    """Occurrences include shape objects for geometry ops."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    mds = builder.build_from_step(asm_path, backend)

    if len(mds["assemblies"]) == 0:
        pytest.skip("No assembly detected")

    asm = mds["assemblies"][0]

    for occ in asm["occurrences"]:
        # Shape stored for interference/clearance checks
        assert "shape" in occ
        # But not serialized to JSON (checked in orchestrator)
        assert occ["shape"] is not None


def test_backward_compat_parts_always_populated(builder, backend):
    """parts[] always populated regardless of assembly detection."""
    paths = [
        Path("src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"),
        Path("src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"),
    ]

    for path in paths:
        mds = builder.build_from_step(path, backend)
        assert len(mds["parts"]) >= 1
        assert "part_id" in mds["parts"][0]
        assert "mass_props" in mds["parts"][0]
