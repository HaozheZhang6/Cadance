"""Tests for scoped ontology loader."""

import tempfile
from pathlib import Path

import yaml

from src.verification.semantic.scoped_ontology.loader import (
    _merge_ontology,
    load_ontology,
    validate_unit_compatibility,
)


class TestLoadOntology:
    """Test ontology loading."""

    def test_load_central_ontology(self):
        """Load default central ontology."""
        ont = load_ontology()

        # Verify quantities (24 from SymbolTable)
        assert len(ont.quantities) >= 24
        assert "payload_mass" in ont.quantities
        assert "hole_diameter" in ont.quantities
        assert "safety_factor" in ont.quantities

    def test_quantities_have_required_fields(self):
        """Each quantity has dimensionality and canonical_unit."""
        ont = load_ontology()

        for qid, q in ont.quantities.items():
            assert q.dimensionality, f"{qid} missing dimensionality"
            # canonical_unit can be empty for dimensionless

    def test_regimes_from_ontology(self):
        """Load 9 regimes."""
        ont = load_ontology()

        assert len(ont.regimes) >= 9
        regime_ids = ont.get_regime_ids()
        assert "normal" in regime_ids
        assert "startup" in regime_ids
        assert "fault" in regime_ids

    def test_entity_kinds_present(self):
        """Load entity kinds."""
        ont = load_ontology()

        assert len(ont.entity_kinds) >= 4
        kind_ids = ont.get_entity_kind_ids()
        assert "system" in kind_ids
        assert "payload" in kind_ids


class TestOverlayMerge:
    """Test overlay merge logic."""

    def test_overlay_adds_new_quantity(self):
        """Overlay can add new quantity."""
        base = {
            "version": "1.0",
            "quantities": {
                "mass": {"dimensionality": "[mass]", "canonical_unit": "kg"}
            },
            "regimes": [],
            "entity_kinds": [],
        }
        overlay = {
            "quantities": {
                "length": {"dimensionality": "[length]", "canonical_unit": "m"}
            }
        }

        merged = _merge_ontology(base, overlay)
        assert "mass" in merged["quantities"]
        assert "length" in merged["quantities"]

    def test_overlay_extends_regimes(self):
        """Overlay extends regime list."""
        base = {
            "version": "1.0",
            "quantities": {},
            "regimes": [{"id": "normal", "label": "Normal"}],
            "entity_kinds": [],
        }
        overlay = {"regimes": [{"id": "hover", "label": "Hover"}]}

        merged = _merge_ontology(base, overlay)
        assert len(merged["regimes"]) == 2

    def test_overlay_no_duplicate_regimes(self):
        """Overlay doesn't duplicate existing regime IDs."""
        base = {
            "version": "1.0",
            "quantities": {},
            "regimes": [{"id": "normal", "label": "Normal"}],
            "entity_kinds": [],
        }
        overlay = {"regimes": [{"id": "normal", "label": "Override"}]}  # Same ID

        merged = _merge_ontology(base, overlay)
        assert len(merged["regimes"]) == 1  # Not duplicated

    def test_overlay_overrides_quantity_fields(self):
        """Overlay can override existing quantity fields (ONT-04: extends/overrides)."""
        base = {
            "version": "1.0",
            "quantities": {
                "mass": {
                    "dimensionality": "[mass]",
                    "canonical_unit": "kg",
                    "aliases": ["weight"],
                }
            },
            "regimes": [],
            "entity_kinds": [],
        }
        overlay = {
            "quantities": {
                "mass": {
                    "dimensionality": "[mass]",
                    "canonical_unit": "g",  # Override unit
                    "aliases": ["weight", "payload_mass"],  # Override aliases
                }
            }
        }

        merged = _merge_ontology(base, overlay)
        # Overlay completely replaces the quantity definition
        assert merged["quantities"]["mass"]["canonical_unit"] == "g"
        assert "payload_mass" in merged["quantities"]["mass"]["aliases"]

    def test_load_with_overlay_file(self):
        """Load central + overlay from files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "quantities": {
                        "custom_param": {
                            "dimensionality": "[length]",
                            "canonical_unit": "m",
                            "aliases": [],
                            "domain_class": "LENGTH_POS",
                        }
                    }
                },
                f,
            )
            overlay_path = Path(f.name)

        try:
            ont = load_ontology(overlay_path=overlay_path)
            assert "custom_param" in ont.quantities
            assert "payload_mass" in ont.quantities  # Base still there
        finally:
            overlay_path.unlink()


class TestUnitValidation:
    """Test unit compatibility validation."""

    def test_compatible_unit(self):
        """Valid unit passes."""
        ont = load_ontology()
        ok, err = validate_unit_compatibility("payload_mass", "kg", ont)
        assert ok is True
        assert err is None

    def test_incompatible_unit(self):
        """Mismatched dimensionality fails."""
        ont = load_ontology()
        ok, err = validate_unit_compatibility("payload_mass", "m", ont)
        assert ok is False
        assert "dimensionality" in err

    def test_unknown_quantity_passes(self):
        """Unknown quantity_id skips validation."""
        ont = load_ontology()
        ok, err = validate_unit_compatibility("unknown_qty", "whatever", ont)
        assert ok is True

    def test_empty_unit_passes(self):
        """Empty unit skips validation."""
        ont = load_ontology()
        ok, err = validate_unit_compatibility("payload_mass", "", ont)
        assert ok is True

    def test_dimensionless_quantity(self):
        """Dimensionless quantities validate correctly."""
        ont = load_ontology()
        ok, err = validate_unit_compatibility("safety_factor", "", ont)
        assert ok is True


class TestOntologyHelpers:
    """Test Ontology helper methods."""

    def test_get_quantity_ids(self):
        """get_quantity_ids returns tuple of IDs."""
        ont = load_ontology()
        ids = ont.get_quantity_ids()
        assert isinstance(ids, tuple)
        assert len(ids) >= 24

    def test_get_regime_ids(self):
        """get_regime_ids returns tuple of IDs."""
        ont = load_ontology()
        ids = ont.get_regime_ids()
        assert isinstance(ids, tuple)
        assert "normal" in ids

    def test_get_entity_kind_ids(self):
        """get_entity_kind_ids returns tuple of IDs."""
        ont = load_ontology()
        ids = ont.get_entity_kind_ids()
        assert isinstance(ids, tuple)
        assert "system" in ids
