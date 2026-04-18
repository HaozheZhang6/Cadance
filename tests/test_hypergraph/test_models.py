"""Tests for hypergraph models."""

from datetime import datetime

import pytest

from src.hypergraph.models import (
    Budget,
    Contract,
    ContractStatus,
    Edge,
    EdgeType,
    Evidence,
    Experiment,
    Intent,
    Node,
    NodeType,
    Requirement,
    RequirementStatus,
    Unknown,
)


class TestNodeType:
    """Tests for NodeType enum."""

    def test_node_types_exist(self):
        """All required node types should be defined."""
        assert NodeType.INTENT is not None
        assert NodeType.BUDGET is not None
        assert NodeType.CONTRACT is not None
        assert NodeType.REQUIREMENT is not None
        assert NodeType.UNKNOWN is not None
        assert NodeType.EVIDENCE is not None
        assert NodeType.EXPERIMENT is not None
        assert NodeType.ARTIFACT is not None
        assert NodeType.TOOL_INVOCATION is not None


class TestEdgeType:
    """Tests for EdgeType enum."""

    def test_edge_types_exist(self):
        """All required edge types should be defined."""
        assert EdgeType.VALIDATES is not None
        assert EdgeType.DEPENDS_ON is not None
        assert EdgeType.RESOLVES is not None
        assert EdgeType.CONSUMES is not None
        assert EdgeType.HAS_CHILD is not None
        assert EdgeType.DERIVES_FROM is not None
        assert EdgeType.SATISFIES is not None
        assert EdgeType.GENERATED is not None
        assert EdgeType.EVIDENCES is not None
        assert EdgeType.RAISES is not None


class TestNode:
    """Tests for base Node class."""

    def test_node_creation(self):
        """Node should be creatable with required fields."""
        node = Node(
            id="test_001",
            node_type=NodeType.INTENT,
            description="Test node",
        )
        assert node.id == "test_001"
        assert node.node_type == NodeType.INTENT
        assert node.description == "Test node"
        assert node.confidence == 1.0  # Default confidence
        assert node.metadata == {}

    def test_node_with_confidence(self):
        """Node should accept custom confidence."""
        node = Node(
            id="test_002",
            node_type=NodeType.UNKNOWN,
            description="Uncertain node",
            confidence=0.2,
        )
        assert node.confidence == 0.2

    def test_node_with_metadata(self):
        """Node should accept metadata dict."""
        metadata = {"source": "user", "version": 1}
        node = Node(
            id="test_003",
            node_type=NodeType.CONTRACT,
            description="Contract node",
            metadata=metadata,
        )
        assert node.metadata == metadata

    def test_node_created_at_auto_populated(self):
        """Node should have created_at timestamp."""
        node = Node(
            id="test_004",
            node_type=NodeType.INTENT,
            description="Test node",
        )
        assert node.created_at is not None
        assert isinstance(node.created_at, datetime)


class TestEdge:
    """Tests for Edge class."""

    def test_edge_creation(self):
        """Edge should be creatable with required fields."""
        edge = Edge(
            id="edge_001",
            source_id="node_001",
            target_id="node_002",
            edge_type=EdgeType.HAS_CHILD,
        )
        assert edge.id == "edge_001"
        assert edge.source_id == "node_001"
        assert edge.target_id == "node_002"
        assert edge.edge_type == EdgeType.HAS_CHILD
        assert edge.metadata == {}

    def test_edge_with_metadata(self):
        """Edge should accept metadata dict."""
        metadata = {"weight": 1.0}
        edge = Edge(
            id="edge_002",
            source_id="node_001",
            target_id="node_002",
            edge_type=EdgeType.VALIDATES,
            metadata=metadata,
        )
        assert edge.metadata == metadata


class TestIntent:
    """Tests for Intent node type."""

    def test_intent_creation(self):
        """Intent should be creatable with goal specification."""
        intent = Intent(
            id="intent_001",
            description="Design a mounting bracket for a 5kg load",
            goal="Create a bracket that can support 5kg",
        )
        assert intent.node_type == NodeType.INTENT
        assert intent.goal == "Create a bracket that can support 5kg"

    def test_intent_with_constraints(self):
        """Intent should accept constraints list."""
        intent = Intent(
            id="intent_002",
            description="Design bracket",
            goal="Support 5kg",
            constraints=["max weight 100g", "aluminum material"],
        )
        assert intent.constraints == ["max weight 100g", "aluminum material"]


class TestRequirementStatus:
    """Tests for RequirementStatus enum."""

    def test_status_values_exist(self):
        """All required status values should be defined."""
        assert RequirementStatus.DRAFT is not None
        assert RequirementStatus.REFINING is not None
        assert RequirementStatus.VALIDATED is not None
        assert RequirementStatus.REJECTED is not None


class TestContractStatus:
    """Tests for ContractStatus enum."""

    def test_status_values_exist(self):
        """All required status values should be defined."""
        assert ContractStatus.DRAFT is not None
        assert ContractStatus.IN_PROGRESS is not None
        assert ContractStatus.SATISFIED is not None
        assert ContractStatus.VIOLATED is not None

    def test_status_values(self):
        """Status values should match expected strings."""
        assert ContractStatus.DRAFT.value == "draft"
        assert ContractStatus.IN_PROGRESS.value == "in_progress"
        assert ContractStatus.SATISFIED.value == "satisfied"
        assert ContractStatus.VIOLATED.value == "violated"


class TestRequirement:
    """Tests for Requirement node type."""

    def test_requirement_creation(self):
        """Requirement should be creatable with statement."""
        requirement = Requirement(
            id="req_001",
            description="REQ-001",
            statement="The bracket shall withstand a static load of 49 N",
        )
        assert requirement.node_type == NodeType.REQUIREMENT
        assert (
            requirement.statement == "The bracket shall withstand a static load of 49 N"
        )
        assert requirement.status == RequirementStatus.DRAFT  # Default

    def test_requirement_with_full_fields(self):
        """Requirement should accept all fields."""
        requirement = Requirement(
            id="req_002",
            description="REQ-002",
            statement="The bracket shall limit deflection to 1.0 mm",
            rationale="Excessive deflection causes misalignment",
            verification_method="FEA analysis or physical load test",
            assumptions=["Material is aluminum", "Load is static"],
            status=RequirementStatus.VALIDATED,
            is_testable=True,
            is_unambiguous=True,
            is_complete=True,
        )
        assert requirement.rationale == "Excessive deflection causes misalignment"
        assert requirement.verification_method == "FEA analysis or physical load test"
        assert requirement.assumptions == ["Material is aluminum", "Load is static"]
        assert requirement.status == RequirementStatus.VALIDATED
        assert requirement.is_testable is True
        assert requirement.is_unambiguous is True
        assert requirement.is_complete is True

    def test_requirement_iteration_tracking(self):
        """Requirement should track iterations."""
        requirement = Requirement(
            id="req_003",
            description="REQ-003",
            statement="Test statement",
            iteration_count=2,
            max_iterations=3,
        )
        assert requirement.iteration_count == 2
        assert requirement.max_iterations == 3

    def test_requirement_evidence_sources(self):
        """Requirement should track evidence sources."""
        requirement = Requirement(
            id="req_004",
            description="REQ-004",
            statement="Test statement",
            evidence_sources=["evidence_001", "evidence_002"],
        )
        assert requirement.evidence_sources == ["evidence_001", "evidence_002"]


class TestBudget:
    """Tests for Budget node type."""

    def test_budget_creation(self):
        """Budget should be creatable with allowances."""
        budget = Budget(
            id="budget_001",
            description="Material budget",
            resource_type="weight",
            total=1000.0,
            unit="grams",
        )
        assert budget.node_type == NodeType.BUDGET
        assert budget.resource_type == "weight"
        assert budget.total == 1000.0
        assert budget.consumed == 0.0  # Default
        assert budget.unit == "grams"

    def test_budget_remaining(self):
        """Budget should calculate remaining amount."""
        budget = Budget(
            id="budget_002",
            description="Cost budget",
            resource_type="cost",
            total=100.0,
            consumed=30.0,
            unit="USD",
        )
        assert budget.remaining == 70.0


class TestContract:
    """Tests for Contract node type."""

    def test_contract_creation(self):
        """Contract should be creatable with I/O guarantees."""
        contract = Contract(
            id="contract_001",
            description="Load bearing contract",
            inputs={"load": "force in Newtons"},
            outputs={"deflection": "displacement in mm"},
            guarantees=["deflection < 1mm for load < 50N"],
        )
        assert contract.node_type == NodeType.CONTRACT
        assert contract.inputs == {"load": "force in Newtons"}
        assert contract.outputs == {"deflection": "displacement in mm"}
        assert "deflection < 1mm for load < 50N" in contract.guarantees

    def test_contract_default_status(self):
        """Contract should default to DRAFT status."""
        contract = Contract(
            id="contract_001",
            description="Test contract",
        )
        assert contract.status == ContractStatus.DRAFT

    def test_contract_status_can_be_set(self):
        """Contract status should be settable."""
        contract = Contract(
            id="contract_001",
            description="Test contract",
            status=ContractStatus.SATISFIED,
        )
        assert contract.status == ContractStatus.SATISFIED

    def test_contract_with_enhanced_fields(self):
        """Contract should accept enhanced fields for requirements-first flow."""
        contract = Contract(
            id="contract_002",
            description="Structural support contract",
            inputs={"applied_load": "Static force at load point"},
            outputs={"stress_state": "Von Mises stress distribution"},
            guarantees=["Max stress < 138 MPa"],
            assumptions=["Material is 6061-T6 aluminum", "Load is static"],
            input_bounds={"load": "0-49 N", "temperature": "-20 to +60 C"},
            cross_effects={"thermal_subsystem": "Generates thermal expansion"},
            unknowns=["unknown_001"],
            experiments_needed=["experiment_001"],
        )
        assert contract.assumptions == [
            "Material is 6061-T6 aluminum",
            "Load is static",
        ]
        assert contract.input_bounds == {
            "load": "0-49 N",
            "temperature": "-20 to +60 C",
        }
        assert contract.cross_effects == {
            "thermal_subsystem": "Generates thermal expansion"
        }
        assert contract.unknowns == ["unknown_001"]
        assert contract.experiments_needed == ["experiment_001"]


class TestUnknown:
    """Tests for Unknown node type."""

    def test_unknown_creation(self):
        """Unknown should be creatable with uncertainty description."""
        unknown = Unknown(
            id="unknown_001",
            description="Material selection uncertainty",
            reason="Multiple valid options, need analysis",
        )
        assert unknown.node_type == NodeType.UNKNOWN
        assert unknown.confidence == 0.2  # Default for Unknown
        assert unknown.reason == "Multiple valid options, need analysis"

    def test_unknown_with_candidates(self):
        """Unknown should accept candidate options."""
        unknown = Unknown(
            id="unknown_002",
            description="Material choice",
            reason="Need to select",
            candidates=["aluminum", "steel", "titanium"],
        )
        assert unknown.candidates == ["aluminum", "steel", "titanium"]


class TestEvidence:
    """Tests for Evidence node type."""

    def test_evidence_creation(self):
        """Evidence should be creatable with provenance."""
        evidence = Evidence(
            id="evidence_001",
            description="FEA simulation result",
            evidence_type="simulation",
            provenance="ANSYS simulation run 2024-01-15",
            data={"max_stress": 150.0, "unit": "MPa"},
        )
        assert evidence.node_type == NodeType.EVIDENCE
        assert evidence.evidence_type == "simulation"
        assert evidence.provenance == "ANSYS simulation run 2024-01-15"
        assert evidence.data["max_stress"] == 150.0

    def test_evidence_requires_provenance(self):
        """Evidence must have provenance."""
        with pytest.raises(ValueError):
            Evidence(
                id="evidence_002",
                description="Test evidence",
                evidence_type="test",
                provenance="",  # Empty provenance should raise
                data={},
            )


class TestExperiment:
    """Tests for Experiment node type."""

    def test_experiment_creation(self):
        """Experiment should be creatable with planned test."""
        experiment = Experiment(
            id="experiment_001",
            description="Load test experiment",
            hypothesis="Bracket will support 5kg without yielding",
            method="Apply 50N load and measure deflection",
            expected_outcome={"max_deflection": 0.5, "unit": "mm"},
        )
        assert experiment.node_type == NodeType.EXPERIMENT
        assert experiment.hypothesis is not None
        assert experiment.method is not None
        assert experiment.status == "planned"  # Default status

    def test_experiment_status_transitions(self):
        """Experiment status should be updatable."""
        experiment = Experiment(
            id="experiment_002",
            description="Test experiment",
            hypothesis="Test hypothesis",
            method="Test method",
        )
        assert experiment.status == "planned"
        experiment.status = "running"
        assert experiment.status == "running"
        experiment.status = "completed"
        assert experiment.status == "completed"
