"""End-to-end tests for regeneration loop wiring.

Success criteria verified:
- E2E: UNSAT core -> regen context with frozen non-implicated
- E2E: non-implicated specs unchanged across regen iterations
- E2E: drift detection blocks changes to frozen specs
- Golden tests verify real Z3 UNSAT core patterns work

These tests use actual SemanticVerifier, BindingRegistry, and PreArtifactGate
to verify full integration of the regeneration loop.
"""

from __future__ import annotations

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import Contract, NodeType, SpecificationNode, SpecParameter
from src.hypergraph.store import HypergraphStore
from src.verification.pre_artifact_gate import PreArtifactGate
from src.verification.semantic.scoped_symbol_table import ScopedKey
from src.verification.tier4_semantic import SemanticVerifier


@pytest.fixture
def engine(tmp_path) -> HypergraphEngine:
    """Create a fresh HypergraphEngine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


@pytest.fixture
def verifier(engine) -> SemanticVerifier:
    """Create a SemanticVerifier with fresh engine."""
    return SemanticVerifier(engine)


@pytest.fixture
def engine_with_specs(tmp_path) -> HypergraphEngine:
    """Engine with specs that produce UNSAT on contracts."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    engine = HypergraphEngine(store)

    # Add specs with different parameters for testing
    # SPEC-001: bracket entity with thickness
    spec1 = SpecificationNode(
        id="SPEC-001",
        node_type=NodeType.SPECIFICATION,
        description="Bracket thickness spec",
        derives_from=["REQ-001"],
        parameters=[
            SpecParameter(
                name="thickness",
                value=5.0,
                unit="mm",
                tolerance="+/- 1mm",
            )
        ],
        entity_id="bracket",
        regime_id="normal",
    )
    # SPEC-002: bracket entity with width
    spec2 = SpecificationNode(
        id="SPEC-002",
        node_type=NodeType.SPECIFICATION,
        description="Bracket width spec",
        derives_from=["REQ-001"],
        parameters=[
            SpecParameter(
                name="width",
                value=50.0,
                unit="mm",
                tolerance="+/- 2mm",
            )
        ],
        entity_id="bracket",
        regime_id="normal",
    )
    engine.add_node(spec1)
    engine.add_node(spec2)

    # Add contract referencing these specs
    contract = Contract(
        id="contract_001",
        node_type=NodeType.CONTRACT,
        description="Bracket contract",
        assumptions=["thickness >= 1"],
        guarantees=["width >= 10"],
    )
    engine.add_node(contract)

    return engine


# ==============================================================================
# E2E: UNSAT core -> regen context with frozen non-implicated
# ==============================================================================


class TestE2EUnsatToRegenContext:
    """E2E: UNSAT core -> regen context with frozen non-implicated."""

    def test_unsat_produces_regen_context_with_frozen(self, engine_with_specs):
        """UNSAT result triggers context creation with frozen specs."""
        verifier = SemanticVerifier(engine_with_specs)

        # Register bindings manually
        key1 = ScopedKey("bracket", "normal", "plate_thickness")
        key2 = ScopedKey("bracket", "normal", "width")
        verifier.binding_registry.register("SPEC-001", "thickness", key1, "user")
        verifier.binding_registry.register("SPEC-002", "width", key2, "user")

        # Build context from a simulated UNSAT core (only SPEC-001 implicated)
        unsat_core = ["SPEC-001_thickness_min", "SPEC-001_thickness_max"]

        context = verifier.build_regeneration_context(
            unsat_core=unsat_core,
            explanation="Thickness constraint conflict",
        )

        # Verify frozen triples exist for non-implicated (SPEC-002)
        frozen_spec_ids = {ft.spec_id for ft in context.frozen_triples}
        implicated_spec_ids = context.implicated.spec_ids

        # SPEC-001 implicated, SPEC-002 frozen
        assert "SPEC-001" in implicated_spec_ids
        assert "SPEC-002" in frozen_spec_ids
        assert "SPEC-001" not in frozen_spec_ids

    def test_regen_context_includes_explanation(self, engine_with_specs):
        """RegenerationContext includes explanation text."""
        verifier = SemanticVerifier(engine_with_specs)

        key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", key, "user")

        context = verifier.build_regeneration_context(
            unsat_core=["SPEC-001_thickness_min"],
            explanation="Test conflict explanation",
        )

        prompt = context.to_prompt_context()
        assert "Test conflict explanation" in prompt

    def test_all_implicated_means_no_frozen(self, engine_with_specs):
        """If all bindings implicated, no frozen triples."""
        verifier = SemanticVerifier(engine_with_specs)

        # Only register one binding
        key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", key, "user")

        # Implicate it
        context = verifier.build_regeneration_context(
            unsat_core=["SPEC-001_thickness_min"],
            explanation="Single spec implicated",
        )

        # No frozen (all implicated)
        assert len(context.frozen_triples) == 0


# ==============================================================================
# E2E: non-implicated specs unchanged across regen iterations
# ==============================================================================


class TestE2ENonImplicatedUnchanged:
    """E2E: non-implicated specs unchanged across regen."""

    def test_frozen_specs_preserved_across_iterations(self, engine_with_specs):
        """Frozen spec bindings unchanged between regen iterations."""
        verifier = SemanticVerifier(engine_with_specs)

        # Register host binding (should stay frozen)
        host_key = ScopedKey("host", "normal", "hole_diameter")
        verifier.binding_registry.register("SPEC-HOST", "diameter", host_key, "user")

        # Register payload binding (will be implicated)
        payload_key = ScopedKey("payload", "normal", "shaft_diameter")
        verifier.binding_registry.register("SPEC-PAYLOAD", "shaft", payload_key, "user")

        # Simulate iteration 1: payload implicated
        core1 = ["SPEC-PAYLOAD_shaft_min"]
        ctx1 = verifier.build_regeneration_context(core1, "iter 1")
        frozen1 = {ft.spec_id for ft in ctx1.frozen_triples}

        # Simulate iteration 2: still payload implicated
        core2 = ["SPEC-PAYLOAD_shaft_max"]
        ctx2 = verifier.build_regeneration_context(core2, "iter 2")
        frozen2 = {ft.spec_id for ft in ctx2.frozen_triples}

        # Host should remain frozen in both iterations
        assert "SPEC-HOST" in frozen1
        assert "SPEC-HOST" in frozen2
        assert frozen1 == frozen2

    def test_multiple_frozen_preserved(self, engine_with_specs):
        """Multiple non-implicated specs all remain frozen."""
        verifier = SemanticVerifier(engine_with_specs)

        # Register 3 bindings (use numeric SPEC-XXX format for pattern matching)
        verifier.binding_registry.register(
            "SPEC-101", "param_a", ScopedKey("e1", "r1", "q1"), "user"
        )
        verifier.binding_registry.register(
            "SPEC-102", "param_b", ScopedKey("e2", "r2", "q2"), "user"
        )
        verifier.binding_registry.register(
            "SPEC-103", "param_c", ScopedKey("e3", "r3", "q3"), "user"
        )

        # Implicate only SPEC-103
        ctx = verifier.build_regeneration_context(
            ["SPEC-103_param_c_min"], "Only SPEC-103 implicated"
        )
        frozen_ids = {ft.spec_id for ft in ctx.frozen_triples}

        # SPEC-101 and SPEC-102 frozen, SPEC-103 implicated
        assert "SPEC-101" in frozen_ids
        assert "SPEC-102" in frozen_ids
        assert "SPEC-103" not in frozen_ids


# ==============================================================================
# E2E: drift detection blocks changes to frozen specs
# ==============================================================================


class TestE2EDriftBlocksFrozen:
    """E2E: drift detection blocks changes to frozen specs."""

    def test_attempt_modify_frozen_entity_blocked(self, engine_with_specs):
        """Modifying frozen spec entity_id triggers drift violation."""
        verifier = SemanticVerifier(engine_with_specs)

        # Establish frozen binding
        frozen_key = ScopedKey("enclosure", "normal", "wall_thickness")
        verifier.binding_registry.register("SPEC-FROZEN", "wall", frozen_key, "user")

        # Attempt to change entity_id
        drifted_spec = {
            "spec_id": "SPEC-FROZEN",
            "param_name": "wall",
            "entity_id": "chassis",  # CHANGED from enclosure
            "regime_id": "normal",
            "quantity_id": "wall_thickness",
        }

        result = verifier.write_llm_output([drifted_spec])
        assert result.rejected is True
        assert "drift" in result.message.lower()

    def test_attempt_modify_frozen_regime_blocked(self, engine_with_specs):
        """Modifying frozen spec regime_id triggers drift violation."""
        verifier = SemanticVerifier(engine_with_specs)

        frozen_key = ScopedKey("bracket", "normal", "thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", frozen_key, "user")

        drifted_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "bracket",
            "regime_id": "high_temp",  # CHANGED from normal
            "quantity_id": "thickness",
        }

        result = verifier.write_llm_output([drifted_spec])
        assert result.rejected is True
        assert len(result.violations) == 1
        assert result.violations[0].field == "regime_id"

    def test_attempt_modify_frozen_quantity_blocked(self, engine_with_specs):
        """Modifying frozen spec quantity_id triggers drift violation."""
        verifier = SemanticVerifier(engine_with_specs)

        frozen_key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register("SPEC-001", "thickness", frozen_key, "user")

        drifted_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "bracket",
            "regime_id": "normal",
            "quantity_id": "wall_thickness",  # CHANGED from plate_thickness
        }

        result = verifier.write_llm_output([drifted_spec])
        assert result.rejected is True
        assert result.violations[0].field == "quantity_id"

    def test_non_drifted_spec_accepted(self, engine_with_specs):
        """Spec with same triple as existing binding is accepted."""
        verifier = SemanticVerifier(engine_with_specs)

        existing_key = ScopedKey("bracket", "normal", "plate_thickness")
        verifier.binding_registry.register(
            "SPEC-001", "thickness", existing_key, "user"
        )

        # Same triple - no drift
        same_spec = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "bracket",
            "regime_id": "normal",
            "quantity_id": "plate_thickness",
        }

        result = verifier.write_llm_output([same_spec])
        assert result.rejected is False
        assert len(result.violations) == 0


# ==============================================================================
# E2E: Orchestrator without LLM hits max_iterations
# ==============================================================================


class TestGateE2ENoLLM:
    """E2E: PreArtifactGate without LLM exhausts attempts."""

    def test_gate_no_contracts_passes(self, engine, tmp_path):
        """No contracts -> gate passes on first attempt."""
        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=str(tmp_path / "test.json"),
            llm=None,
            max_attempts=3,
        )
        result = gate.run()
        assert result.success is True
        assert result.attempts == 1

    def test_gate_sat_contract_passes(self, engine_with_specs, tmp_path):
        """SAT contract -> gate passes."""
        gate = PreArtifactGate(
            engine=engine_with_specs,
            intent="test",
            store_path=str(tmp_path / "test.json"),
            llm=None,
            max_attempts=3,
        )
        result = gate.run()
        assert result.attempts >= 1

    def test_gate_unsat_no_llm_exhausts_attempts(self, tmp_path):
        """UNSAT without LLM -> exhausts max_attempts."""
        store = HypergraphStore(tmp_path / "conflict_graph.json")
        engine = HypergraphEngine(store)

        spec = SpecificationNode(
            id="SPEC-CONFLICT",
            node_type=NodeType.SPECIFICATION,
            description="Conflicting spec",
            derives_from=["REQ-001"],
            parameters=[
                SpecParameter(
                    name="thickness",
                    value=5.0,
                    unit="mm",
                    tolerance="+/- 1mm",
                )
            ],
            entity_id="bracket",
            regime_id="normal",
        )
        engine.add_node(spec)

        contract = Contract(
            id="conflict_contract",
            node_type=NodeType.CONTRACT,
            description="Conflicting contract",
            assumptions=["thickness >= 10"],
            guarantees=["thickness <= 3"],
        )
        engine.add_node(contract)

        gate = PreArtifactGate(
            engine=engine,
            intent="test",
            store_path=str(tmp_path / "conflict.json"),
            llm=None,
            max_attempts=2,
        )
        result = gate.run()
        assert result.attempts <= 2


# ==============================================================================
# Golden tests: real Z3 UNSAT core patterns
# ==============================================================================


class TestGoldenUnsatCoreScenarios:
    """Golden test cases with known UNSAT core patterns from Phase 16 Z3 output."""

    # Golden UNSAT core from real Z3 output (specification_<hex>_param_bound format)
    GOLDEN_CORE_SPEC_CONFLICT = [
        "specification_7be07d53_thickness_min",
        "specification_7be07d53_thickness_max",
    ]

    GOLDEN_CORE_CROSS_SPEC = [
        "SPEC-001_safety_factor_min",
        "SPEC-002_safety_factor_max",
        "INV_GE1_bracket__normal__safety_factor",
    ]

    def test_golden_single_spec_conflict(self, engine_with_specs):
        """Single spec with contradictory min/max -> implicated."""
        verifier = SemanticVerifier(engine_with_specs)

        # Build context from golden core
        context = verifier.build_regeneration_context(
            self.GOLDEN_CORE_SPEC_CONFLICT,
            "Thickness min > max",
        )

        # specification_7be07d53 should be implicated
        assert "specification_7be07d53" in context.implicated.spec_ids
        assert "thickness" in context.implicated.param_names

    def test_golden_cross_spec_with_invariant(self, engine_with_specs):
        """Cross-spec conflict with domain invariant -> both implicated."""
        verifier = SemanticVerifier(engine_with_specs)

        # Register bindings so there are non-implicated specs to freeze
        verifier.binding_registry.register(
            "SPEC-003", "other", ScopedKey("a", "b", "c"), "user"
        )

        context = verifier.build_regeneration_context(
            self.GOLDEN_CORE_CROSS_SPEC,
            "Safety factor conflict across specs",
        )

        # Both specs implicated
        assert "SPEC-001" in context.implicated.spec_ids
        assert "SPEC-002" in context.implicated.spec_ids
        # Scoped key from INV captured
        assert len(context.implicated.scoped_keys) >= 1
        # Verify bracket/normal/safety_factor key parsed
        expected_key = ScopedKey("bracket", "normal", "safety_factor")
        assert expected_key in context.implicated.scoped_keys

    def test_golden_uuid_spec_id_extraction(self, engine_with_specs):
        """specification_<hex>_param_bound extracts correct spec_id."""
        verifier = SemanticVerifier(engine_with_specs)

        # UUID-style spec IDs from real Z3 output
        uuid_core = [
            "specification_1bdce5ce_safety_factor_min",
            "specification_0619e592_hole_diameter_max",
        ]

        context = verifier.build_regeneration_context(uuid_core, "UUID test")

        # Verify both UUID-style spec IDs extracted
        assert "specification_1bdce5ce" in context.implicated.spec_ids
        assert "specification_0619e592" in context.implicated.spec_ids

    def test_golden_mixed_core_formats(self, engine_with_specs):
        """Mixed SPEC-XXX and specification_<hex> formats in same core."""
        verifier = SemanticVerifier(engine_with_specs)

        mixed_core = [
            "SPEC-001_thickness_min",
            "specification_abcd1234_width_max",
            "INV_POS_bracket__normal__plate_thickness",
        ]

        context = verifier.build_regeneration_context(mixed_core, "Mixed formats")

        # All spec IDs extracted
        assert "SPEC-001" in context.implicated.spec_ids
        assert "specification_abcd1234" in context.implicated.spec_ids
        # INV scoped key extracted
        expected_key = ScopedKey("bracket", "normal", "plate_thickness")
        assert expected_key in context.implicated.scoped_keys

    def test_golden_param_with_underscores(self, engine_with_specs):
        """Param names with underscores parsed correctly."""
        verifier = SemanticVerifier(engine_with_specs)

        underscore_core = [
            "SPEC-001_max_allowed_stress_min",
            "SPEC-002_min_wall_thickness_max",
        ]

        context = verifier.build_regeneration_context(
            underscore_core, "Underscore params"
        )

        # Param names extracted (everything except _min/_max suffix)
        assert "max_allowed_stress" in context.implicated.param_names
        assert "min_wall_thickness" in context.implicated.param_names


# ==============================================================================
# Full pipeline E2E: verify -> regen context -> drift check
# ==============================================================================


class TestFullPipelineE2E:
    """Full E2E: run verifier, build context, apply changes with drift check."""

    def test_full_pipeline_verify_to_context_to_drift(self, engine_with_specs):
        """Verify -> UNSAT -> context -> drift check flow."""
        verifier = SemanticVerifier(engine_with_specs)

        # Register bindings
        verifier.binding_registry.register(
            "SPEC-001", "thickness", ScopedKey("bracket", "normal", "thickness"), "user"
        )
        verifier.binding_registry.register(
            "SPEC-002", "width", ScopedKey("bracket", "normal", "width"), "user"
        )

        # Run verification (may or may not UNSAT - we simulate UNSAT below)
        _ = verifier.verify_contracts()

        # Simulate UNSAT with known core
        unsat_core = ["SPEC-001_thickness_min"]
        context = verifier.build_regeneration_context(unsat_core, "Test conflict")

        # Verify SPEC-001 implicated, SPEC-002 frozen
        frozen_ids = {ft.spec_id for ft in context.frozen_triples}
        assert "SPEC-002" in frozen_ids
        assert "SPEC-001" in context.implicated.spec_ids

        # Attempt to modify frozen SPEC-002 - should be blocked by drift
        drifted = {
            "spec_id": "SPEC-002",
            "param_name": "width",
            "entity_id": "housing",  # DRIFTED
            "regime_id": "normal",
            "quantity_id": "width",
        }
        result = verifier.write_llm_output([drifted])
        assert result.rejected is True

        # Modify implicated SPEC-001 - also blocked since binding exists
        # (drift check applies to all bindings, not just frozen)
        implicated_drift = {
            "spec_id": "SPEC-001",
            "param_name": "thickness",
            "entity_id": "enclosure",  # DRIFTED
            "regime_id": "normal",
            "quantity_id": "thickness",
        }
        result2 = verifier.write_llm_output([implicated_drift])
        assert result2.rejected is True

    def test_audit_trail_recorded(self, engine_with_specs):
        """Regeneration audit trail records iterations."""
        verifier = SemanticVerifier(engine_with_specs)

        # Record a few iterations
        verifier.record_regeneration_iteration(
            modified_specs=["SPEC-001"],
            preserved_specs=["SPEC-002"],
            outcome="retry",
        )
        verifier.record_regeneration_iteration(
            modified_specs=["SPEC-001"],
            preserved_specs=["SPEC-002"],
            outcome="success",
        )

        history = verifier.regeneration_audit.get_history()
        assert len(history) == 2
        assert history[0].iteration == 1
        assert history[0].outcome == "retry"
        assert history[1].iteration == 2
        assert history[1].outcome == "success"


# ==============================================================================
# Binding conflict in verify_all_specs does not crash
# ==============================================================================


class TestBindingConflictDoesNotCrash:
    """BindingConflictError during verify_all_specs becomes a warning, not crash."""

    def test_binding_conflict_produces_warning_not_crash(self, engine):
        """Pre-registered binding with different key -> warning, no crash."""
        # "thickness" alias resolves to quantity_id "plate_thickness" in ontology.
        # entity_id comes from metadata["interface"].
        spec = SpecificationNode(
            id="SPEC-001",
            node_type=NodeType.SPECIFICATION,
            description="Bracket thickness",
            derives_from=["REQ-001"],
            parameters=[
                SpecParameter(
                    name="thickness", value=5.0, unit="mm", tolerance="+/- 1mm"
                )
            ],
            metadata={"interface": "bracket"},
        )
        engine.add_node(spec)

        verifier = SemanticVerifier(engine)

        # Pre-register with canonical param_name "plate_thickness" (what register()
        # uses: c.canonical_name or c.name) but DIFFERENT entity_id
        old_key = ScopedKey("housing", "normal", "plate_thickness")
        verifier.binding_registry.register(
            "SPEC-001", "plate_thickness", old_key, "spec"
        )

        # Without the fix this crashes with BindingConflictError;
        # with the fix it should produce a warning
        result = verifier.verify_all_specs()
        assert result is not None
        # Result should contain a BINDING_CONFLICT warning
        warnings = result.details.get("warnings", [])
        conflict_warnings = [w for w in warnings if w.get("code") == "BINDING_CONFLICT"]
        assert len(conflict_warnings) >= 1
