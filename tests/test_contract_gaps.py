"""Tests for contract extraction gap closure (UAT issues).

Tests:
1. GRS tree reconstruction from hypergraph (HAS_CHILD edges)
2. Spec citation display in contract terms
3. Contract replacement (not accumulation)
4. SATISFIES edges from contracts to requirements
"""

import pytest

from src import config
from src.agents.contract_extraction import (
    ContractExtractionAgent,
    # reconstruct_grs_tree,  # Will be added in Task 2
    # format_term_with_citation,  # Will be added in Task 2
)
from src.agents.llm import LLMClient
from src.agents.schemas import ContractOutput, ContractTermOutput
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    EdgeType,
    GoalNode,
    NodeType,
    Requirement,
    SpecificationNode,
)
from src.hypergraph.store import HypergraphStore

# Verify schema field exists

assert (
    "source_spec_id" in ContractTermOutput.model_fields
), "ContractTermOutput missing source_spec_id field"


@pytest.fixture
def engine():
    """Create test engine with in-memory store."""
    store = HypergraphStore(path=":memory:")
    engine = HypergraphEngine(store)
    return engine


@pytest.fixture
def populated_engine(engine):
    """Engine with G->R->S hierarchy for testing reconstruction."""
    # Create Goal G1
    goal = GoalNode(
        id="goal_test_1",
        description="Bracket securely mounts to wall",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="system",
        metadata={
            "grs_id": "G1",
            "assumptions": [
                {
                    "id": "A1",
                    "text": "Wall is solid",
                    "confidence": "Likely",
                    "reasoning": "Standard construction",
                    "affects": "G1",
                }
            ],
        },
    )
    engine.add_node(goal)

    # Create Requirement R1.1
    req = Requirement(
        id="req_test_1",
        description="Bracket SHALL support 5kg load",
        statement="Bracket SHALL support 5kg load",
        rationale="User specified load",
        metadata={
            "grs_id": "R1.1",
            "assumptions": [
                {
                    "id": "A2",
                    "text": "Static load only",
                    "confidence": "Confident",
                    "reasoning": "No mention of dynamic",
                    "affects": "R1.1",
                }
            ],
        },
    )
    engine.add_node(req)

    # Create Spec S1.1.1
    spec = SpecificationNode(
        id="spec_test_1",
        description="Material: AISI 1018 steel, thickness 2.0mm",
        metadata={
            "grs_id": "S1.1.1",
            "parameters": [
                {"name": "material", "value": "AISI 1018", "unit": "", "tolerance": ""},
                {
                    "name": "thickness",
                    "value": "2.0",
                    "unit": "mm",
                    "tolerance": "±0.1",
                },
            ],
            "verification_criteria": [
                "Material certification",
                "Thickness measurement",
            ],
        },
    )
    engine.add_node(spec)

    # Wire with HAS_CHILD edges: G1 -> R1.1 -> S1.1.1
    engine.add_edge(goal.id, req.id, EdgeType.HAS_CHILD)
    engine.add_edge(req.id, spec.id, EdgeType.HAS_CHILD)

    return engine


def test_grs_tree_reconstruction_includes_full_hierarchy(populated_engine):
    """Test that reconstruct_grs_tree builds full G->R->S tree from HAS_CHILD edges."""
    from src.agents.contract_extraction import reconstruct_grs_tree

    grs_tree = reconstruct_grs_tree(populated_engine)

    # Verify structure
    assert len(grs_tree.goals) == 1, "Should have 1 goal"
    goal = grs_tree.goals[0]
    assert goal.id == "G1", "Goal ID should be G1"
    assert len(goal.requirements) == 1, "Goal should have 1 requirement"

    req = goal.requirements[0]
    assert req.id == "R1.1", "Requirement ID should be R1.1"
    assert len(req.specifications) == 1, "Requirement should have 1 spec"

    spec = req.specifications[0]
    assert spec.id == "S1.1.1", "Spec ID should be S1.1.1"
    assert len(spec.parameters) == 2, "Spec should have 2 parameters"
    assert len(spec.verification_criteria) == 2, "Spec should have 2 criteria"

    # Verify assumptions collected
    assert len(grs_tree.assumptions) >= 1, "Should collect assumptions from nodes"


def test_contract_terms_include_spec_citations():
    """Test that format_term_with_citation adds [source_spec_id] suffix."""
    from src.agents.contract_extraction import format_term_with_citation

    term = ContractTermOutput(
        text="Deflection <= 1.0mm",
        confidence="Confident",
        source_spec_id="S1.1.1",
    )

    formatted = format_term_with_citation(term)

    assert "[S1.1.1]" in formatted, "Should include spec citation"
    assert "Deflection <= 1.0mm" in formatted, "Should include term text"


def test_save_contracts_replaces_existing(engine):
    """Test that save_to_hypergraph with replace_existing removes old contracts."""
    # Setup: Add 2 existing contracts manually
    from src.hypergraph.models import Contract, ContractParty

    old1 = Contract(
        id="old_contract_1",
        description="Old contract 1",
        assumptions=["Old assumption"],
        guarantees=["Old guarantee"],
        valid_regimes=["Normal"],
        parties=[
            ContractParty(node_id="A", role="provider", variables=[]),
            ContractParty(node_id="B", role="consumer", variables=[]),
        ],
    )
    old2 = Contract(
        id="old_contract_2",
        description="Old contract 2",
        assumptions=["Old assumption 2"],
        guarantees=["Old guarantee 2"],
        valid_regimes=["Normal"],
        parties=[
            ContractParty(node_id="C", role="provider", variables=[]),
            ContractParty(node_id="D", role="consumer", variables=[]),
        ],
    )
    engine.add_node(old1)
    engine.add_node(old2)

    # Create agent and new contracts
    llm = LLMClient(api_key=config.OPENAI_API_KEY)
    agent = ContractExtractionAgent(engine, llm)

    new_contract = ContractOutput(
        from_component="Bracket",
        to_component="Wall",
        assumptions=[
            ContractTermOutput(
                text="Wall provides anchor points",
                confidence="Likely",
                source_spec_id="S1.1.1",
            )
        ],
        guarantees=[
            ContractTermOutput(
                text="Bracket distributes load",
                confidence="Confident",
                source_spec_id="S1.1.2",
            )
        ],
        reasoning="Test contract",
        valid_regimes=["Normal"],
    )

    # Save with replace_existing=True
    grs_mapping = {}
    agent.save_to_hypergraph([new_contract], grs_mapping, replace_existing=True)

    # Verify: Only new contract exists
    contracts = engine.get_nodes_by_type(NodeType.CONTRACT)
    assert len(contracts) == 1, "Should have exactly 1 contract after replacement"
    assert (
        "Bracket" in contracts[0].description
    ), "Should be the new contract, not old ones"


def test_satisfies_edges_created_from_source_spec_id(engine):
    """Test that SATISFIES edges link contracts to requirements via source_spec_id."""
    # Setup: Create GRS hierarchy with grs_id in metadata
    goal = GoalNode(
        id="goal_1",
        description="Test goal",
        goal_type="ACHIEVE",
        refinement_type="AND",
        agent="system",
        metadata={"grs_id": "G1"},
    )
    req = Requirement(
        id="req_1",
        description="Test requirement",
        statement="Test requirement SHALL do something",
        metadata={"grs_id": "R1.1"},
    )
    spec = SpecificationNode(
        id="spec_1",
        description="Test spec",
        metadata={"grs_id": "S1.1.1"},
    )
    engine.add_node(goal)
    engine.add_node(req)
    engine.add_node(spec)
    engine.add_edge(goal.id, req.id, EdgeType.HAS_CHILD)
    engine.add_edge(req.id, spec.id, EdgeType.HAS_CHILD)

    # Create grs_mapping
    grs_mapping = {
        "G1": goal.id,
        "R1.1": req.id,
        "S1.1.1": spec.id,
    }

    # Create contract with terms referencing S1.1.1
    llm = LLMClient(api_key=config.OPENAI_API_KEY)
    agent = ContractExtractionAgent(engine, llm)

    contract = ContractOutput(
        from_component="Bracket",
        to_component="Wall",
        assumptions=[
            ContractTermOutput(
                text="Wall provides anchor points",
                confidence="Likely",
                source_spec_id="S1.1.1",
            )
        ],
        guarantees=[
            ContractTermOutput(
                text="Bracket distributes load",
                confidence="Confident",
                source_spec_id="S1.1.1",
            )
        ],
        reasoning="Test contract",
        valid_regimes=["Normal"],
    )

    # Save contract
    agent.save_to_hypergraph([contract], grs_mapping)

    # Verify SATISFIES edge exists from contract to requirement
    satisfies_edges = engine.get_edges_by_type(EdgeType.SATISFIES)
    assert len(satisfies_edges) > 0, "Should have at least 1 SATISFIES edge"

    # Find contract node
    contracts = engine.get_nodes_by_type(NodeType.CONTRACT)
    assert len(contracts) == 1, "Should have 1 contract"
    contract_node_id = contracts[0].id

    # Verify edge connects contract to requirement
    edge_found = False
    for edge in satisfies_edges:
        if edge.source_id == contract_node_id and edge.target_id == req.id:
            edge_found = True
            break

    assert edge_found, "SATISFIES edge should connect contract to requirement R1.1"
