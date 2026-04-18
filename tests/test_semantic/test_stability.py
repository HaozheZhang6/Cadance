"""Tests for identity binding registry and drift detection.

STB-01: BindingRegistry.register() raises BindingConflictError on conflict
STB-02: Bindings are append-only
STB-03: detect_drift() returns (has_drift, list[DriftViolation])
STB-04: DriftViolation checks triple fields only (not value bounds)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from src.verification.semantic.scoped_symbol_table import ScopedKey
from src.verification.semantic.stability import (
    BindingConflictError,
    BindingRegistry,
    DriftViolation,
    IdentityBinding,
    detect_drift,
)

if TYPE_CHECKING:
    pass


# ==============================================================================
# IdentityBinding tests
# ==============================================================================


class TestIdentityBinding:
    """Tests for IdentityBinding frozen dataclass."""

    def test_identity_binding_is_frozen(self) -> None:
        """STB-02: IdentityBinding is immutable."""
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        binding = IdentityBinding(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_at=datetime.now(),
            created_by="user",
        )
        with pytest.raises(AttributeError):
            binding.spec_id = "SPEC-002"  # type: ignore

    def test_identity_binding_fields(self) -> None:
        """IdentityBinding has required fields."""
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        ts = datetime(2026, 2, 4, 12, 0, 0)
        binding = IdentityBinding(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_at=ts,
            created_by="user",
        )
        assert binding.spec_id == "SPEC-001"
        assert binding.param_name == "thickness"
        assert binding.scoped_key == key
        assert binding.created_at == ts
        assert binding.created_by == "user"

    def test_identity_binding_binding_id(self) -> None:
        """IdentityBinding.binding_id combines spec::param."""
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        binding = IdentityBinding(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_at=datetime.now(),
            created_by="user",
        )
        assert binding.binding_id == "SPEC-001::thickness"


# ==============================================================================
# BindingRegistry tests
# ==============================================================================


class TestBindingRegistry:
    """Tests for BindingRegistry."""

    def test_register_new_binding(self) -> None:
        """Register returns binding for new spec::param."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        binding = registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        assert binding.spec_id == "SPEC-001"
        assert binding.param_name == "thickness"
        assert binding.scoped_key == key

    def test_register_same_binding_idempotent(self) -> None:
        """STB-01: Same (spec, param, key) is idempotent."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        b1 = registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        b2 = registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        assert b1 == b2
        assert len(registry.all_bindings()) == 1

    def test_register_conflicting_binding_raises(self) -> None:
        """STB-01: Different scoped_key for same spec::param raises."""
        registry = BindingRegistry()
        key1 = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        key2 = ScopedKey(
            entity_id="housing", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key1,
            created_by="user",
        )
        with pytest.raises(BindingConflictError) as exc_info:
            registry.register(
                spec_id="SPEC-001",
                param_name="thickness",
                scoped_key=key2,
                created_by="user",
            )
        assert "SPEC-001::thickness" in str(exc_info.value)
        assert "bracket" in str(exc_info.value) or "housing" in str(exc_info.value)

    def test_get_returns_binding_if_exists(self) -> None:
        """get() returns binding for existing spec::param."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        binding = registry.get("SPEC-001", "thickness")
        assert binding is not None
        assert binding.scoped_key == key

    def test_get_returns_none_if_not_exists(self) -> None:
        """get() returns None for non-existent binding."""
        registry = BindingRegistry()
        binding = registry.get("SPEC-001", "thickness")
        assert binding is None

    def test_all_bindings_returns_copy(self) -> None:
        """all_bindings() returns list of all bindings."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        bindings = registry.all_bindings()
        assert len(bindings) == 1
        assert bindings[0].spec_id == "SPEC-001"

    def test_registry_append_only_no_delete(self) -> None:
        """STB-02: No delete method exists."""
        registry = BindingRegistry()
        assert not hasattr(registry, "delete")
        assert not hasattr(registry, "remove")
        assert not hasattr(registry, "unregister")

    def test_registry_append_only_no_update(self) -> None:
        """STB-02: No update method exists."""
        registry = BindingRegistry()
        assert not hasattr(registry, "update")
        assert not hasattr(registry, "modify")
        assert not hasattr(registry, "set")


# ==============================================================================
# DriftViolation tests
# ==============================================================================


class TestDriftViolation:
    """Tests for DriftViolation dataclass."""

    def test_drift_violation_fields(self) -> None:
        """DriftViolation has required fields."""
        key_old = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        key_new = ScopedKey(
            entity_id="housing", regime_id="normal", quantity_id="plate_thickness"
        )
        violation = DriftViolation(
            spec_id="SPEC-001",
            param_name="thickness",
            field="entity_id",
            old_value="bracket",
            new_value="housing",
            old_scoped_key=key_old,
            new_scoped_key=key_new,
        )
        assert violation.spec_id == "SPEC-001"
        assert violation.param_name == "thickness"
        assert violation.field == "entity_id"
        assert violation.old_value == "bracket"
        assert violation.new_value == "housing"


# ==============================================================================
# detect_drift tests
# ==============================================================================


class TestDetectDrift:
    """Tests for detect_drift() function."""

    def test_detect_drift_no_changes(self) -> None:
        """STB-03: No drift when bindings unchanged."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        # New spec with same triple
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
                "value": 5.0,  # value doesn't matter for drift
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is False
        assert violations == []

    def test_detect_drift_entity_id_change(self) -> None:
        """STB-03: Drift detected when entity_id changes."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        # LLM tries to change entity_id
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "housing",  # CHANGED
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is True
        assert len(violations) == 1
        assert violations[0].field == "entity_id"
        assert violations[0].old_value == "bracket"
        assert violations[0].new_value == "housing"

    def test_detect_drift_regime_id_change(self) -> None:
        """STB-03: Drift detected when regime_id changes."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "shock",  # CHANGED
                "quantity_id": "plate_thickness",
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is True
        assert len(violations) == 1
        assert violations[0].field == "regime_id"
        assert violations[0].old_value == "normal"
        assert violations[0].new_value == "shock"

    def test_detect_drift_quantity_id_change(self) -> None:
        """STB-03: Drift detected when quantity_id changes."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "normal",
                "quantity_id": "wall_thickness",  # CHANGED
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is True
        assert len(violations) == 1
        assert violations[0].field == "quantity_id"
        assert violations[0].old_value == "plate_thickness"
        assert violations[0].new_value == "wall_thickness"

    def test_detect_drift_value_change_no_drift(self) -> None:
        """STB-04: Value change does NOT cause drift."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
                "value": 10.0,  # Value changed but doesn't matter
                "min_value": 2.0,  # Bounds changed but doesn't matter
                "max_value": 20.0,
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is False
        assert violations == []

    def test_detect_drift_multiple_violations(self) -> None:
        """STB-03: Multiple fields changed -> multiple violations."""
        registry = BindingRegistry()
        key = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key,
            created_by="user",
        )
        # LLM changes both entity and regime
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "housing",  # CHANGED
                "regime_id": "shock",  # CHANGED
                "quantity_id": "plate_thickness",
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is True
        assert len(violations) == 2
        fields = {v.field for v in violations}
        assert fields == {"entity_id", "regime_id"}

    def test_detect_drift_new_spec_no_existing_binding(self) -> None:
        """New spec with no existing binding is not drift."""
        registry = BindingRegistry()
        # No bindings registered
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
            }
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is False
        assert violations == []

    def test_detect_drift_multiple_specs(self) -> None:
        """Drift check across multiple specs."""
        registry = BindingRegistry()
        key1 = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="plate_thickness"
        )
        key2 = ScopedKey(
            entity_id="bracket", regime_id="normal", quantity_id="hole_diameter"
        )
        registry.register(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=key1,
            created_by="user",
        )
        registry.register(
            spec_id="SPEC-002",
            param_name="diameter",
            scoped_key=key2,
            created_by="user",
        )
        # First spec unchanged, second spec drifted
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "bracket",
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
            },
            {
                "spec_id": "SPEC-002",
                "param_name": "diameter",
                "entity_id": "housing",  # CHANGED
                "regime_id": "normal",
                "quantity_id": "hole_diameter",
            },
        ]
        has_drift, violations = detect_drift(registry, new_specs)
        assert has_drift is True
        assert len(violations) == 1
        assert violations[0].spec_id == "SPEC-002"
        assert violations[0].field == "entity_id"
