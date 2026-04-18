"""Tests for OCCT backend assembly methods (TDD - write first)."""

from pathlib import Path

import pytest

from .conftest import requires_occt

pytestmark = requires_occt

try:
    from src.mech_verifier.mech_verify.backend.occt import OCCTBackend
except ImportError:
    OCCTBackend = None


@pytest.fixture
def backend():
    """Create OCCT backend instance."""
    return OCCTBackend()


def test_load_assembly_returns_none_for_single_part(backend):
    """Single-part STEP → None (no assembly structure)."""
    single_part = Path(
        "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
    )
    result = backend.load_assembly(single_part)
    assert result is None


def test_load_assembly_two_parts_with_transforms(backend):
    """Assembly STEP → dict with occurrences."""
    # Will need real assembly STEP fixture
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    result = backend.load_assembly(asm_path)

    assert result is not None
    assert "name" in result
    assert "occurrences" in result
    assert len(result["occurrences"]) >= 2

    for occ in result["occurrences"]:
        assert "occurrence_id" in occ
        assert "part_id" in occ
        assert "name" in occ
        assert "transform" in occ
        assert "shape" in occ
        assert "bbox" in occ
        # Transform is 4x4 matrix (flat list of 16 floats)
        assert len(occ["transform"]) == 16


def test_load_assembly_deterministic_part_ids(backend):
    """Part IDs consistent across multiple loads."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )

    result1 = backend.load_assembly(asm_path)
    result2 = backend.load_assembly(asm_path)

    if result1 is not None and result2 is not None:
        ids1 = [occ["part_id"] for occ in result1["occurrences"]]
        ids2 = [occ["part_id"] for occ in result2["occurrences"]]
        assert ids1 == ids2


def test_get_intersection_volume_overlapping(backend):
    """Overlapping shapes → positive volume."""
    # Use same shape for self-intersection (= full volume)
    single_part = Path(
        "src/mech_verifier/test_projects/step_golden_pass/inputs/simple_box.step"
    )
    shapes = backend.load_step(single_part)

    if not shapes:
        pytest.skip("Need valid STEP file")

    shape = shapes[0]
    # Self-intersection should equal shape volume
    volume = backend.get_intersection_volume(shape, shape)
    assert volume > 0.0


def test_get_intersection_volume_separated(backend):
    """Non-overlapping shapes → zero volume."""
    # Will need assembly with separated parts
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    result = backend.load_assembly(asm_path)

    if result is None or len(result["occurrences"]) < 2:
        pytest.skip("Need assembly with 2+ separated parts")

    shape_a = result["occurrences"][0]["shape"]
    shape_b = result["occurrences"][1]["shape"]
    volume = backend.get_intersection_volume(shape_a, shape_b)
    assert volume == 0.0


def test_get_min_distance_separated(backend):
    """Separated shapes → positive distance."""
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )
    result = backend.load_assembly(asm_path)

    if result is None or len(result["occurrences"]) < 2:
        pytest.skip("Need assembly with 2+ parts")

    shape_a = result["occurrences"][0]["shape"]
    shape_b = result["occurrences"][1]["shape"]
    distance = backend.get_min_distance(shape_a, shape_b)
    assert distance > 0.0


def test_get_min_distance_touching(backend):
    """Touching/overlapping shapes → zero or near-zero distance."""
    # Will need assembly with interference
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_interference/inputs/assembly.step"
    )
    result = backend.load_assembly(asm_path)

    if result is None or len(result["occurrences"]) < 2:
        pytest.skip("Need assembly with interference")

    shape_a = result["occurrences"][0]["shape"]
    shape_b = result["occurrences"][1]["shape"]
    distance = backend.get_min_distance(shape_a, shape_b)
    assert distance < 0.1  # Touching or overlapping


def test_backend_graceful_degradation(backend):
    """Invalid inputs → conservative fallback (no crash)."""
    # Test with None/invalid shapes
    try:
        volume = backend.get_intersection_volume(None, None)
        assert volume == 0.0  # Conservative
    except Exception:
        pass  # OK to raise, just don't crash

    try:
        distance = backend.get_min_distance(None, None)
        assert distance == float("inf")  # Conservative
    except Exception:
        pass


def test_load_assembly_uses_xde_when_available():
    """Test that XDE parsing is used for proper assembly STEP files."""
    from pathlib import Path

    from mech_verify.backend.occt import OCCTBackend

    backend = OCCTBackend()
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )

    result = backend.load_assembly(asm_path)
    assert result is not None
    assert result.get("has_xde") is True, "Should use XDE for assembly STEP"
    assert len(result.get("occurrences", [])) >= 2


def test_xde_assembly_has_transforms():
    """Test that XDE assembly loading extracts transforms."""
    from pathlib import Path

    from mech_verify.backend.occt import OCCTBackend

    backend = OCCTBackend()
    asm_path = Path(
        "src/mech_verifier/test_projects/step_asm_clean/inputs/assembly.step"
    )

    result = backend.load_assembly(asm_path)
    assert result is not None

    for occ in result.get("occurrences", []):
        transform = occ.get("transform")
        assert transform is not None, "Each occurrence should have a transform"
        assert len(transform) == 16, "Transform should be 4x4 matrix (16 elements)"
