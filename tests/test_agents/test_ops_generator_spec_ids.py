"""Tests for spec-parameter → ops-program source_spec_ids threading."""

from unittest.mock import MagicMock

from src.agents.ops_generator import _annotate_spec_ids, _build_specs_text


class TestBuildSpecsText:
    """Tests for _build_specs_text enriching specs with GRS IDs."""

    def test_prefixes_grs_id(self):
        spec = MagicMock()
        spec.description = "Hole diameter 6mm"
        spec.metadata = {"grs_id": "S1.1.1"}
        result = _build_specs_text([spec])
        assert "[S1.1.1]" in result
        assert "Hole diameter 6mm" in result

    def test_missing_grs_id_no_prefix(self):
        spec = MagicMock()
        spec.description = "Wall thickness 2mm"
        spec.metadata = {}
        result = _build_specs_text([spec])
        assert "Wall thickness 2mm" in result
        assert "[" not in result

    def test_multiple_specs(self):
        s1 = MagicMock()
        s1.description = "Hole diameter 6mm"
        s1.metadata = {"grs_id": "S1.1.1"}
        s2 = MagicMock()
        s2.description = "Fillet radius 2mm"
        s2.metadata = {"grs_id": "S1.2.1"}
        result = _build_specs_text([s1, s2])
        assert "[S1.1.1]" in result
        assert "[S1.2.1]" in result

    def test_no_metadata_attr_fallback(self):
        spec = MagicMock(spec=[])
        spec.description = "desc"
        del spec.metadata
        result = _build_specs_text([spec])
        assert "desc" in result


class TestAnnotateSpecIds:
    """Tests for _annotate_spec_ids post-hoc matcher."""

    def test_trusts_existing_ids(self):
        """LLM-provided source_spec_ids kept, not overwritten."""
        ops = {
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [{"name": "diameter", "value": 6.0}],
                    "source_spec_ids": ["S1.1.1"],
                }
            ]
        }
        specs = [_mock_spec("S1.1.1", "diameter", 6.0)]
        _annotate_spec_ids(ops, specs)
        assert ops["operations"][0]["source_spec_ids"] == ["S1.1.1"]

    def test_fills_empty_by_name_match(self):
        """Fills empty source_spec_ids via parameter name match."""
        ops = {
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [{"name": "diameter", "value": 6.0}],
                }
            ]
        }
        specs = [_mock_spec("S1.1.1", "diameter", 6.0)]
        _annotate_spec_ids(ops, specs)
        assert "S1.1.1" in ops["operations"][0]["source_spec_ids"]

    def test_fills_by_value_match_float_tol(self):
        """Matches by value within float tolerance 0.01."""
        ops = {
            "operations": [
                {
                    "primitive": "fillet",
                    "parameters": [{"name": "radius", "value": 2.005}],
                }
            ]
        }
        specs = [_mock_spec("S2.1", "radius", 2.0)]
        _annotate_spec_ids(ops, specs)
        assert "S2.1" in ops["operations"][0]["source_spec_ids"]

    def test_no_match_leaves_empty(self):
        """No match leaves source_spec_ids empty."""
        ops = {
            "operations": [
                {
                    "primitive": "box",
                    "parameters": [{"name": "width", "value": 100.0}],
                }
            ]
        }
        specs = [_mock_spec("S1.1.1", "diameter", 6.0)]
        _annotate_spec_ids(ops, specs)
        assert ops["operations"][0].get("source_spec_ids", []) == []

    def test_multiple_specs_match(self):
        """Op can match multiple specs."""
        ops = {
            "operations": [
                {
                    "primitive": "hole",
                    "parameters": [
                        {"name": "diameter", "value": 6.0},
                        {"name": "depth", "value": 15.0},
                    ],
                }
            ]
        }
        specs = [
            _mock_spec("S1.1.1", "diameter", 6.0),
            _mock_spec("S1.1.2", "depth", 15.0),
        ]
        _annotate_spec_ids(ops, specs)
        ids = ops["operations"][0]["source_spec_ids"]
        assert "S1.1.1" in ids
        assert "S1.1.2" in ids


def _mock_spec(grs_id: str, param_name: str, param_value: float) -> MagicMock:
    """Helper to create a mock SpecificationNode."""
    spec = MagicMock()
    spec.metadata = {"grs_id": grs_id}
    param = MagicMock()
    param.name = param_name
    param.value = param_value
    spec.parameters = [param]
    return spec
