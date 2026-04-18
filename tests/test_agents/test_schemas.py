"""Tests for schema extensions."""

import pytest
from pydantic import ValidationError

from src.agents.schemas import (
    SpecOutput,
    SpecParameterOutput,
    get_valid_entity_kind_ids,
    get_valid_quantity_ids,
    get_valid_regime_ids,
    validate_entity_id,
    validate_ontology_id,
    validate_quantity_id,
    validate_regime_id,
)


class TestSpecParameterOutputExtensions:
    """Test SpecParameterOutput schema extensions."""

    def test_backward_compat_no_new_fields(self):
        """Old code without new fields still works."""
        param = SpecParameterOutput(name="thickness", value="2.0", unit="mm")
        assert param.quantity_id is None
        assert param.term_class is None

    def test_with_quantity_id(self):
        """Can set quantity_id."""
        param = SpecParameterOutput(
            name="thickness", value="2.0", unit="mm", quantity_id="plate_thickness"
        )
        assert param.quantity_id == "plate_thickness"

    def test_with_term_class_structured(self):
        """Can set term_class to structured."""
        param = SpecParameterOutput(
            name="thickness", value="2.0", unit="mm", term_class="structured"
        )
        assert param.term_class == "structured"

    def test_with_term_class_nl_only(self):
        """Can set term_class to nl_only."""
        param = SpecParameterOutput(
            name="material", value="corrosion resistant", term_class="nl_only"
        )
        assert param.term_class == "nl_only"

    def test_invalid_term_class_rejected(self):
        """Invalid term_class raises validation error."""
        with pytest.raises(ValidationError):
            SpecParameterOutput(
                name="x",
                value="y",
                term_class="invalid",  # type: ignore
            )

    def test_full_new_fields(self):
        """All new fields together."""
        param = SpecParameterOutput(
            name="thickness",
            value="2.0",
            unit="mm",
            tolerance="+/-0.1",
            quantity_id="plate_thickness",
            term_class="structured",
        )
        assert param.quantity_id == "plate_thickness"
        assert param.term_class == "structured"


class TestSpecOutputExtensions:
    """Test SpecOutput schema extensions."""

    def test_backward_compat_no_new_fields(self):
        """Old code without new fields still works."""
        spec = SpecOutput(id="S1.1", description="Test spec")
        assert spec.entity_id is None
        assert spec.regime_id is None

    def test_with_entity_id(self):
        """Can set entity_id."""
        spec = SpecOutput(
            id="S1.1", description="Bracket thickness", entity_id="bracket"
        )
        assert spec.entity_id == "bracket"

    def test_with_regime_id(self):
        """Can set regime_id."""
        spec = SpecOutput(
            id="S1.1", description="Normal operation spec", regime_id="normal"
        )
        assert spec.regime_id == "normal"

    def test_full_new_fields(self):
        """All new fields together."""
        spec = SpecOutput(
            id="S1.1",
            description="Bracket thickness in normal operation",
            entity_id="bracket",
            regime_id="normal",
            parameters=[
                SpecParameterOutput(
                    name="thickness",
                    value="2.0",
                    unit="mm",
                    quantity_id="plate_thickness",
                    term_class="structured",
                )
            ],
        )
        assert spec.entity_id == "bracket"
        assert spec.regime_id == "normal"
        assert spec.parameters[0].quantity_id == "plate_thickness"


class TestValidateOntologyId:
    """Test ontology ID validation helper."""

    def test_none_passes(self):
        """None value passes validation."""
        result = validate_ontology_id(None, ("a", "b"), "test")
        assert result is None

    def test_valid_id_passes(self):
        """Valid ID passes validation."""
        result = validate_ontology_id("a", ("a", "b", "c"), "test")
        assert result == "a"

    def test_invalid_id_raises(self):
        """Invalid ID raises ValueError."""
        with pytest.raises(ValueError) as exc:
            validate_ontology_id("x", ("a", "b", "c"), "quantity_id")
        assert "Invalid quantity_id 'x'" in str(exc.value)
        assert "a, b, c" in str(exc.value)

    def test_error_truncates_long_list(self):
        """Error message truncates long allowed lists."""
        allowed = tuple(f"item_{i}" for i in range(20))
        with pytest.raises(ValueError) as exc:
            validate_ontology_id("bad", allowed, "test")
        assert "..." in str(exc.value)


class TestOntologyWiring:
    """Test schema-to-ontology integration (key_link validation)."""

    def test_get_valid_quantity_ids_from_ontology(self):
        """get_valid_quantity_ids loads from ontology."""
        ids = get_valid_quantity_ids()
        assert isinstance(ids, tuple)
        assert len(ids) >= 24  # From central.yaml
        assert "payload_mass" in ids

    def test_get_valid_regime_ids_from_ontology(self):
        """get_valid_regime_ids loads from ontology."""
        ids = get_valid_regime_ids()
        assert isinstance(ids, tuple)
        assert "normal" in ids

    def test_get_valid_entity_kind_ids_from_ontology(self):
        """get_valid_entity_kind_ids loads from ontology."""
        ids = get_valid_entity_kind_ids()
        assert isinstance(ids, tuple)
        assert "system" in ids

    def test_validate_quantity_id_against_ontology(self):
        """validate_quantity_id checks against loaded ontology."""
        # Valid ID from ontology
        result = validate_quantity_id("payload_mass")
        assert result == "payload_mass"

        # Invalid ID raises
        with pytest.raises(ValueError) as exc:
            validate_quantity_id("not_a_real_quantity")
        assert "Invalid quantity_id" in str(exc.value)

    def test_validate_regime_id_against_ontology(self):
        """validate_regime_id checks against loaded ontology."""
        result = validate_regime_id("normal")
        assert result == "normal"

        with pytest.raises(ValueError):
            validate_regime_id("not_a_regime")

    def test_validate_entity_id_against_ontology(self):
        """validate_entity_id checks against loaded ontology."""
        result = validate_entity_id("system")
        assert result == "system"

        with pytest.raises(ValueError):
            validate_entity_id("not_an_entity")
