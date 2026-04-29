"""Integration tests for bench.metrics — real STEP files via CadQuery.

Builds tiny test parts in tmp_path and exercises the file-touching paths:
  - _step_has_hole (Method B detector, appendix §D.7)
  - extract_features(code, step_path) — Method B overrides AST when STEP given
  - compute_iou / compute_chamfer / compute_hausdorff self-self sanity

Each test is gated by tests.conftest.requires_working_cadquery so the suite
skips cleanly on environments where OCP is missing or HashCode-broken.

The two key examples mirror appendix §D.4:
  - test_extract_features_step_overrides_ast_fp:  rect cutThruAll
    AST=True but STEP=False (A_harms case → B avoids Type II FP).
  - test_extract_features_step_overrides_ast_to_true:  bore in geometry but
    no hole-API in code (B catches what AST cannot — bellows-style rescue).
"""

from __future__ import annotations

import pytest

from bench.metrics import (
    compute_chamfer,
    compute_hausdorff,
    compute_iou,
    extract_features,
)


def _step_pipeline_works() -> bool:
    """Narrower smoke test than conftest.requires_working_cadquery.

    These tests don't use cq's `.faces(selector)` (which calls hashCode and
    breaks on OCP builds missing TopoDS_Face.HashCode). We only need:
    box/cylinder construction, hole/cutThruAll, STEP export/import, OCP
    TopExp face walk. Test that pipeline directly.
    """
    try:
        import tempfile
        from pathlib import Path

        import cadquery as cq

        with tempfile.TemporaryDirectory() as tmp:
            r = cq.Workplane("XY").box(10, 10, 10).workplane().hole(2)
            p = Path(tmp) / "smoke.step"
            cq.exporters.export(r, str(p))
            shape = cq.importers.importStep(str(p))
            _ = shape.val()  # touch the wrapped solid
        return True
    except Exception:
        return False


requires_working_cadquery = pytest.mark.skipif(
    not _step_pipeline_works(),
    reason="CadQuery box/hole/STEP roundtrip not functional in this env",
)


# ── Fixtures: tiny CadQuery parts → STEP files in tmp_path ────────────────


@pytest.fixture
def cq_drilled_box(tmp_path):
    """10×10×10 mm box with a 2mm-diameter bore through Z (r=1.0 mm > 0.5 mm
    threshold in `_step_has_hole`).

    Avoids `.faces('>Z')` selector — that path goes through cq's hashCode-based
    de-dup which breaks on OCP builds missing TopoDS_Face.HashCode. Workplane
    default normal is +Z, so `.workplane().hole(2)` drills through Z.
    """
    import cadquery as cq

    r = cq.Workplane("XY").box(10, 10, 10).workplane().hole(2)
    out = tmp_path / "drilled.step"
    cq.exporters.export(r, str(out))
    return str(out)


@pytest.fixture
def cq_solid_box(tmp_path):
    """Plain 10×10×10 mm box. No inner cylindrical face."""
    import cadquery as cq

    r = cq.Workplane("XY").box(10, 10, 10)
    out = tmp_path / "solid.step"
    cq.exporters.export(r, str(out))
    return str(out)


@pytest.fixture
def cq_rect_cut_box(tmp_path):
    """rect cutThruAll — appendix §D.5 Type II: AST=True but no Cylinder face."""
    import cadquery as cq

    r = cq.Workplane("XY").box(10, 10, 4).workplane().rect(4, 4).cutThruAll()
    out = tmp_path / "rect_cut.step"
    cq.exporters.export(r, str(out))
    return str(out)


# ── _step_has_hole (Method B detector) ────────────────────────────────────


@requires_working_cadquery
def test_step_has_hole_drilled_returns_true(cq_drilled_box):
    from bench.metrics import _step_has_hole

    assert _step_has_hole(cq_drilled_box) is True


@requires_working_cadquery
def test_step_has_hole_solid_returns_false(cq_solid_box):
    from bench.metrics import _step_has_hole

    assert _step_has_hole(cq_solid_box) is False


@requires_working_cadquery
def test_step_has_hole_rect_cut_returns_false(cq_rect_cut_box):
    """Appendix §D.5 Type II: rectangular cutThruAll produces only planar faces."""
    from bench.metrics import _step_has_hole

    assert _step_has_hole(cq_rect_cut_box) is False


@requires_working_cadquery
def test_step_has_hole_missing_file_returns_false(tmp_path):
    """Defensive: bad path returns False, does not raise."""
    from bench.metrics import _step_has_hole

    assert _step_has_hole(str(tmp_path / "nonexistent.step")) is False


# ── extract_features Method B integration (the production decision) ──────


@requires_working_cadquery
def test_extract_features_step_overrides_ast_fp(cq_rect_cut_box):
    """A_harms case (appendix §D.4.1): rect_frame / l_bracket / hollow_tube.

    AST regex matches `cutThruAll(` and would return True. STEP B-rep has no
    cylindrical face. Production Method B: STEP authoritative → has_hole=False.
    """
    code = (
        "import cadquery as cq\n"
        "r = cq.Workplane().box(1, 1, 0.4).faces('>Z').rect(0.4, 0.4).cutThruAll()"
    )
    assert extract_features(code)["has_hole"] is True  # AST alone
    assert extract_features(code, cq_rect_cut_box)["has_hole"] is False  # STEP wins


@requires_working_cadquery
def test_extract_features_step_overrides_ast_to_true(cq_drilled_box):
    """Inverse: bellows-style — no hole-API in code, but bore in geometry.

    Mirrors the B_alone bucket (appendix §D.3.2 — n=150). STEP rescues what
    AST cannot see (revolve / boolean cut / sweep+cut). Production Method B
    catches these because STEP overrides.
    """
    code = "import cadquery as cq\nr = cq.Workplane().box(1, 1, 1)"
    assert extract_features(code)["has_hole"] is False  # AST sees nothing
    assert extract_features(code, cq_drilled_box)["has_hole"] is True  # STEP overrides


@requires_working_cadquery
def test_extract_features_fillet_chamfer_unaffected_by_step(cq_drilled_box):
    """has_fillet / has_chamfer never consult STEP — only has_hole does."""
    code = "r = cq.Workplane().box(1, 1, 1).fillet(0.05).chamfer(0.02)"
    feats = extract_features(code, cq_drilled_box)
    assert feats["has_fillet"] is True
    assert feats["has_chamfer"] is True


# ── Geometric metrics self-self sanity ───────────────────────────────────


@requires_working_cadquery
def test_compute_iou_self_self_is_one(cq_solid_box):
    iou, err = compute_iou(cq_solid_box, cq_solid_box)
    assert err is None
    assert iou >= 0.99  # appendix §D.8.1: voxelisation deterministic, exact 1.0


@requires_working_cadquery
def test_compute_iou_drilled_vs_solid_below_one(cq_drilled_box, cq_solid_box):
    """Drilled removes mass — strictly smaller intersection than self-IoU."""
    iou, err = compute_iou(cq_drilled_box, cq_solid_box)
    assert err is None
    assert iou < 0.99


@requires_working_cadquery
def test_compute_chamfer_self_self_near_zero(cq_solid_box):
    """Surface sampling jitter only — should be ~1e-4 magnitude."""
    cd, err = compute_chamfer(cq_solid_box, cq_solid_box)
    assert err is None
    assert cd < 0.01


@requires_working_cadquery
def test_compute_hausdorff_self_self_below_threshold(cq_solid_box):
    """Self-self HD has a sampling-density floor on unit-cube normalised mesh.

    With 2048 surface samples, max-of-mins between two random samplings of the
    same mesh is typically 0.05–0.1. _HD_LOW=0.05 in metrics is calibrated to
    this floor.
    """
    hd, err = compute_hausdorff(cq_solid_box, cq_solid_box)
    assert err is None
    assert hd < 0.15


@requires_working_cadquery
def test_compute_chamfer_handles_missing_file(tmp_path):
    """Bad path returns (inf, error string), does not raise."""
    cd, err = compute_chamfer(str(tmp_path / "missing.step"), str(tmp_path / "x.step"))
    assert cd == float("inf")
    assert err is not None


@requires_working_cadquery
def test_compute_hausdorff_handles_missing_file(tmp_path):
    hd, err = compute_hausdorff(
        str(tmp_path / "missing.step"), str(tmp_path / "x.step")
    )
    assert hd == float("inf")
    assert err is not None
