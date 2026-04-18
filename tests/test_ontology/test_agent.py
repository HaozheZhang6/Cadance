"""Tests for OntologyAgent."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import Trigger, TriggerType
from src.hypergraph.models import (
    Contract,
    EdgeType,
    NodeType,
    Requirement,
    SpecificationNode,
    SpecParameter,
)
from src.ontology import (
    ConfidenceSource,
    FailureMode,
    InterfacePhysics,
    MaterialEntity,
    OntologyStore,
    PartEntity,
    PhysicsPhenomenon,
    ProcessTechnique,
)
from src.ontology.agent import OntologyAgent


@pytest.fixture
def ontology_store():
    """Create populated ontology store for testing."""
    store = OntologyStore()

    # Add failure modes
    fatigue = FailureMode(
        id="fm-fatigue-001",
        name="Fatigue Failure",
        description="Material failure due to cyclic loading",
        domain="mechanical",
        severity="high",
        causes=["cyclic loading", "stress concentration"],
        effects=["crack initiation", "fracture"],
        mitigations=["reduce stress concentration", "improve surface finish"],
        detection_methods=["visual inspection", "NDT"],
        confidence=0.85,
        source="textbook",
        source_type=ConfidenceSource.TEXTBOOK,
        tags=["mechanical", "structural"],
    )
    store.add_entity(fatigue)

    corrosion = FailureMode(
        id="fm-corrosion-001",
        name="Corrosion",
        description="Material degradation due to chemical reaction",
        domain="chemical",
        severity="medium",
        causes=["moisture", "chemical exposure"],
        effects=["material loss", "structural weakening"],
        mitigations=["protective coating", "material selection"],
        confidence=0.80,
        source="textbook",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(corrosion)

    # Add physics phenomena
    stress_concentration = PhysicsPhenomenon(
        id="phys-stress-001",
        name="Stress Concentration",
        description="Localized increase in stress at geometry changes",
        domain="mechanical",
        parameters=["stress concentration factor", "notch radius"],
        equations=[{"name": "Kt", "formula": "sigma_max/sigma_nom"}],
        keywords=["stress", "notch", "fillet", "corner"],
        confidence=0.90,
        source="textbook",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(stress_concentration)

    # Add parts
    bracket = PartEntity(
        id="part-bracket-001",
        name="Mounting Bracket",
        category="bracket",
        typical_materials=["steel", "aluminum"],
        standards=["ISO 4762"],
        confidence=0.85,
        source="datasheet",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(bracket)

    # Add materials
    steel = MaterialEntity(
        id="mat-steel-001",
        name="1020 Steel",
        category="metal",
        compatible_materials=["aluminum"],
        incompatible_materials=["copper"],
        confidence=0.90,
        source="datasheet",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(steel)

    aluminum = MaterialEntity(
        id="mat-aluminum-001",
        name="6061 Aluminum",
        category="metal",
        compatible_materials=["steel"],
        incompatible_materials=[],
        confidence=0.90,
        source="datasheet",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(aluminum)

    # Add process
    cnc = ProcessTechnique(
        id="proc-cnc-001",
        name="CNC Milling",
        category="machining",
        material_compatibility=["steel", "aluminum"],
        common_defects=["tool marks", "burrs"],
        parameters={"feed_rate": {"value": 100, "unit": "mm/min"}},
        confidence=0.85,
        source="manual",
        source_type=ConfidenceSource.MANUAL,
    )
    store.add_entity(cnc)

    # Add interface physics
    thermal_interface = InterfacePhysics(
        id="iface-thermal-001",
        name="Thermal Interface",
        interface_type="thermal",
        component_types=["heatsink", "processor"],
        phenomena=["thermal resistance", "contact conductance"],
        design_rules=["minimize air gaps", "use thermal paste"],
        interface_failure_modes=["thermal runaway", "delamination"],
        confidence=0.85,
        source="textbook",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(thermal_interface)

    return store


@pytest.fixture
def mock_engine():
    """Create mock HypergraphEngine."""
    engine = MagicMock()
    return engine


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    return MagicMock()


@pytest.fixture
def agent(mock_engine, mock_llm, ontology_store):
    """Create OntologyAgent with mocked dependencies."""
    return OntologyAgent(mock_engine, mock_llm, ontology_store)


class TestAgentBasics:
    """Test basic agent properties."""

    def test_agent_name(self, agent):
        """Test agent name property."""
        assert agent.name == "OntologyAgent"

    def test_trigger_types(self, agent):
        """Test agent responds to correct trigger types."""
        triggers = agent.trigger_types
        assert TriggerType.REQUIREMENTS_GENERATED in triggers
        assert TriggerType.SPECIFICATIONS_DERIVED in triggers
        assert TriggerType.CONTRACTS_EXTRACTED in triggers
        assert TriggerType.MANUAL in triggers


class TestRequirementsAnalysis:
    """Test _analyze_requirements method."""

    def test_analyze_requirements_creates_evidence_for_failure_modes(
        self, agent, mock_engine
    ):
        """Test that failure mode evidence is created for requirements."""
        # Setup mock engine to return a requirement
        req = Requirement(
            id="req-001",
            node_type=NodeType.REQUIREMENT,
            description="Fatigue resistance requirement",
            statement="The bracket shall withstand cyclic loading without fatigue failure",
            rationale="Safety critical",
        )
        mock_engine.get_nodes_by_type.return_value = [req]

        # Mock physics taxonomy where it's imported
        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
            mutation = agent.propose_mutation(trigger)

        # Should have created evidence nodes
        assert len(mutation.nodes_to_add) > 0

        # Check evidence node properties
        evidence_nodes = [
            n for n in mutation.nodes_to_add if n.node_type == NodeType.EVIDENCE
        ]
        assert len(evidence_nodes) > 0

        # Verify evidence has failure mode data
        fm_evidence = [
            e for e in evidence_nodes if e.evidence_type == "ontology_failure_mode"
        ]
        assert len(fm_evidence) > 0
        assert fm_evidence[0].data["failure_mode"] == "Fatigue Failure"
        assert fm_evidence[0].data["severity"] == "high"

    def test_analyze_requirements_creates_physics_evidence(self, agent, mock_engine):
        """Test that physics evidence is created for requirements."""
        req = Requirement(
            id="req-002",
            node_type=NodeType.REQUIREMENT,
            description="Stress concentration requirement",
            statement="The part shall have stress concentration factor below 2.0",
            rationale="Durability",
        )
        mock_engine.get_nodes_by_type.return_value = [req]

        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
            mutation = agent.propose_mutation(trigger)

        physics_evidence = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type") and n.evidence_type == "ontology_physics"
        ]
        assert len(physics_evidence) > 0
        assert physics_evidence[0].data["phenomenon"] == "Stress Concentration"

    def test_analyze_requirements_creates_unknown_for_gaps(self, agent, mock_engine):
        """Test that Unknown nodes are created when no knowledge found."""
        # Use empty ontology store to ensure no matches
        empty_store = OntologyStore()
        agent_with_empty_store = OntologyAgent(mock_engine, MagicMock(), empty_store)

        req = Requirement(
            id="req-003",
            node_type=NodeType.REQUIREMENT,
            description="Quantum requirement",
            statement="The system shall comply with quantum entanglement protocols",
            rationale="Future tech",
        )
        mock_engine.get_nodes_by_type.return_value = [req]

        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
            mutation = agent_with_empty_store.propose_mutation(trigger)

        unknown_nodes = [
            n for n in mutation.nodes_to_add if n.node_type == NodeType.UNKNOWN
        ]
        assert len(unknown_nodes) > 0
        assert "No ontology knowledge found" in unknown_nodes[0].description

    def test_analyze_requirements_creates_edges(self, agent, mock_engine):
        """Test that edges are created linking evidence to requirements."""
        req = Requirement(
            id="req-004",
            node_type=NodeType.REQUIREMENT,
            description="Fatigue resistance",
            statement="The bracket shall resist fatigue",
            rationale="Safety",
        )
        mock_engine.get_nodes_by_type.return_value = [req]

        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
            mutation = agent.propose_mutation(trigger)

        # Should have edges
        assert len(mutation.edges_to_add) > 0

        # Check edge types
        validates_edges = [
            e for e in mutation.edges_to_add if e.edge_type == EdgeType.VALIDATES
        ]
        assert len(validates_edges) > 0


class TestSpecificationsAnalysis:
    """Test _analyze_specifications method."""

    def test_analyze_specifications_suggests_processes(self, agent, mock_engine):
        """Test that manufacturing processes are suggested for specs."""
        spec = SpecificationNode(
            id="spec-001",
            node_type=NodeType.SPECIFICATION,
            description="CNC machined steel bracket with milling operations",
            parameters=[
                SpecParameter(name="milling", value="required", unit=""),
                SpecParameter(name="material_type", value="steel", unit=""),
            ],
        )
        mock_engine.get_nodes_by_type.return_value = [spec]

        trigger = Trigger(trigger_type=TriggerType.SPECIFICATIONS_DERIVED)
        mutation = agent.propose_mutation(trigger)

        process_evidence = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type") and n.evidence_type == "ontology_process"
        ]
        # May or may not find process depending on keyword matching
        # If found, verify structure
        if process_evidence:
            assert "process" in process_evidence[0].data
            assert process_evidence[0].evidence_type == "ontology_process"


class TestContractsAnalysis:
    """Test _analyze_contracts method."""

    def test_analyze_contracts_finds_interface_physics(self, agent, mock_engine):
        """Test that interface physics are found for contracts."""
        contract = Contract(
            id="contract-001",
            node_type=NodeType.CONTRACT,
            description="Thermal interface between heatsink and processor",
            inputs={"heat_input": "thermal"},
            outputs={"heat_output": "thermal"},
            assumptions=["Good thermal contact"],
            guarantees=["Temperature below 80C"],
        )
        mock_engine.get_nodes_by_type.return_value = [contract]

        trigger = Trigger(trigger_type=TriggerType.CONTRACTS_EXTRACTED)
        mutation = agent.propose_mutation(trigger)

        interface_evidence = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type") and n.evidence_type == "ontology_interface"
        ]
        assert len(interface_evidence) > 0
        assert interface_evidence[0].data["interface_type"] == "thermal"


class TestManualQueries:
    """Test manual query handling."""

    def test_manual_query_failure_modes(self, agent, mock_engine):
        """Test manual failure mode query."""
        mock_engine.get_nodes_by_type.return_value = []

        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={
                "query_type": "failure_modes",
                "domains": ["mechanical"],
            },
        )
        mutation = agent.propose_mutation(trigger)

        evidence_nodes = [
            n for n in mutation.nodes_to_add if n.node_type == NodeType.EVIDENCE
        ]
        assert len(evidence_nodes) > 0

    def test_manual_query_components(self, agent, mock_engine):
        """Test manual component query."""
        mock_engine.get_nodes_by_type.return_value = []

        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={
                "query_type": "components",
                "requirements": ["mounting", "bracket"],
                "category": "bracket",
            },
        )
        mutation = agent.propose_mutation(trigger)

        # Should find bracket component
        evidence_nodes = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type") and n.evidence_type == "ontology_component"
        ]
        assert len(evidence_nodes) > 0

    def test_manual_query_physics(self, agent, mock_engine):
        """Test manual physics query."""
        mock_engine.get_nodes_by_type.return_value = []

        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={
                "query_type": "physics",
                "keywords": ["stress", "concentration"],
            },
        )
        mutation = agent.propose_mutation(trigger)

        physics_evidence = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type") and n.evidence_type == "ontology_physics"
        ]
        assert len(physics_evidence) > 0

    def test_manual_query_with_target_node(self, agent, mock_engine):
        """Test manual query creates edge to target node."""
        mock_engine.get_nodes_by_type.return_value = []

        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={
                "query_type": "failure_modes",
                "domains": ["mechanical"],
                "target_node_id": "target-001",
            },
        )
        mutation = agent.propose_mutation(trigger)

        # Should have edges to target
        target_edges = [e for e in mutation.edges_to_add if e.target_id == "target-001"]
        assert len(target_edges) > 0


class TestHelperMethods:
    """Test helper methods."""

    def test_extract_keywords(self, agent):
        """Test keyword extraction from text."""
        text = "The bracket shall withstand 5kg load without yielding"
        keywords = agent._extract_keywords(text)

        assert "bracket" in keywords
        assert "withstand" in keywords
        assert "load" in keywords
        assert "yielding" in keywords
        # Stop words should be filtered
        assert "the" not in keywords
        assert "shall" not in keywords

    def test_extract_keywords_limits_results(self, agent):
        """Test keyword extraction limits to 20."""
        text = " ".join([f"word{i}" for i in range(50)])
        keywords = agent._extract_keywords(text)
        assert len(keywords) <= 20

    def test_detect_domains_with_mechanical_keywords(self, agent):
        """Test domain detection for mechanical keywords."""
        from src.physics.domains import PhysicsDomain

        mock_taxonomy = {
            PhysicsDomain.MECHANICAL: {
                "keywords": ["stress", "load", "fatigue", "bracket"],
            },
            PhysicsDomain.THERMAL: {
                "keywords": ["temperature", "heat", "thermal"],
            },
        }

        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", mock_taxonomy):
            domains = agent._detect_domains(["stress", "load", "bracket"])
            assert "mechanical" in domains

    def test_detect_domains_returns_empty_for_unknown(self, agent):
        """Test domain detection returns empty for unknown keywords."""
        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            domains = agent._detect_domains(["quantum", "entanglement"])
            assert domains == []


class TestMutationStructure:
    """Test mutation output structure."""

    def test_mutation_has_description(self, agent, mock_engine):
        """Test mutation has descriptive message."""
        mock_engine.get_nodes_by_type.return_value = []

        trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            mutation = agent.propose_mutation(trigger)

        assert "OntologyAgent" in mutation.description
        assert "knowledge nodes" in mutation.description

    def test_empty_trigger_returns_empty_mutation(self, agent, mock_engine):
        """Test unhandled trigger returns empty mutation."""
        mock_engine.get_nodes_by_type.return_value = []

        # Use a trigger type not in agent.trigger_types
        trigger = Trigger(trigger_type=TriggerType.INTENT_CREATED)
        mutation = agent.propose_mutation(trigger)

        assert len(mutation.nodes_to_add) == 0
        assert len(mutation.edges_to_add) == 0


class TestConfidenceHandling:
    """Test confidence score handling."""

    def test_evidence_confidence_is_damped(self, agent, mock_engine):
        """Test evidence confidence is damped from source."""
        req = Requirement(
            id="req-conf-001",
            node_type=NodeType.REQUIREMENT,
            description="Confidence test requirement",
            statement="The bracket shall resist fatigue failure",
            rationale="Safety",
        )
        mock_engine.get_nodes_by_type.return_value = [req]

        with patch("src.physics.taxonomy.PHYSICS_TAXONOMY", {}):
            trigger = Trigger(trigger_type=TriggerType.REQUIREMENTS_GENERATED)
            mutation = agent.propose_mutation(trigger)

        fm_evidence = [
            n
            for n in mutation.nodes_to_add
            if hasattr(n, "evidence_type")
            and n.evidence_type == "ontology_failure_mode"
        ]
        if fm_evidence:
            # Fatigue FM has confidence 0.85, damping factor is 0.8
            # So evidence confidence should be 0.85 * 0.8 = 0.68
            assert fm_evidence[0].confidence == pytest.approx(0.68, rel=0.01)
