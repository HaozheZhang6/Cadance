"""Integration tests for stability/regeneration wired into pipeline.

Tests:
- BindingRegistry created at pipeline/verifier start
- detect_drift called before accepting LLM output
- Drift violations block regeneration
- Non-implicated params frozen during regen
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.store import HypergraphStore
from src.verification.semantic.constraint_extractor import Constraint
from src.verification.semantic.regeneration import (
    RegenerationAudit,
    RegenerationContext,
)
from src.verification.semantic.scoped_symbol_table import ScopedKey
from src.verification.semantic.stability import (
    BindingRegistry,
)
from src.verification.semantic.vacuity_audit import audit_vacuity
from src.verification.tier4_semantic import SemanticVerifier

if TYPE_CHECKING:
    pass


@pytest.fixture
def engine(tmp_path) -> HypergraphEngine:
    """Create a fresh HypergraphEngine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


@pytest.fixture
def verifier(engine) -> SemanticVerifier:
    """Create a SemanticVerifier with fresh engine."""
    return SemanticVerifier(engine)


# ==============================================================================
# BindingRegistry instantiation at pipeline start
# ==============================================================================


class TestRegistryAtPipelineStart:
    """Tests for BindingRegistry created at pipeline/verifier start."""

    def test_semantic_verifier_has_binding_registry(self, verifier) -> None:
        """SemanticVerifier has a BindingRegistry instance."""
        assert hasattr(verifier, "binding_registry")
        assert isinstance(verifier.binding_registry, BindingRegistry)

    def test_binding_registry_initially_empty(self, verifier) -> None:
        """BindingRegistry starts empty."""
        assert len(verifier.binding_registry.all_bindings()) == 0


# ==============================================================================
# Drift detection before accepting LLM output
# ==============================================================================


class TestDriftDetectionInPipeline:
    """Tests for drift detection before node writes."""

    def test_check_drift_method_exists(self, verifier) -> None:
        """SemanticVerifier has check_drift method."""
        assert hasattr(verifier, "check_drift")
        assert callable(verifier.check_drift)

    def test_check_drift_returns_violations(self, verifier) -> None:
        """check_drift returns (has_drift, violations) tuple."""
        # Register a binding
        key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", key, "user")

        # Check with changed entity_id
        new_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "thickness",
                "entity_id": "housing",  # CHANGED
                "regime_id": "normal",
                "quantity_id": "plate_thickness",
            }
        ]
        has_drift, violations = verifier.check_drift(new_specs)
        assert has_drift is True
        assert len(violations) == 1
        assert violations[0].field == "entity_id"

    def test_drift_blocks_node_write(self, verifier) -> None:
        """Drift violations prevent node from being written."""
        # Register binding for SPEC-001
        key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", key, "user")

        # Try to write spec with drifted binding
        drifted_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "housing",  # DRIFTED
            "regime_id": "normal",
            "quantity_id": "plate_thickness",
        }

        # write_llm_output should reject
        result = verifier.write_llm_output([drifted_spec])
        assert result.rejected is True
        assert "drift" in result.message.lower()


# ==============================================================================
# Drift violations block regeneration
# ==============================================================================


class TestDriftBlocksRegeneration:
    """Tests for drift blocking regeneration."""

    def test_regeneration_blocked_on_drift(self, verifier) -> None:
        """Regeneration attempt blocked when drift detected."""
        # Establish host binding
        host_key = ScopedKey("host", "normal", "hole_diameter")
        verifier.binding_registry.register("SPEC-001", "diameter", host_key, "user")

        # Payload binding
        payload_key = ScopedKey("payload", "normal", "shaft_diameter")
        verifier.binding_registry.register("SPEC-002", "shaft", payload_key, "user")

        # Regen tries to change host entity_id
        regen_specs = [
            {
                "spec_id": "SPEC-001",
                "param_name": "diameter",
                "entity_id": "enclosure",  # CHANGED from host
                "regime_id": "normal",
                "quantity_id": "hole_diameter",
            },
            {
                "spec_id": "SPEC-002",
                "param_name": "shaft",
                "entity_id": "payload",
                "regime_id": "normal",
                "quantity_id": "shaft_diameter",
            },
        ]

        has_drift, violations = verifier.check_drift(regen_specs)
        assert has_drift is True
        # SPEC-001 drifted
        spec_ids_drifted = {v.spec_id for v in violations}
        assert "SPEC-001" in spec_ids_drifted
        assert "SPEC-002" not in spec_ids_drifted


# ==============================================================================
# Non-implicated params frozen during regen
# ==============================================================================


class TestFrozenParamsDuringRegen:
    """Tests for non-implicated bindings frozen during regeneration."""

    def test_build_regen_context_from_verifier(self, verifier) -> None:
        """Verifier builds RegenerationContext with frozen non-implicated."""
        # Register bindings
        host_key = ScopedKey("host", "normal", "hole_diameter")
        payload_key = ScopedKey("payload", "normal", "shaft_diameter")
        verifier.binding_registry.register("SPEC-001", "diameter", host_key, "user")
        verifier.binding_registry.register("SPEC-002", "shaft", payload_key, "user")

        # UNSAT core implicates only payload
        unsat_core = ["SPEC-002_shaft_min", "SPEC-002_shaft_max"]

        # Build context
        context = verifier.build_regeneration_context(
            unsat_core=unsat_core,
            explanation="Payload shaft too large for hole",
        )

        assert isinstance(context, RegenerationContext)
        # SPEC-002 implicated, SPEC-001 frozen
        frozen_spec_ids = {ft.spec_id for ft in context.frozen_triples}
        assert "SPEC-001" in frozen_spec_ids
        assert "SPEC-002" not in frozen_spec_ids

    def test_frozen_bindings_unchanged_across_iterations(self, verifier) -> None:
        """Non-implicated bindings remain frozen across regen iterations."""
        # Register bindings
        host_key = ScopedKey("host", "normal", "hole_diameter")
        payload_key = ScopedKey("payload", "normal", "shaft_diameter")
        verifier.binding_registry.register("SPEC-001", "diameter", host_key, "user")
        verifier.binding_registry.register("SPEC-002", "shaft", payload_key, "user")

        # Iteration 1: SPEC-002 implicated
        unsat_core1 = ["SPEC-002_shaft_min"]
        ctx1 = verifier.build_regeneration_context(unsat_core1, "iter 1")
        frozen1 = {ft.spec_id for ft in ctx1.frozen_triples}
        assert "SPEC-001" in frozen1

        # Iteration 2: still only SPEC-002 implicated
        unsat_core2 = ["SPEC-002_shaft_max"]
        ctx2 = verifier.build_regeneration_context(unsat_core2, "iter 2")
        frozen2 = {ft.spec_id for ft in ctx2.frozen_triples}
        assert "SPEC-001" in frozen2

        # Host stays frozen
        assert frozen1 == frozen2


# ==============================================================================
# Audit trail for multi-iteration regen
# ==============================================================================


class TestRegenerationAuditTrail:
    """Tests for audit trail during multi-iteration regeneration."""

    def test_verifier_has_regeneration_audit(self, verifier) -> None:
        """SemanticVerifier has a RegenerationAudit instance."""
        assert hasattr(verifier, "regeneration_audit")
        assert isinstance(verifier.regeneration_audit, RegenerationAudit)

    def test_audit_records_iteration(self, verifier) -> None:
        """Audit records each regeneration iteration."""
        # Record iteration
        verifier.record_regeneration_iteration(
            modified_specs=["SPEC-002"],
            preserved_specs=["SPEC-001"],
            outcome="retry",
        )

        history = verifier.regeneration_audit.get_history()
        assert len(history) == 1
        assert history[0].modified_specs == ["SPEC-002"]
        assert history[0].preserved_specs == ["SPEC-001"]

    def test_multi_iteration_audit_trail(self, verifier) -> None:
        """Multiple iterations create audit trail."""
        # 3 iterations
        for i in range(3):
            outcome = "retry" if i < 2 else "success"
            verifier.record_regeneration_iteration(
                modified_specs=[f"SPEC-00{i + 1}"],
                preserved_specs=["SPEC-010"],
                outcome=outcome,
            )

        history = verifier.regeneration_audit.get_history()
        assert len(history) == 3
        assert history[0].iteration == 1
        assert history[1].iteration == 2
        assert history[2].iteration == 3
        assert history[2].outcome == "success"

    def test_audit_to_prompt_context(self, verifier) -> None:
        """Audit can be serialized for prompt context."""
        verifier.record_regeneration_iteration(
            modified_specs=["SPEC-001"],
            preserved_specs=[],
            outcome="retry",
        )

        json_str = verifier.regeneration_audit.to_json()
        assert "SPEC-001" in json_str
        assert "retry" in json_str


# ==============================================================================
# End-to-end drift detection test
# ==============================================================================


class TestE2EDriftDetection:
    """End-to-end test: run A, regen with changed entity_id -> drift caught."""

    def test_e2e_regen_with_entity_drift_rejected(self, verifier) -> None:
        """Full scenario: initial run, then regen with drifted entity_id is rejected."""
        # Run A: establish bindings
        initial_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "bracket",
            "regime_id": "normal",
            "quantity_id": "plate_thickness",
        }
        verifier.register_binding_from_spec(initial_spec, created_by="contract")

        # Verify binding established
        binding = verifier.binding_registry.get("SPEC-001", "thickness")
        assert binding is not None
        assert binding.scoped_key.entity_id == "bracket"

        # Regen attempt with changed entity_id
        regen_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "housing",  # DRIFTED
            "regime_id": "normal",
            "quantity_id": "plate_thickness",
        }

        has_drift, violations = verifier.check_drift([regen_spec])
        assert has_drift is True
        assert violations[0].old_value == "bracket"
        assert violations[0].new_value == "housing"


# ==============================================================================
# UNSAT implicates payload only -> host bindings unchanged
# ==============================================================================


class TestUNSATImplicatesPayloadOnly:
    """UNSAT implicates payload only -> host bindings unchanged."""

    def test_unsat_payload_host_frozen(self, verifier) -> None:
        """When UNSAT only implicates payload, host bindings stay frozen."""
        # Host and payload bindings (use numeric spec IDs for pattern matching)
        host_key = ScopedKey("host", "normal", "hole_diameter")
        payload_key = ScopedKey("payload", "normal", "shaft_diameter")
        verifier.binding_registry.register("SPEC-001", "diameter", host_key, "user")
        verifier.binding_registry.register("SPEC-002", "shaft", payload_key, "user")

        # UNSAT core only mentions payload (SPEC-002)
        unsat_core = [
            "SPEC-002_shaft_min",
            "INV_POS_payload__normal__shaft_diameter",
        ]

        context = verifier.build_regeneration_context(
            unsat_core=unsat_core,
            explanation="Payload shaft violates positivity",
        )

        # Host should be frozen
        frozen_spec_ids = {ft.spec_id for ft in context.frozen_triples}
        assert "SPEC-001" in frozen_spec_ids
        # Payload implicated
        assert "SPEC-002" in context.implicated.spec_ids
        assert "SPEC-002" not in frozen_spec_ids


# ==============================================================================
# derived_sources reduce vacuity warnings
# ==============================================================================


class TestDerivedSourcesReduceVacuity:
    """derived_sources from derived constraints suppress vacuity for factor vars."""

    def test_derived_sources_reduce_vacuity(self) -> None:
        """Contract F = m * g, spec constrains F, m, g once each → no vacuity for m, g."""
        key_f = ScopedKey("system", "normal", "static_force")
        key_m = ScopedKey("system", "normal", "payload_mass")
        key_g = ScopedKey("system", "normal", "gravity")

        c_f = Constraint(
            name="SPEC-001_static_force_min",
            min_name="SPEC-001_static_force_min",
            max_name="SPEC-001_static_force_max",
            min_value=40.0,
            max_value=60.0,
            canonical_unit="N",
            is_equality=False,
            canonical_name="static_force",
            scoped_key=key_f,
        )
        c_m = Constraint(
            name="SPEC-002_payload_mass_min",
            min_name="SPEC-002_payload_mass_min",
            max_name="SPEC-002_payload_mass_max",
            min_value=4.5,
            max_value=5.5,
            canonical_unit="kg",
            is_equality=False,
            canonical_name="payload_mass",
            scoped_key=key_m,
        )
        c_g = Constraint(
            name="SPEC-003_gravity_min",
            min_name="SPEC-003_gravity_min",
            max_name="SPEC-003_gravity_max",
            exact_value=9.81,
            canonical_unit="m/s^2",
            is_equality=True,
            canonical_name="gravity",
            scoped_key=key_g,
        )

        constraints = [c_f, c_m, c_g]

        # Without derived_sources: m and g each appear once → vacuity
        report_no_ds = audit_vacuity(constraints, registry=None)
        vacuous_names = {u.var_name for u in report_no_ds.unconstrained}
        assert (
            key_m.to_z3_name() in vacuous_names or key_g.to_z3_name() in vacuous_names
        )

        # With derived_sources marking m and g as factors
        derived_sources = {
            key_m.to_z3_name(),
            key_g.to_z3_name(),
        }
        report_ds = audit_vacuity(
            constraints, registry=None, derived_sources=derived_sources
        )
        vacuous_names_ds = {u.var_name for u in report_ds.unconstrained}
        assert key_m.to_z3_name() not in vacuous_names_ds
        assert key_g.to_z3_name() not in vacuous_names_ds
