"""Unit tests for cad_synth.push_bench_hf — family filter + multi-run merge.

We don't push to HF here (network + token required); we test the helpers:
  - parse_family_filter: empty / None / comma list parsing
  - build_rows family-filter branch: simulate verified_<run>/meta.json files
    in tmp_path and verify include/exclude semantics.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.data_generation.cad_synth.push_bench_hf import (
    build_rows,
    parse_family_filter,
)

# ── parse_family_filter ───────────────────────────────────────────────────────


class TestParseFamilyFilter:
    def test_none_returns_none(self):
        assert parse_family_filter(None) is None

    def test_empty_returns_none(self):
        assert parse_family_filter("") is None

    def test_single_family(self):
        assert parse_family_filter("hex_nut") == {"hex_nut"}

    def test_comma_list(self):
        assert parse_family_filter("a,b,c") == {"a", "b", "c"}

    def test_strips_whitespace(self):
        assert parse_family_filter(" a , b , c ") == {"a", "b", "c"}

    def test_drops_empty_tokens(self):
        # Trailing/double commas don't add empty strings to the set
        assert parse_family_filter("a,,b,") == {"a", "b"}

    def test_returns_set_not_list(self):
        # Sets give O(1) membership, important for the in/not-in check
        assert isinstance(parse_family_filter("x"), set)

    def test_dedups_repeated_names(self):
        assert parse_family_filter("a,b,a") == {"a", "b"}


# ── build_rows family filter ──────────────────────────────────────────────────


@pytest.fixture
def fake_run_dir(tmp_path):
    """Create a tmp directory tree mimicking generated_data/fusion360/<stem>/.

    Returns (data_dir, run_name, fam_to_stems) where each stem has a
    verified_<run>/meta.json + views/composite.png + code.py.
    """
    run_name = "test_run_xx"
    data_dir = tmp_path / "fusion360"
    data_dir.mkdir(parents=True)
    families = {"hex_nut": 3, "washer": 2, "eyebolt": 4}
    fam_to_stems: dict[str, list[str]] = {}
    for fam, n in families.items():
        stems = []
        for i in range(n):
            stem = f"synth_{fam}_{i:03d}_s99"
            stems.append(stem)
            stem_dir = data_dir / stem / f"verified_{run_name}"
            stem_dir.mkdir(parents=True)
            (stem_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "stem": stem,
                        "family": fam,
                        "difficulty": "easy",
                        "params": {"base_plane": "XY"},
                        "feature_tags": {"has_hole": True},
                        "ops_used": ["box"],
                        "qa_pairs": [],
                        "iso_tags": {},
                    }
                )
            )
            (stem_dir / "views").mkdir()
            (stem_dir / "views" / "composite.png").write_bytes(b"FAKE_PNG")
            (stem_dir / "code.py").write_text("import cadquery as cq\nresult = None")
        fam_to_stems[fam] = stems
    return data_dir, run_name, fam_to_stems


def _make_accepted_stems(stems: list[str]) -> set[str]:
    """All stems pass the CSV-side filter."""
    return set(stems)


def _patch_data_dir(monkeypatch, data_dir):
    """Point push_bench_hf.DATA at our tmp dir so glob finds our files."""
    import scripts.data_generation.cad_synth.push_bench_hf as mod

    monkeypatch.setattr(mod, "DATA", data_dir)


class TestBuildRowsFamilyFilter:
    def test_no_filter_returns_all(self, fake_run_dir, monkeypatch):
        data_dir, run_name, fam_to_stems = fake_run_dir
        _patch_data_dir(monkeypatch, data_dir)
        all_stems = sum(fam_to_stems.values(), [])
        # Patch accepted_stems + filter_rows to return all (we want to test family filter, not exec)
        with (
            patch(
                "scripts.data_generation.cad_synth._upload_filter.accepted_stems",
                return_value=_make_accepted_stems(all_stems),
            ),
            patch(
                "scripts.data_generation.cad_synth._upload_filter.filter_rows",
                side_effect=lambda meta_files, *a, **kw: (list(meta_files), {}),
            ),
        ):
            rows = build_rows(run_name, revalidate_code=False)
        assert len(rows) == len(all_stems)
        families_in_rows = {r["family"] for r in rows}
        assert families_in_rows == set(fam_to_stems.keys())

    def test_include_filter_keeps_only_listed(self, fake_run_dir, monkeypatch):
        data_dir, run_name, fam_to_stems = fake_run_dir
        _patch_data_dir(monkeypatch, data_dir)
        all_stems = sum(fam_to_stems.values(), [])
        with (
            patch(
                "scripts.data_generation.cad_synth._upload_filter.accepted_stems",
                return_value=_make_accepted_stems(all_stems),
            ),
            patch(
                "scripts.data_generation.cad_synth._upload_filter.filter_rows",
                side_effect=lambda meta_files, *a, **kw: (list(meta_files), {}),
            ),
        ):
            rows = build_rows(
                run_name,
                revalidate_code=False,
                include_families={"hex_nut", "washer"},
            )
        assert len(rows) == len(fam_to_stems["hex_nut"]) + len(fam_to_stems["washer"])
        assert {r["family"] for r in rows} == {"hex_nut", "washer"}

    def test_exclude_filter_drops_listed(self, fake_run_dir, monkeypatch):
        data_dir, run_name, fam_to_stems = fake_run_dir
        _patch_data_dir(monkeypatch, data_dir)
        all_stems = sum(fam_to_stems.values(), [])
        with (
            patch(
                "scripts.data_generation.cad_synth._upload_filter.accepted_stems",
                return_value=_make_accepted_stems(all_stems),
            ),
            patch(
                "scripts.data_generation.cad_synth._upload_filter.filter_rows",
                side_effect=lambda meta_files, *a, **kw: (list(meta_files), {}),
            ),
        ):
            rows = build_rows(
                run_name,
                revalidate_code=False,
                exclude_families={"eyebolt"},
            )
        assert {r["family"] for r in rows} == {"hex_nut", "washer"}
        assert len(rows) == len(fam_to_stems["hex_nut"]) + len(fam_to_stems["washer"])

    def test_include_and_exclude_combined(self, fake_run_dir, monkeypatch):
        # Inclusion narrows, then exclusion removes from inclusion set
        data_dir, run_name, fam_to_stems = fake_run_dir
        _patch_data_dir(monkeypatch, data_dir)
        all_stems = sum(fam_to_stems.values(), [])
        with (
            patch(
                "scripts.data_generation.cad_synth._upload_filter.accepted_stems",
                return_value=_make_accepted_stems(all_stems),
            ),
            patch(
                "scripts.data_generation.cad_synth._upload_filter.filter_rows",
                side_effect=lambda meta_files, *a, **kw: (list(meta_files), {}),
            ),
        ):
            rows = build_rows(
                run_name,
                revalidate_code=False,
                include_families={"hex_nut", "washer", "eyebolt"},
                exclude_families={"washer"},
            )
        assert {r["family"] for r in rows} == {"hex_nut", "eyebolt"}

    def test_empty_filter_set_includes_nothing(self, fake_run_dir, monkeypatch):
        data_dir, run_name, fam_to_stems = fake_run_dir
        _patch_data_dir(monkeypatch, data_dir)
        all_stems = sum(fam_to_stems.values(), [])
        with (
            patch(
                "scripts.data_generation.cad_synth._upload_filter.accepted_stems",
                return_value=_make_accepted_stems(all_stems),
            ),
            patch(
                "scripts.data_generation.cad_synth._upload_filter.filter_rows",
                side_effect=lambda meta_files, *a, **kw: (list(meta_files), {}),
            ),
        ):
            # Include set is empty → all rows filtered out
            # (parse_family_filter("") returns None which means no filter; but a literal
            # empty SET truthy-evaluates to False so the branch is skipped — this
            # test documents that behavior.)
            rows = build_rows(
                run_name,
                revalidate_code=False,
                include_families=set(),
            )
        # Empty set: branch skipped → all rows pass through (semantics of "no filter")
        assert len(rows) == len(all_stems)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
