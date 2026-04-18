"""Tests for hypergraph invariant enforcement."""

import pytest

from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.invariants import InvariantChecker
from src.hypergraph.models import (
    Contract,
    EdgeType,
    Evidence,
    Intent,
    Unknown,
)
from src.hypergraph.store import HypergraphStore


class TestInvariantChecker:
    """Tests for InvariantChecker."""

    @pytest.fixture
    def engine(self, tmp_path):
        """Create a fresh engine for each test."""
        store_path = tmp_path / "test_graph.json"
        store = HypergraphStore(store_path)
        return HypergraphEngine(store)

    @pytest.fixture
    def checker(self, engine):
        """Create invariant checker."""
        return InvariantChecker(engine)

    def test_checker_creation(self, checker):
        """Checker should be creatable with an engine."""
        assert checker is not None

    def test_no_interface_without_contract(self, checker, engine):
        """Invariant: No interface without a contract.

        If a node has inputs/outputs defined, it must have Contract type.
        """
        # Valid: Contract with interface
        contract = Contract(
            id="contract_001",
            description="Valid contract",
            inputs={"load": "force"},
            outputs={"stress": "pressure"},
            guarantees=[],
        )
        engine.add_node(contract)

        violations = checker.check_all()
        assert len(violations) == 0

    def test_contract_claim_without_evidence_flagged(self, checker, engine):
        """Invariant: No contract claim without Evidence or Unknown.

        Each guarantee in a Contract should have either:
        - An Evidence node validating it, OR
        - An Unknown node marking it as unverified
        """
        # Contract with guarantee but no evidence
        contract = Contract(
            id="contract_001",
            description="Contract with unverified claim",
            inputs={},
            outputs={},
            guarantees=["stress < 100 MPa"],
        )
        engine.add_node(contract)

        violations = checker.check_all()
        # Should flag missing evidence
        assert len(violations) == 1
        assert violations[0].invariant == "contract_claim_needs_backing"
        assert violations[0].node_id == "contract_001"

    def test_contract_with_evidence_passes(self, checker, engine):
        """Contract with evidence for claims should pass."""
        contract = Contract(
            id="contract_001",
            description="Contract with evidence",
            inputs={},
            outputs={},
            guarantees=["stress < 100 MPa"],
        )
        evidence = Evidence(
            id="evidence_001",
            description="FEA result",
            evidence_type="simulation",
            provenance="ANSYS run 2024-01",
            data={"max_stress": 80.0},
        )
        engine.add_node(contract)
        engine.add_node(evidence)
        engine.add_edge("evidence_001", "contract_001", EdgeType.VALIDATES)

        violations = checker.check_all()
        assert len(violations) == 0

    def test_contract_with_unknown_passes(self, checker, engine):
        """Contract with Unknown marking uncertainty should pass."""
        contract = Contract(
            id="contract_001",
            description="Contract with unknown",
            inputs={},
            outputs={},
            guarantees=["stress < 100 MPa"],
        )
        unknown = Unknown(
            id="unknown_001",
            description="Stress analysis needed",
            reason="No FEA performed yet",
        )
        engine.add_node(contract)
        engine.add_node(unknown)
        # Unknown depends on contract (marks it as unverified)
        engine.add_edge("unknown_001", "contract_001", EdgeType.DEPENDS_ON)

        violations = checker.check_all()
        assert len(violations) == 0

    def test_evidence_requires_provenance(self, checker, engine):
        """Invariant: Every Evidence must include provenance.

        Note: This is enforced at model level, but checker should also verify.
        """
        # This should already be caught by the model validation
        # But the checker can verify existing data
        evidence = Evidence(
            id="evidence_001",
            description="Valid evidence",
            evidence_type="test",
            provenance="Lab test 2024-01-15",
            data={},
        )
        engine.add_node(evidence)

        violations = checker.check_all()
        assert len(violations) == 0

    def test_parent_confidence_bounded_by_children(self, checker, engine):
        """Invariant: Parent confidence bounded by critical children.

        Parent confidence should not exceed minimum child confidence.
        """
        # Parent with high confidence
        intent = Intent(
            id="intent_001",
            description="Parent",
            goal="Goal",
            confidence=0.9,
        )
        # Children with lower confidence
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.5,  # Lower confidence
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        violations = checker.check_all()
        # Parent confidence 0.9 > min child confidence 0.5
        assert len(violations) == 1
        assert violations[0].invariant == "parent_confidence_bounded"
        assert violations[0].node_id == "intent_001"

    def test_valid_confidence_hierarchy(self, checker, engine):
        """Valid confidence hierarchy should pass."""
        intent = Intent(
            id="intent_001",
            description="Parent",
            goal="Goal",
            confidence=0.5,  # <= min child
        )
        contract1 = Contract(
            id="contract_001",
            description="Child 1",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.8,
        )
        contract2 = Contract(
            id="contract_002",
            description="Child 2",
            inputs={},
            outputs={},
            guarantees=[],
            confidence=0.5,
        )

        engine.add_node(intent)
        engine.add_node(contract1)
        engine.add_node(contract2)
        engine.add_edge("intent_001", "contract_001", EdgeType.HAS_CHILD)
        engine.add_edge("intent_001", "contract_002", EdgeType.HAS_CHILD)

        violations = checker.check_all()
        # No contract claim violations since no guarantees
        assert len(violations) == 0

    def test_check_specific_node(self, checker, engine):
        """Checker should support checking specific nodes."""
        contract = Contract(
            id="contract_001",
            description="Contract",
            inputs={},
            outputs={},
            guarantees=["claim"],
        )
        engine.add_node(contract)

        violations = checker.check_node("contract_001")
        assert len(violations) == 1

    def test_get_violation_summary(self, checker, engine):
        """Checker should provide summary of all violations."""
        # Add multiple problematic nodes
        contract1 = Contract(
            id="contract_001",
            description="Contract 1",
            inputs={},
            outputs={},
            guarantees=["claim 1"],
        )
        contract2 = Contract(
            id="contract_002",
            description="Contract 2",
            inputs={},
            outputs={},
            guarantees=["claim 2"],
        )
        engine.add_node(contract1)
        engine.add_node(contract2)

        summary = checker.get_summary()
        assert summary["total_violations"] == 2
        assert "contract_claim_needs_backing" in summary["by_invariant"]
