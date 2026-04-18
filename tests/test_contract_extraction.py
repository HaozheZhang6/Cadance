"""TDD tests for ContractExtractionAgent.

Tests contract extraction from G->R->S tree.
"""

import json

import pytest

from src.agents.llm import MockLLMClient
from src.agents.schemas import (
    AssumptionOutput,
    ContractExtractionOutput,
    ContractOutput,
    ContractTermOutput,
    GoalOutput,
    GRSTreeOutput,
    RequirementOutput,
    SpecOutput,
    SpecParameterOutput,
)
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.store import HypergraphStore


@pytest.fixture
def engine(tmp_path):
    """Fresh hypergraph engine for each test."""
    store = HypergraphStore(tmp_path / "test_graph.json")
    return HypergraphEngine(store)


@pytest.fixture
def bracket_grs_tree():
    """Sample bracket GRS tree with specs and assumptions."""
    return GRSTreeOutput(
        goals=[
            GoalOutput(
                id="G1",
                description="Support 5kg payload safely",
                goal_type="ACHIEVE",
                requirements=[
                    RequirementOutput(
                        id="R1.1",
                        statement="System SHALL support 5kg static load",
                        rationale="Primary load requirement",
                        specifications=[
                            SpecOutput(
                                id="S1.1.1",
                                description="Steel bracket with 10mm thickness",
                                parameters=[
                                    SpecParameterOutput(
                                        name="thickness",
                                        value="10",
                                        unit="mm",
                                        tolerance="±0.5",
                                    ),
                                    SpecParameterOutput(
                                        name="material",
                                        value="AISI 1018 steel",
                                        unit="",
                                        tolerance="",
                                    ),
                                ],
                                verification_criteria=["Load test to 7.5kg"],
                            )
                        ],
                    ),
                    RequirementOutput(
                        id="R1.2",
                        statement="System SHALL attach to wall securely",
                        rationale="Mounting requirement",
                        specifications=[
                            SpecOutput(
                                id="S1.2.1",
                                description="Use 4x M8 bolts into concrete wall",
                                parameters=[
                                    SpecParameterOutput(
                                        name="bolt_count",
                                        value="4",
                                        unit="",
                                        tolerance="",
                                    ),
                                    SpecParameterOutput(
                                        name="bolt_size",
                                        value="M8",
                                        unit="",
                                        tolerance="",
                                    ),
                                ],
                                verification_criteria=["Pull test 100N per bolt"],
                            )
                        ],
                    ),
                ],
            )
        ],
        assumptions=[
            AssumptionOutput(
                id="A1",
                text="Wall can support 400N shear load",
                confidence="Likely",
                reasoning="Standard concrete wall assumption",
                affects="S1.2.1",
            ),
            AssumptionOutput(
                id="A2",
                text="Payload center of mass within 50mm of bracket",
                confidence="Uncertain",
                reasoning="Intent doesn't specify payload geometry",
                affects="S1.1.1",
            ),
        ],
    )


@pytest.fixture
def mock_llm_with_contracts():
    """Mock LLM returning valid contract extraction."""
    response = json.dumps(
        {
            "contracts": [
                {
                    "from_component": "Bracket",
                    "to_component": "Wall",
                    "assumptions": [
                        {
                            "text": "Wall can support 400N shear load",
                            "confidence": "Likely",
                            "source_spec_id": "S1.2.1",
                        }
                    ],
                    "guarantees": [
                        {
                            "text": "Bracket transmits max 400N to wall",
                            "confidence": "Confident",
                            "source_spec_id": "S1.1.1",
                        }
                    ],
                    "reasoning": "Bracket relies on wall strength for mounting stability",
                },
                {
                    "from_component": "Bracket",
                    "to_component": "Payload",
                    "assumptions": [
                        {
                            "text": "Payload center of mass within 50mm of bracket",
                            "confidence": "Uncertain",
                            "source_spec_id": "S1.1.1",
                        }
                    ],
                    "guarantees": [
                        {
                            "text": "Bracket supports 5kg load with deflection <1mm",
                            "confidence": "Confident",
                            "source_spec_id": "S1.1.1",
                        }
                    ],
                    "reasoning": "Bracket provides load capacity to payload",
                },
            ]
        }
    )
    return MockLLMClient(default_response=response)


def test_contract_schemas_valid():
    """Test contract schemas are valid and accessible."""
    term = ContractTermOutput(
        text="Wall can support 400N shear load",
        confidence="Likely",
        source_spec_id="S1.2.1",
    )

    contract = ContractOutput(
        from_component="Bracket",
        to_component="Wall",
        assumptions=[term],
        guarantees=[
            ContractTermOutput(
                text="Bracket transmits max 400N",
                confidence="Confident",
                source_spec_id="S1.1.1",
            )
        ],
        reasoning="Interface analysis",
    )

    output = ContractExtractionOutput(contracts=[contract])

    # Assert all fields accessible
    assert output.contracts[0].from_component == "Bracket"
    assert output.contracts[0].to_component == "Wall"
    assert len(output.contracts[0].assumptions) == 1
    assert len(output.contracts[0].guarantees) == 1
    assert output.contracts[0].assumptions[0].confidence == "Likely"


def test_extract_contracts_from_grs(engine, bracket_grs_tree, mock_llm_with_contracts):
    """Test extract_contracts() produces bidirectional A-G pairs."""
    from src.agents.contract_extraction import ContractExtractionAgent

    agent = ContractExtractionAgent(engine, mock_llm_with_contracts)
    result = agent.extract_contracts(bracket_grs_tree)

    # Assert result structure
    assert isinstance(result, ContractExtractionOutput)
    assert (
        len(result.contracts) >= 2
    ), "Should extract Bracket->Wall and Bracket->Payload"

    # Find Bracket->Wall contract
    bracket_wall = next(
        (
            c
            for c in result.contracts
            if c.from_component == "Bracket" and c.to_component == "Wall"
        ),
        None,
    )
    assert bracket_wall is not None, "Should extract Bracket->Wall interface"
    assert len(bracket_wall.assumptions) > 0, "Should have assumptions"
    assert len(bracket_wall.guarantees) > 0, "Should have guarantees"

    # Find Bracket->Payload contract
    bracket_payload = next(
        (
            c
            for c in result.contracts
            if c.from_component == "Bracket" and c.to_component == "Payload"
        ),
        None,
    )
    assert bracket_payload is not None, "Should extract Bracket->Payload interface"
    assert len(bracket_payload.assumptions) > 0, "Should have assumptions"
    assert len(bracket_payload.guarantees) > 0, "Should have guarantees"

    # Assert contract terms reference source specs
    for contract in result.contracts:
        for term in contract.assumptions + contract.guarantees:
            assert term.source_spec_id.startswith(
                ("S", "R", "G")
            ), "Terms should reference GRS items"


def test_extract_contracts_uses_structured_output(
    engine, bracket_grs_tree, mock_llm_with_contracts
):
    """Test agent uses LLM complete_json with ContractExtractionOutput schema."""
    from src.agents.contract_extraction import ContractExtractionAgent

    agent = ContractExtractionAgent(engine, mock_llm_with_contracts)
    agent.extract_contracts(bracket_grs_tree)

    # Mock LLM tracks calls
    assert mock_llm_with_contracts.call_count == 1, "Should call LLM once"


def test_save_contracts_to_hypergraph(engine, mock_llm_with_contracts):
    """Test save_to_hypergraph creates Contract nodes with SATISFIES edges."""
    from src.agents.contract_extraction import ContractExtractionAgent
    from src.hypergraph.models import Contract, EdgeType

    agent = ContractExtractionAgent(engine, mock_llm_with_contracts)

    # Create sample contracts with valid_regimes
    contracts = [
        ContractOutput(
            from_component="Bracket",
            to_component="Wall",
            assumptions=[
                ContractTermOutput(
                    text="Wall can support 400N shear load",
                    confidence="Likely",
                    source_spec_id="S1.2.1",
                )
            ],
            guarantees=[
                ContractTermOutput(
                    text="Bracket transmits max 400N to wall",
                    confidence="Confident",
                    source_spec_id="S1.1.1",
                )
            ],
            reasoning="Interface contract",
            valid_regimes=["Normal", "Fault"],
        )
    ]

    # Mock GRS mapping
    grs_mapping = {
        "G1": "goal-001",
        "R1.1": "req-001",
        "R1.2": "req-002",
        "S1.1.1": "spec-001",
        "S1.2.1": "spec-002",
    }

    # Add mock requirement nodes to engine
    from src.hypergraph.models import Requirement

    req1 = Requirement(
        id="req-001",
        description="Load requirement",
        statement="System SHALL support 5kg load",
    )
    req2 = Requirement(
        id="req-002",
        description="Mounting requirement",
        statement="System SHALL attach securely",
    )
    engine.add_node(req1)
    engine.add_node(req2)

    # Save contracts
    mapping = agent.save_to_hypergraph(contracts, grs_mapping)

    # Verify Contract node created
    assert "Bracket->Wall" in mapping
    contract_node_id = mapping["Bracket->Wall"]
    assert contract_node_id in engine.nodes

    contract_node = engine.get_node(contract_node_id)
    assert isinstance(contract_node, Contract)
    assert len(contract_node.assumptions) == 1
    assert len(contract_node.guarantees) == 1
    assert contract_node.valid_regimes == ["Normal", "Fault"]
    assert len(contract_node.parties) == 2

    # Verify SATISFIES edges exist
    satisfies_edges = [
        e for e in engine.edges.values() if e.edge_type == EdgeType.SATISFIES
    ]
    assert len(satisfies_edges) > 0, "Should create SATISFIES edges"

    # Verify edge connects contract to requirement
    edge = satisfies_edges[0]
    assert edge.source_id == contract_node_id
    assert edge.target_id in ["req-001", "req-002"]


def test_cli_save_contracts_integration(engine, mock_llm_with_contracts):
    """Test CLI save pattern: build grs_mapping from engine nodes and call save_to_hypergraph."""
    from src.agents.contract_extraction import ContractExtractionAgent
    from src.hypergraph.models import EdgeType, GoalNode, Requirement, SpecificationNode

    agent = ContractExtractionAgent(engine, mock_llm_with_contracts)

    # Simulate GRS nodes in hypergraph (with grs_id metadata as CLI expects)
    goal = GoalNode(
        id="goal-001",
        description="Support payload",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="System",
        metadata={"grs_id": "G1"},
    )
    req1 = Requirement(
        id="req-001",
        description="Load requirement",
        statement="System SHALL support 5kg load",
        metadata={"grs_id": "R1.1"},
    )
    req2 = Requirement(
        id="req-002",
        description="Mounting requirement",
        statement="System SHALL attach securely",
        metadata={"grs_id": "R1.2"},
    )
    spec1 = SpecificationNode(
        id="spec-001",
        description="Steel bracket",
        parameters=[],
        verification_criteria=[],
        metadata={"grs_id": "S1.1.1"},
    )
    spec2 = SpecificationNode(
        id="spec-002",
        description="M8 bolts",
        parameters=[],
        verification_criteria=[],
        metadata={"grs_id": "S1.2.1"},
    )

    engine.add_node(goal)
    engine.add_node(req1)
    engine.add_node(req2)
    engine.add_node(spec1)
    engine.add_node(spec2)

    # Build grs_mapping (CLI pattern)
    grs_mapping = {
        n.metadata.get("grs_id"): n.id
        for n in engine.nodes.values()
        if n.metadata.get("grs_id")
    }

    # Verify mapping built correctly
    assert grs_mapping == {
        "G1": "goal-001",
        "R1.1": "req-001",
        "R1.2": "req-002",
        "S1.1.1": "spec-001",
        "S1.2.1": "spec-002",
    }

    # Create sample contract
    contracts = [
        ContractOutput(
            from_component="Bracket",
            to_component="Wall",
            assumptions=[
                ContractTermOutput(
                    text="Wall can support 400N shear load",
                    confidence="Likely",
                    source_spec_id="S1.2.1",
                )
            ],
            guarantees=[
                ContractTermOutput(
                    text="Bracket transmits max 400N to wall",
                    confidence="Confident",
                    source_spec_id="S1.1.1",
                )
            ],
            reasoning="Interface contract",
            valid_regimes=["Normal"],
        )
    ]

    # Call save_to_hypergraph (CLI pattern)
    mapping = agent.save_to_hypergraph(contracts, grs_mapping)

    # Verify Contract node created
    assert "Bracket->Wall" in mapping
    contract_node_id = mapping["Bracket->Wall"]
    assert contract_node_id in engine.nodes

    # Verify SATISFIES edges created
    satisfies_edges = [
        e for e in engine.edges.values() if e.edge_type == EdgeType.SATISFIES
    ]
    assert (
        len(satisfies_edges) > 0
    ), "Should create SATISFIES edges from contract to requirements"
