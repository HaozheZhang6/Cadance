"""Tests for parametric families — param sampling, validation, program generation."""

import numpy as np
import pytest

from ..families.mounting_plate import MountingPlateFamily
from ..families.round_flange import RoundFlangeFamily
from ..pipeline.builder import Program, render_program_to_code


FAMILIES = [MountingPlateFamily(), RoundFlangeFamily()]
DIFFICULTIES = ["easy", "medium", "hard"]


@pytest.fixture(params=FAMILIES, ids=lambda f: f.name)
def family(request):
    """Parametrize over all families."""
    return request.param


@pytest.fixture
def rng():
    """Deterministic RNG."""
    return np.random.default_rng(12345)


class TestSampleParams:
    """Test parameter sampling."""

    def test_returns_dict(self, family, rng):
        """sample_params returns a dict."""
        for diff in DIFFICULTIES:
            p = family.sample_params(diff, rng)
            assert isinstance(p, dict), f"{family.name}/{diff} not dict"

    def test_valid_after_sample(self, family, rng):
        """Sampled params pass validation most of the time."""
        ok = 0
        for _ in range(20):
            for diff in DIFFICULTIES:
                p = family.sample_params(diff, rng)
                if family.validate_params(p):
                    ok += 1
        # At least 80% should be valid
        total = 20 * len(DIFFICULTIES)
        assert ok / total >= 0.8, f"{family.name}: only {ok}/{total} valid"


class TestValidateParams:
    """Test parameter validation."""

    def test_reject_bad_mounting_plate(self):
        """Mounting plate rejects thickness < 3."""
        f = MountingPlateFamily()
        assert not f.validate_params({"length": 50, "width": 50, "thickness": 1})

    def test_reject_bad_flange(self):
        """Flange rejects inner >= outer."""
        f = RoundFlangeFamily()
        assert not f.validate_params({
            "outer_radius": 20, "inner_radius": 25, "height": 10,
        })


class TestMakeProgram:
    """Test program generation."""

    def test_returns_program(self, family, rng):
        """make_program returns a Program with ops."""
        for diff in DIFFICULTIES:
            p = family.sample_params(diff, rng)
            if not family.validate_params(p):
                continue
            prog = family.make_program(p)
            assert isinstance(prog, Program)
            assert len(prog.ops) >= 1
            assert prog.family == family.name

    def test_easy_fewer_ops(self, family, rng):
        """Easy difficulty produces fewer ops than hard."""
        easy_counts = []
        hard_counts = []
        for _ in range(10):
            ep = family.sample_params("easy", rng)
            hp = family.sample_params("hard", rng)
            if family.validate_params(ep):
                easy_counts.append(len(family.make_program(ep).ops))
            if family.validate_params(hp):
                hard_counts.append(len(family.make_program(hp).ops))
        if easy_counts and hard_counts:
            assert np.mean(easy_counts) <= np.mean(hard_counts)


class TestExportCode:
    """Test code rendering."""

    def test_code_is_valid_python(self, family, rng):
        """Rendered code is syntactically valid Python."""
        for diff in DIFFICULTIES:
            p = family.sample_params(diff, rng)
            if not family.validate_params(p):
                continue
            code = family.export_code(p)
            assert "import cadquery" in code
            # Check syntax
            compile(code, "<test>", "exec")

    def test_code_contains_ops(self, family, rng):
        """Rendered code contains expected CadQuery method calls."""
        p = family.sample_params("easy", rng)
        if not family.validate_params(p):
            return
        code = family.export_code(p)
        # Should have at least one CQ builder call
        assert ".box(" in code or ".cylinder(" in code
