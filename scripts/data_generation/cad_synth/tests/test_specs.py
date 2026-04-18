"""Tests for family spec YAML files."""

from pathlib import Path

import yaml
import pytest

SPECS_DIR = Path(__file__).parent.parent / "specs"
REQUIRED_KEYS = {"family", "difficulty_levels", "ops", "params", "constraints", "feature_tags"}


def _load_specs():
    """Load all spec YAML files."""
    specs = {}
    for p in sorted(SPECS_DIR.glob("*.yaml")):
        with open(p) as f:
            specs[p.stem] = yaml.safe_load(f)
    return specs


@pytest.fixture
def specs():
    """All loaded spec dicts."""
    return _load_specs()


def test_specs_exist():
    """At least 2 spec files exist."""
    yamls = list(SPECS_DIR.glob("*.yaml"))
    assert len(yamls) >= 2, f"Only {len(yamls)} specs found"


def test_spec_required_keys(specs):
    """Every spec has all required keys."""
    for name, spec in specs.items():
        missing = REQUIRED_KEYS - set(spec.keys())
        assert not missing, f"{name} missing keys: {missing}"


def test_spec_difficulty_levels(specs):
    """Every spec includes easy and hard at minimum."""
    for name, spec in specs.items():
        levels = spec["difficulty_levels"]
        assert "easy" in levels, f"{name} missing 'easy'"
        assert "hard" in levels, f"{name} missing 'hard'"


def test_spec_ops_nonempty(specs):
    """Every spec lists at least one op."""
    for name, spec in specs.items():
        assert len(spec["ops"]) >= 1, f"{name} has no ops"


def test_spec_params_are_ranges(specs):
    """Every param value is a 2-element list [min, max]."""
    for name, spec in specs.items():
        for pname, prange in spec["params"].items():
            assert isinstance(prange, list) and len(prange) == 2, (
                f"{name}.params.{pname} not a [min,max] pair: {prange}"
            )
            assert prange[0] <= prange[1], (
                f"{name}.params.{pname}: min > max ({prange})"
            )
