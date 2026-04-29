"""Unit tests for cad_synth.pipeline.registry — family lookup + count.

Family code execution is tested separately (tests/test_data_generation/
test_pipeline_families.py); this file just verifies the registry mechanics.
"""

from __future__ import annotations

import pytest

from scripts.data_generation.cad_synth.families.base import BaseFamily
from scripts.data_generation.cad_synth.pipeline.registry import (
    get_family,
    list_families,
    register_family,
)

# ── list_families ─────────────────────────────────────────────────────────────


class TestListFamilies:
    def test_returns_list(self):
        families = list_families()
        assert isinstance(families, list)
        assert len(families) > 0

    def test_sorted_alphabetically(self):
        families = list_families()
        assert families == sorted(families)

    def test_no_duplicates(self):
        families = list_families()
        assert len(families) == len(set(families))

    def test_count_matches_claudemd_target(self):
        """CLAUDE.md states 106 registered families as of 2026-04-19.

        This test guards against accidental drops/dupes during family edits.
        Update the constant when new families are added intentionally.
        """
        # Allow some growth (≥106), but flag drops below.
        families = list_families()
        assert len(families) >= 106, (
            f"Family count regressed: {len(families)} < 106. "
            "If this is intentional (deliberate removal), update CLAUDE.md "
            "and the test target together."
        )

    def test_known_families_present(self):
        """Smoke check: a few well-known families are registered.

        Failure here usually means an import-time error in the family module
        is silently dropping it from registry.
        """
        families = set(list_families())
        # Sample of the 41 modified + a few unchanged
        for name in [
            "grease_nipple",
            "eyebolt",
            "hex_nut",
            "washer",
            "bevel_gear",  # unchanged
            "bolt",  # unchanged
        ]:
            assert name in families, f"family {name!r} missing from registry"


# ── get_family ────────────────────────────────────────────────────────────────


class TestGetFamily:
    def test_returns_base_family_instance(self):
        fam = get_family("hex_nut")
        assert isinstance(fam, BaseFamily)

    def test_name_attribute_matches(self):
        fam = get_family("hex_nut")
        assert fam.name == "hex_nut"

    def test_unknown_raises_keyerror(self):
        with pytest.raises(KeyError, match="Unknown family"):
            get_family("totally_made_up_family")

    def test_keyerror_lists_available(self):
        try:
            get_family("xyz_not_real")
        except KeyError as e:
            # Error message includes "Available:" with the list
            assert "Available" in str(e)


# ── register_family (dynamic addition) ────────────────────────────────────────


class _FakeFamily(BaseFamily):
    name = "_fake_test_family_xyz"
    standard = "TEST"

    def sample_params(self, difficulty, rng):
        return {"difficulty": difficulty}

    def validate_params(self, params):
        return True

    def make_program(self, params):
        from scripts.data_generation.cad_synth.pipeline.builder import Op, Program

        return Program(
            family=self.name,
            difficulty=params["difficulty"],
            params=params,
            ops=[Op("box", {"length": 1, "width": 1, "height": 1})],
        )


class TestRegisterFamily:
    def test_register_then_get(self):
        register_family(_FakeFamily())
        fam = get_family("_fake_test_family_xyz")
        assert isinstance(fam, _FakeFamily)
        assert fam.standard == "TEST"

    def test_registered_appears_in_list(self):
        register_family(_FakeFamily())
        assert "_fake_test_family_xyz" in list_families()


# ── Smoke: every registered family responds to sample_params ──────────────────


class TestAllFamiliesSmoke:
    """Cross-cutting: each family must implement the BaseFamily contract.

    Calling sample_params + validate_params with seed=0 should not raise for
    any registered family. This catches typos / missing methods on new families.
    """

    @pytest.mark.parametrize("family_name", list_families())
    def test_sample_params_does_not_raise(self, family_name):
        import numpy as np

        fam = get_family(family_name)
        rng = np.random.default_rng(0)
        # At least one of the 3 difficulties must produce a valid params dict
        any_valid = False
        for diff in ("easy", "medium", "hard"):
            try:
                p = fam.sample_params(diff, rng)
                if fam.validate_params(p):
                    any_valid = True
                    break
            except Exception as e:
                pytest.fail(f"{family_name}.sample_params({diff}) raised: {e}")
        assert any_valid, f"{family_name} produced no valid sample in 3 difficulties"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
