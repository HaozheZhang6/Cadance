"""Tests for regeneration module.

RGN-01: extract_implicated_nodes parses UNSAT core to spec_ids
RGN-02: build_regeneration_context freezes non-implicated bindings
RGN-03: RegenerationAudit tracks modified vs preserved
RGN-04: to_prompt_context formats for LLM
"""

from datetime import datetime

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import Contract, NodeType, SpecificationNode
from src.hypergraph.store import HypergraphStore
from src.verification.semantic.regeneration import (
    FrozenTriple,
    ImplicatedNodeSet,
    RegenerationAudit,
    RegenerationAuditEntry,
    RegenerationContext,
    build_regeneration_context,
    extract_implicated_nodes,
    resolve_core_to_nodes,
)
from src.verification.semantic.scoped_symbol_table import ScopedKey
from src.verification.semantic.stability import BindingRegistry


class TestImplicatedNodeSet:
    """Tests for ImplicatedNodeSet dataclass."""

    def test_empty_implicated_set(self):
        """Empty set has no spec_ids or constraint_names."""
        implicated = ImplicatedNodeSet(
            spec_ids=set(),
            param_names=set(),
            scoped_keys=set(),
            constraint_names=[],
            failure_type="unsat",
        )
        assert len(implicated.spec_ids) == 0
        assert len(implicated.constraint_names) == 0

    def test_implicated_set_with_specs(self):
        """ImplicatedNodeSet holds spec_ids correctly."""
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001", "SPEC-002"},
            param_names={"thickness", "width"},
            scoped_keys={
                ScopedKey("bracket", "normal", "plate_thickness"),
            },
            constraint_names=["SPEC-001_thickness_min", "SPEC-002_width_max"],
            failure_type="unsat",
        )
        assert "SPEC-001" in implicated.spec_ids
        assert "SPEC-002" in implicated.spec_ids
        assert "thickness" in implicated.param_names

    def test_implicated_set_frozen_key(self):
        """ScopedKeys in implicated set are hashable."""
        key = ScopedKey("bracket", "normal", "plate_thickness")
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names={"thickness"},
            scoped_keys={key},
            constraint_names=["SPEC-001_thickness_min"],
            failure_type="unsat",
        )
        assert key in implicated.scoped_keys


class TestExtractImplicatedNodes:
    """Tests for extract_implicated_nodes function (RGN-01)."""

    def test_empty_unsat_core(self):
        """Empty core -> empty ImplicatedNodeSet."""
        result = extract_implicated_nodes([])
        assert len(result.spec_ids) == 0
        assert len(result.constraint_names) == 0

    def test_single_spec_constraint(self):
        """SPEC-001_thickness_min -> spec_ids={SPEC-001}."""
        result = extract_implicated_nodes(["SPEC-001_thickness_min"])
        assert "SPEC-001" in result.spec_ids
        assert "SPEC-001_thickness_min" in result.constraint_names

    def test_multiple_specs(self):
        """Multiple constraints -> multiple spec_ids."""
        result = extract_implicated_nodes(
            [
                "SPEC-001_thickness_min",
                "SPEC-002_width_max",
                "SPEC-003_length_exact",
            ]
        )
        assert result.spec_ids == {"SPEC-001", "SPEC-002", "SPEC-003"}
        assert len(result.constraint_names) == 3

    def test_invariant_constraint_parsing(self):
        """INV_POS_bracket__normal__plate_thickness -> parses scoped_key."""
        result = extract_implicated_nodes(["INV_POS_bracket__normal__plate_thickness"])
        expected_key = ScopedKey("bracket", "normal", "plate_thickness")
        assert expected_key in result.scoped_keys
        # INV constraints don't have spec_id
        assert len(result.spec_ids) == 0

    def test_invariant_nonneg_parsing(self):
        """INV_NONNEG_* also parsed."""
        result = extract_implicated_nodes(["INV_NONNEG_housing__static__clearance"])
        expected_key = ScopedKey("housing", "static", "clearance")
        assert expected_key in result.scoped_keys

    def test_invariant_ge1_parsing(self):
        """INV_GE1_* parsed correctly."""
        result = extract_implicated_nodes(["INV_GE1_bracket__normal__safety_factor"])
        expected_key = ScopedKey("bracket", "normal", "safety_factor")
        assert expected_key in result.scoped_keys

    def test_mixed_constraints(self):
        """Mixed SPEC and INV constraints."""
        result = extract_implicated_nodes(
            [
                "SPEC-001_thickness_min",
                "INV_POS_bracket__normal__plate_thickness",
                "SPEC-002_safety_factor_min",
            ]
        )
        assert result.spec_ids == {"SPEC-001", "SPEC-002"}
        assert ScopedKey("bracket", "normal", "plate_thickness") in result.scoped_keys

    def test_identity_errors_input(self):
        """Identity errors add to implicated set."""
        identity_errors = [
            {
                "spec_id": "SPEC-005",
                "param_name": "weight",
                "error": "missing_entity_id",
            }
        ]
        result = extract_implicated_nodes([], identity_errors=identity_errors)
        assert "SPEC-005" in result.spec_ids
        assert "weight" in result.param_names
        assert result.failure_type == "identity"


class TestFrozenTriple:
    """Tests for FrozenTriple dataclass."""

    def test_frozen_triple_min_max(self):
        """FrozenTriple with min/max bounds."""
        frozen = FrozenTriple(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            min_value=2.0,
            max_value=5.0,
            exact_value=None,
        )
        assert frozen.min_value == 2.0
        assert frozen.max_value == 5.0
        assert frozen.exact_value is None

    def test_frozen_triple_exact(self):
        """FrozenTriple with exact value."""
        frozen = FrozenTriple(
            spec_id="SPEC-002",
            param_name="count",
            scoped_key=ScopedKey("bracket", "normal", "hole_count"),
            min_value=None,
            max_value=None,
            exact_value=4,
        )
        assert frozen.exact_value == 4
        assert frozen.min_value is None

    def test_frozen_triple_hashable(self):
        """FrozenTriple is frozen (hashable)."""
        frozen = FrozenTriple(
            spec_id="SPEC-001",
            param_name="thickness",
            scoped_key=ScopedKey("bracket", "normal", "plate_thickness"),
            min_value=2.0,
            max_value=5.0,
            exact_value=None,
        )
        # Should be usable in set
        frozen_set = {frozen}
        assert frozen in frozen_set


class TestBuildRegenerationContext:
    """Tests for build_regeneration_context function (RGN-02)."""

    def test_freezes_non_implicated_bindings(self):
        """Bindings NOT in implicated set become frozen."""
        registry = BindingRegistry()
        key1 = ScopedKey("bracket", "normal", "plate_thickness")
        key2 = ScopedKey("bracket", "normal", "width")
        registry.register("SPEC-001", "thickness", key1, "user")
        registry.register("SPEC-002", "width", key2, "user")

        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names={"thickness"},
            scoped_keys={key1},
            constraint_names=["SPEC-001_thickness_min"],
            failure_type="unsat",
        )

        context = build_regeneration_context(registry, implicated)
        # SPEC-002 should be frozen (not implicated)
        frozen_spec_ids = {ft.spec_id for ft in context.frozen_triples}
        assert "SPEC-002" in frozen_spec_ids
        assert "SPEC-001" not in frozen_spec_ids

    def test_all_implicated_means_no_frozen(self):
        """If all bindings implicated, no frozen triples."""
        registry = BindingRegistry()
        key1 = ScopedKey("bracket", "normal", "plate_thickness")
        registry.register("SPEC-001", "thickness", key1, "user")

        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names={"thickness"},
            scoped_keys={key1},
            constraint_names=["SPEC-001_thickness_min"],
            failure_type="unsat",
        )

        context = build_regeneration_context(registry, implicated)
        assert len(context.frozen_triples) == 0

    def test_empty_registry_empty_frozen(self):
        """Empty registry -> empty frozen triples."""
        registry = BindingRegistry()
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names=set(),
            scoped_keys=set(),
            constraint_names=[],
            failure_type="unsat",
        )
        context = build_regeneration_context(registry, implicated)
        assert len(context.frozen_triples) == 0


class TestRegenerationContext:
    """Tests for RegenerationContext dataclass (RGN-04)."""

    def test_to_prompt_context_includes_may_modify(self):
        """to_prompt_context includes MAY modify section."""
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names={"thickness"},
            scoped_keys={ScopedKey("bracket", "normal", "plate_thickness")},
            constraint_names=["SPEC-001_thickness_min"],
            failure_type="unsat",
        )
        context = RegenerationContext(
            implicated=implicated,
            frozen_triples=[],
            frozen_couplings=[],
            unsat_core_explanation="Thickness constraint conflict",
        )
        prompt = context.to_prompt_context()
        assert "MAY modify" in prompt or "may modify" in prompt.lower()
        assert "SPEC-001" in prompt

    def test_to_prompt_context_includes_must_not_modify(self):
        """to_prompt_context includes MUST NOT modify section when frozen exists."""
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names={"thickness"},
            scoped_keys={ScopedKey("bracket", "normal", "plate_thickness")},
            constraint_names=["SPEC-001_thickness_min"],
            failure_type="unsat",
        )
        frozen = FrozenTriple(
            spec_id="SPEC-002",
            param_name="width",
            scoped_key=ScopedKey("bracket", "normal", "width"),
            min_value=10.0,
            max_value=20.0,
            exact_value=None,
        )
        context = RegenerationContext(
            implicated=implicated,
            frozen_triples=[frozen],
            frozen_couplings=[],
            unsat_core_explanation="Thickness conflict",
        )
        prompt = context.to_prompt_context()
        assert "MUST NOT modify" in prompt or "must not modify" in prompt.lower()
        assert "SPEC-002" in prompt

    def test_to_prompt_context_includes_explanation(self):
        """to_prompt_context includes UNSAT core explanation."""
        implicated = ImplicatedNodeSet(
            spec_ids={"SPEC-001"},
            param_names=set(),
            scoped_keys=set(),
            constraint_names=[],
            failure_type="unsat",
        )
        context = RegenerationContext(
            implicated=implicated,
            frozen_triples=[],
            frozen_couplings=[],
            unsat_core_explanation="Conflicting min/max bounds",
        )
        prompt = context.to_prompt_context()
        assert "Conflicting min/max bounds" in prompt


class TestRegenerationAuditEntry:
    """Tests for RegenerationAuditEntry dataclass (RGN-03)."""

    def test_audit_entry_creation(self):
        """AuditEntry stores iteration data."""
        entry = RegenerationAuditEntry(
            timestamp=datetime.now(),
            iteration=1,
            modified_specs=["SPEC-001"],
            preserved_specs=["SPEC-002", "SPEC-003"],
            outcome="retry",
        )
        assert entry.iteration == 1
        assert "SPEC-001" in entry.modified_specs
        assert len(entry.preserved_specs) == 2

    def test_audit_entry_to_dict(self):
        """to_dict serializes correctly."""
        ts = datetime(2026, 2, 4, 12, 0, 0)
        entry = RegenerationAuditEntry(
            timestamp=ts,
            iteration=2,
            modified_specs=["SPEC-001"],
            preserved_specs=["SPEC-002"],
            outcome="success",
        )
        d = entry.to_dict()
        assert d["iteration"] == 2
        assert d["outcome"] == "success"
        assert "timestamp" in d
        assert d["modified_specs"] == ["SPEC-001"]


class TestRegenerationAudit:
    """Tests for RegenerationAudit class (RGN-03)."""

    def test_record_stores_entry(self):
        """record() stores entry in history."""
        audit = RegenerationAudit()
        entry = RegenerationAuditEntry(
            timestamp=datetime.now(),
            iteration=1,
            modified_specs=["SPEC-001"],
            preserved_specs=["SPEC-002"],
            outcome="retry",
        )
        audit.record(entry)
        assert len(audit.get_history()) == 1

    def test_multiple_records(self):
        """Multiple records preserved in order."""
        audit = RegenerationAudit()
        for i in range(3):
            entry = RegenerationAuditEntry(
                timestamp=datetime.now(),
                iteration=i + 1,
                modified_specs=[f"SPEC-{i:03d}"],
                preserved_specs=[],
                outcome="retry" if i < 2 else "success",
            )
            audit.record(entry)
        history = audit.get_history()
        assert len(history) == 3
        assert history[0].iteration == 1
        assert history[2].iteration == 3
        assert history[2].outcome == "success"

    def test_get_history_by_spec(self):
        """Filter history by spec_id."""
        audit = RegenerationAudit()
        audit.record(
            RegenerationAuditEntry(
                timestamp=datetime.now(),
                iteration=1,
                modified_specs=["SPEC-001"],
                preserved_specs=["SPEC-002"],
                outcome="retry",
            )
        )
        audit.record(
            RegenerationAuditEntry(
                timestamp=datetime.now(),
                iteration=2,
                modified_specs=["SPEC-002"],
                preserved_specs=["SPEC-001"],
                outcome="success",
            )
        )

        spec001_history = audit.get_history_by_spec("SPEC-001")
        assert (
            len(spec001_history) == 2
        )  # Appears in both (modified in 1, preserved in 2)

    def test_to_json(self):
        """to_json serializes full audit."""
        audit = RegenerationAudit()
        audit.record(
            RegenerationAuditEntry(
                timestamp=datetime(2026, 2, 4, 12, 0, 0),
                iteration=1,
                modified_specs=["SPEC-001"],
                preserved_specs=[],
                outcome="success",
            )
        )
        json_str = audit.to_json()
        assert "SPEC-001" in json_str
        assert "iteration" in json_str
        assert "success" in json_str

    def test_empty_audit_to_json(self):
        """Empty audit produces valid JSON."""
        audit = RegenerationAudit()
        json_str = audit.to_json()
        assert json_str == "[]" or "[]" in json_str


class TestUnsatCoreGoldenParsing:
    """Golden-file tests for UNSAT core parsing with real Z3 output."""

    # Golden test data: real Z3 constraint name formats
    GOLDEN_SPEC_CONSTRAINT = "specification_7be07d53_hole_diameter_min"
    GOLDEN_SPEC_CONSTRAINT_MAX = "specification_7be07d53_hole_diameter_max"
    GOLDEN_SPEC_SHORT = "SPEC-001_wall_thickness_min"
    GOLDEN_INV_POS = "INV_POS_host__normal__plate_thickness"
    GOLDEN_INV_NONNEG = "INV_NONNEG_payload__static__clearance"
    GOLDEN_INV_GE1 = "INV_GE1_bracket__normal__safety_factor"

    def test_real_spec_uuid_format(self):
        """Parse specification_<hex>_param_bound format (real Z3 output)."""
        result = extract_implicated_nodes([self.GOLDEN_SPEC_CONSTRAINT])
        # Should extract spec_id as "specification_7be07d53"
        assert "specification_7be07d53" in result.spec_ids
        # Should extract param_name as "hole_diameter"
        assert "hole_diameter" in result.param_names

    def test_real_spec_uuid_max_bound(self):
        """Parse specification_<hex>_param_max format."""
        result = extract_implicated_nodes([self.GOLDEN_SPEC_CONSTRAINT_MAX])
        assert "specification_7be07d53" in result.spec_ids
        assert "hole_diameter" in result.param_names

    def test_short_spec_format_still_works(self):
        """SPEC-XXX format continues to work."""
        result = extract_implicated_nodes([self.GOLDEN_SPEC_SHORT])
        assert "SPEC-001" in result.spec_ids
        assert "wall_thickness" in result.param_names

    def test_mixed_core_with_multiple_constraints(self):
        """Parse mixed core with 5+ constraints."""
        core = [
            "specification_1bdce5ce_safety_factor_min",
            "specification_0619e592_safety_factor_max",
            "SPEC-002_payload_mass_min",
            "INV_POS_bracket__normal__plate_thickness",
            "INV_NONNEG_housing__static__clearance",
            "specification_3c933162_hole_diameter_min",
        ]
        result = extract_implicated_nodes(core)
        # All 4 specification IDs extracted
        assert "specification_1bdce5ce" in result.spec_ids
        assert "specification_0619e592" in result.spec_ids
        assert "specification_3c933162" in result.spec_ids
        assert "SPEC-002" in result.spec_ids
        # Param names extracted
        assert "safety_factor" in result.param_names
        assert "payload_mass" in result.param_names
        assert "hole_diameter" in result.param_names
        # Scoped keys from INV constraints
        assert len(result.scoped_keys) == 2
        assert len(result.constraint_names) == 6

    def test_core_with_newlines(self):
        """Parse core when constraints have leading/trailing whitespace."""
        # Simulate constraints with whitespace (as might occur in parsing)
        core = [
            "  specification_7be07d53_hole_diameter_min  ",
            "\tINV_POS_host__normal__plate_thickness\n",
        ]
        # Strip whitespace before parsing
        stripped = [c.strip() for c in core]
        result = extract_implicated_nodes(stripped)
        assert "specification_7be07d53" in result.spec_ids
        assert len(result.scoped_keys) == 1

    def test_malformed_constraint_skipped(self):
        """Malformed constraint (no pattern match) skipped gracefully."""
        core = [
            "specification_7be07d53_hole_diameter_min",  # valid
            "some_random_string",  # invalid - no SPEC/INV pattern
            "justtext",  # invalid - no underscore structure
            "INV_INVALID_notscoped",  # invalid - bad scoped key format
        ]
        result = extract_implicated_nodes(core)
        # Only valid spec constraint parsed
        assert "specification_7be07d53" in result.spec_ids
        assert len(result.spec_ids) == 1
        # INV_INVALID should not crash but won't produce valid key
        # All constraints in constraint_names list
        assert len(result.constraint_names) == 4

    def test_deterministic_ordering(self):
        """Output sets have deterministic iteration order."""
        core = [
            "SPEC-003_c_min",
            "SPEC-001_a_min",
            "SPEC-002_b_min",
        ]
        result1 = extract_implicated_nodes(core)
        result2 = extract_implicated_nodes(core)
        # Sets should contain same elements
        assert result1.spec_ids == result2.spec_ids
        assert result1.param_names == result2.param_names
        # Constraint names list preserved in order
        assert result1.constraint_names == result2.constraint_names

    def test_spec_id_extraction_accuracy(self):
        """Verify exact spec_id extraction from various formats."""
        test_cases = [
            ("specification_abcd1234_param_min", "specification_abcd1234"),
            ("specification_12345678_some_param_max", "specification_12345678"),
            ("SPEC-001_param_min", "SPEC-001"),
            ("SPEC-999_multi_word_param_max", "SPEC-999"),
        ]
        for constraint, expected_id in test_cases:
            result = extract_implicated_nodes([constraint])
            assert expected_id in result.spec_ids, f"Failed for {constraint}"

    def test_param_extraction_with_underscores(self):
        """Param names with underscores parsed correctly."""
        # "hole_diameter_min" -> param is "hole_diameter", bound is "min"
        result = extract_implicated_nodes(["specification_7be07d53_hole_diameter_min"])
        assert "hole_diameter" in result.param_names

        # Multi-underscore param
        result2 = extract_implicated_nodes(["SPEC-001_max_allowed_stress_min"])
        assert "max_allowed_stress" in result2.param_names

    def test_empty_core_empty_result(self):
        """Empty UNSAT core produces empty ImplicatedNodeSet."""
        result = extract_implicated_nodes([])
        assert len(result.spec_ids) == 0
        assert len(result.param_names) == 0
        assert len(result.scoped_keys) == 0
        assert len(result.constraint_names) == 0
        assert result.failure_type == "unsat"


# ==============================================================================
# resolve_core_to_nodes tests
# ==============================================================================


@pytest.fixture
def engine(tmp_path) -> HypergraphEngine:
    """Create a fresh HypergraphEngine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


class TestResolveCoreToNodes:
    """Tests for resolve_core_to_nodes function."""

    def test_resolve_spec_constraint_to_node(self, engine):
        """specification_<hex>_param_bound -> node ID."""
        # Add spec node
        spec = SpecificationNode(
            id="specification_7be07d53",
            node_type=NodeType.SPECIFICATION,
            description="Test spec",
            derives_from=["REQ-001"],
            parameters=[],
        )
        engine.add_node(spec)

        core = ["specification_7be07d53_hole_diameter_min"]
        result = resolve_core_to_nodes(core, engine)

        assert len(result) == 1
        assert (
            result["specification_7be07d53_hole_diameter_min"]
            == "specification_7be07d53"
        )

    def test_resolve_short_spec_format(self, engine):
        """SPEC-XXX_param_bound -> node ID."""
        spec = SpecificationNode(
            id="SPEC-001",
            node_type=NodeType.SPECIFICATION,
            description="Test",
            derives_from=["REQ-001"],
            parameters=[],
        )
        engine.add_node(spec)

        core = ["SPEC-001_thickness_min", "SPEC-001_thickness_max"]
        result = resolve_core_to_nodes(core, engine)

        assert len(result) == 2
        assert result["SPEC-001_thickness_min"] == "SPEC-001"
        assert result["SPEC-001_thickness_max"] == "SPEC-001"

    def test_resolve_missing_node_excluded(self, engine):
        """Constraint with non-existent node excluded from result."""
        # Don't add any nodes
        core = ["SPEC-999_param_min", "specification_deadbeef_value_max"]
        result = resolve_core_to_nodes(core, engine)

        assert len(result) == 0

    def test_resolve_contract_constraint_to_node(self, engine):
        """CONTRACT_<id>_A_<n> -> node ID (clause index in key)."""
        contract = Contract(
            id="c001",
            node_type=NodeType.CONTRACT,
            description="Test Contract",
            assumptions=["temperature >= 0"],
            guarantees=["output <= 100"],
        )
        engine.add_node(contract)

        core = ["CONTRACT_c001_A_0", "CONTRACT_c001_G_1"]
        result = resolve_core_to_nodes(core, engine)

        assert len(result) == 2
        assert result["CONTRACT_c001_A_0"] == "c001"
        assert result["CONTRACT_c001_G_1"] == "c001"

    def test_resolve_mixed_constraints(self, engine):
        """Mixed SPEC and CONTRACT constraints resolved."""
        spec = SpecificationNode(
            id="SPEC-001",
            node_type=NodeType.SPECIFICATION,
            description="Test",
            derives_from=["REQ-001"],
            parameters=[],
        )
        contract = Contract(
            id="contract_abc",
            node_type=NodeType.CONTRACT,
            description="Contract",
            assumptions=["a > 0"],
            guarantees=["b < 10"],
        )
        engine.add_node(spec)
        engine.add_node(contract)

        core = [
            "SPEC-001_param_min",
            "CONTRACT_contract_abc_A_0",
            "INV_POS_entity__regime__quantity",  # Not resolved (no node ID)
        ]
        result = resolve_core_to_nodes(core, engine)

        assert len(result) == 2
        assert result["SPEC-001_param_min"] == "SPEC-001"
        assert result["CONTRACT_contract_abc_A_0"] == "contract_abc"

    def test_resolve_empty_core(self, engine):
        """Empty core returns empty dict."""
        result = resolve_core_to_nodes([], engine)
        assert result == {}

    def test_inv_constraints_not_resolved(self, engine):
        """INV constraints don't have node IDs, excluded from result."""
        core = [
            "INV_POS_bracket__normal__thickness",
            "INV_NONNEG_housing__static__clearance",
        ]
        result = resolve_core_to_nodes(core, engine)
        assert len(result) == 0


# ==============================================================================
# CONTRACT pattern in extract_implicated_nodes
# ==============================================================================


class TestExtractImplicatedContractNodes:
    """Tests for CONTRACT pattern matching in extract_implicated_nodes."""

    def test_extract_implicated_contract_only_core(self):
        """UNSAT core = [CONTRACT_c1_G_2, CONTRACT_c1_G_4] → contract_ids = {'c1'}."""
        result = extract_implicated_nodes(["CONTRACT_c1_G_2", "CONTRACT_c1_G_4"])
        assert result.contract_ids == {"c1"}
        assert len(result.spec_ids) == 0

    def test_extract_implicated_mixed_core(self):
        """SPEC + CONTRACT → both spec_ids and contract_ids populated."""
        result = extract_implicated_nodes(
            [
                "SPEC-001_thickness_min",
                "CONTRACT_c2_A_1",
                "CONTRACT_c2_G_3",
            ]
        )
        assert "SPEC-001" in result.spec_ids
        assert "c2" in result.contract_ids
