"""Tests for new node types (Goal, Obstacle, Softgoal, Specification)."""

from src.hypergraph.models import (
    ArtifactNode,
    Contract,
    ContractParty,
    Edge,
    EdgeType,
    GoalNode,
    NodeType,
    ObstacleNode,
    SoftgoalNode,
    SpecificationNode,
    SpecParameter,
    ToolInvocationNode,
)
from src.hypergraph.store import NODE_TYPE_MAP, HypergraphStore


def test_goal_node_creation():
    """Test GoalNode creation with all fields."""
    goal = GoalNode(
        id="g1",
        description="System shall operate safely",
        goal_type="MAINTAIN",
        refinement_type="AND",
        agent="SafetyController",
        obstacle_ids=["obs1", "obs2"],
        tbd_fields=["environmental_conditions"],
    )

    assert goal.node_type == NodeType.GOAL
    assert goal.goal_type == "MAINTAIN"
    assert goal.refinement_type == "AND"
    assert goal.agent == "SafetyController"
    assert len(goal.obstacle_ids) == 2
    assert "environmental_conditions" in goal.tbd_fields


def test_obstacle_node_creation():
    """Test ObstacleNode creation."""
    obstacle = ObstacleNode(
        id="obs1",
        description="Power supply failure",
        severity="CRITICAL",
        mitigated_by=["req1", "req2"],
    )

    assert obstacle.node_type == NodeType.OBSTACLE
    assert obstacle.severity == "CRITICAL"
    assert len(obstacle.mitigated_by) == 2


def test_softgoal_node_creation():
    """Test SoftgoalNode creation."""
    softgoal = SoftgoalNode(
        id="sg1",
        description="System should be maintainable",
        name="Maintainability",
        type="QUALITY_ATTRIBUTE",
        satisfaction_level="WEAKLY_SATISFIED",
    )

    assert softgoal.node_type == NodeType.SOFTGOAL
    assert softgoal.name == "Maintainability"
    assert softgoal.type == "QUALITY_ATTRIBUTE"
    assert softgoal.satisfaction_level == "WEAKLY_SATISFIED"


def test_spec_parameter_creation():
    """Test SpecParameter model."""
    param = SpecParameter(
        name="load_capacity",
        value=5.0,
        unit="kg",
        tolerance="±0.1",
        confidence=0.95,
    )

    assert param.name == "load_capacity"
    assert param.value == 5.0
    assert param.unit == "kg"
    assert param.tolerance == "±0.1"
    assert param.confidence == 0.95


def test_specification_node_creation():
    """Test SpecificationNode creation."""
    param1 = SpecParameter(name="length", value=100, unit="mm", confidence=1.0)
    param2 = SpecParameter(name="width", value=50, unit="mm", confidence=0.9)

    spec = SpecificationNode(
        id="spec1",
        description="Mounting bracket specification",
        derives_from=["req1", "goal1"],
        parameters=[param1, param2],
        design_decisions=[
            {
                "decision": "Use aluminum alloy",
                "rationale": "Weight and strength balance",
                "alternatives": "Steel, titanium",
            }
        ],
        verification_criteria=["FEA analysis", "Physical load test"],
        formal_repr="load <= 50N AND stress < yield_strength",
    )

    assert spec.node_type == NodeType.SPECIFICATION
    assert len(spec.derives_from) == 2
    assert len(spec.parameters) == 2
    assert spec.parameters[0].name == "length"
    assert len(spec.design_decisions) == 1
    assert len(spec.verification_criteria) == 2
    assert "FEA analysis" in spec.verification_criteria


def test_artifact_node_creation():
    """Test ArtifactNode creation."""
    artifact = ArtifactNode(
        id="artifact_001",
        description="STEP input artifact",
        artifact_type="step",
        uri="file:///tmp/part.step",
        sha256="deadbeef",
        media_type="model/step",
        role="input",
        size_bytes=1024,
        meta={"source": "fixture"},
    )

    assert artifact.node_type == NodeType.ARTIFACT
    assert artifact.artifact_type == "step"
    assert artifact.uri == "file:///tmp/part.step"
    assert artifact.role == "input"
    assert artifact.size_bytes == 1024


def test_tool_invocation_node_creation():
    """Test ToolInvocationNode creation."""
    invocation = ToolInvocationNode(
        id="tool_001",
        description="mech-verify invocation",
        tool_name="mech-verify",
        tool_version="1.0.0",
        inputs={"path": "part.step"},
        outputs={"report": "report.json"},
        exit_code=0,
        status="success",
        duration_ms=1200.0,
        config_hash="abc123",
    )

    assert invocation.node_type == NodeType.TOOL_INVOCATION
    assert invocation.tool_name == "mech-verify"
    assert invocation.status == "success"
    assert invocation.exit_code == 0


def test_contract_party_creation():
    """Test ContractParty model."""
    party = ContractParty(
        node_id="contract1",
        role="provider",
        variables=["input_voltage", "output_current"],
    )

    assert party.node_id == "contract1"
    assert party.role == "provider"
    assert len(party.variables) == 2


def test_contract_with_parties():
    """Test updated Contract with parties field."""
    party1 = ContractParty(node_id="c1", role="provider", variables=["v1"])
    party2 = ContractParty(node_id="c2", role="consumer", variables=["v2"])

    contract = Contract(
        id="contract1",
        description="Multi-party contract",
        parties=[party1, party2],
        formal_repr="v1 > 0 AND v2 < 10",
        valid_regimes=["normal", "fault_tolerant"],
    )

    assert len(contract.parties) == 2
    assert contract.parties[0].role == "provider"
    assert contract.formal_repr == "v1 > 0 AND v2 < 10"
    assert "normal" in contract.valid_regimes


def test_new_edge_types():
    """Test new EdgeType values."""
    edge1 = Edge(
        id="e1",
        source_id="g1",
        target_id="g2",
        edge_type=EdgeType.REFINES,
    )

    edge2 = Edge(
        id="e2",
        source_id="req1",
        target_id="obs1",
        edge_type=EdgeType.MITIGATES,
    )

    edge3 = Edge(
        id="e3",
        source_id="sg1",
        target_id="sg2",
        edge_type=EdgeType.CONTRIBUTES_TO,
    )

    edge4 = Edge(
        id="e4",
        source_id="tool_001",
        target_id="artifact_001",
        edge_type=EdgeType.GENERATED,
    )

    edge5 = Edge(
        id="e5",
        source_id="artifact_001",
        target_id="evidence_001",
        edge_type=EdgeType.EVIDENCES,
    )

    edge6 = Edge(
        id="e6",
        source_id="tool_001",
        target_id="unknown_001",
        edge_type=EdgeType.RAISES,
    )

    assert edge1.edge_type == EdgeType.REFINES
    assert edge2.edge_type == EdgeType.MITIGATES
    assert edge3.edge_type == EdgeType.CONTRIBUTES_TO
    assert edge4.edge_type == EdgeType.GENERATED
    assert edge5.edge_type == EdgeType.EVIDENCES
    assert edge6.edge_type == EdgeType.RAISES


def test_node_type_map_registration():
    """Test all new node types registered in NODE_TYPE_MAP."""
    assert NodeType.GOAL in NODE_TYPE_MAP
    assert NodeType.OBSTACLE in NODE_TYPE_MAP
    assert NodeType.SOFTGOAL in NODE_TYPE_MAP
    assert NodeType.SPECIFICATION in NODE_TYPE_MAP
    assert NodeType.ARTIFACT in NODE_TYPE_MAP
    assert NodeType.TOOL_INVOCATION in NODE_TYPE_MAP

    assert NODE_TYPE_MAP[NodeType.GOAL] == GoalNode
    assert NODE_TYPE_MAP[NodeType.OBSTACLE] == ObstacleNode
    assert NODE_TYPE_MAP[NodeType.SOFTGOAL] == SoftgoalNode
    assert NODE_TYPE_MAP[NodeType.SPECIFICATION] == SpecificationNode
    assert NODE_TYPE_MAP[NodeType.ARTIFACT] == ArtifactNode
    assert NODE_TYPE_MAP[NodeType.TOOL_INVOCATION] == ToolInvocationNode


def test_serialization_round_trip(tmp_path):
    """Test serialization and deserialization of new node types."""
    store_path = tmp_path / "test_graph.json"
    store = HypergraphStore(store_path)

    # Create nodes of each new type
    goal = GoalNode(
        id="g1",
        description="Test goal",
        goal_type="ACHIEVE",
        refinement_type="OR",
        agent="TestAgent",
    )

    obstacle = ObstacleNode(
        id="obs1",
        description="Test obstacle",
        severity="HIGH",
    )

    softgoal = SoftgoalNode(
        id="sg1",
        description="Test softgoal",
        name="Usability",
        type="QUALITY_ATTRIBUTE",
    )

    spec = SpecificationNode(
        id="spec1",
        description="Test spec",
        parameters=[SpecParameter(name="x", value=10, unit="mm")],
    )

    artifact = ArtifactNode(
        id="artifact_001",
        description="Ops program artifact",
        artifact_type="ops_program",
        path="/tmp/ops.json",
        media_type="application/json",
        role="input",
    )

    invocation = ToolInvocationNode(
        id="tool_001",
        description="Tool invocation",
        tool_name="mech-verify",
        tool_version="1.0.0",
        status="success",
    )

    nodes = {
        "g1": goal,
        "obs1": obstacle,
        "sg1": softgoal,
        "spec1": spec,
        "artifact_001": artifact,
        "tool_001": invocation,
    }

    edges = {}

    # Save
    store.save(nodes, edges)

    # Load
    loaded_nodes, loaded_edges = store.load()

    # Verify all nodes loaded correctly
    assert len(loaded_nodes) == 6
    assert isinstance(loaded_nodes["g1"], GoalNode)
    assert isinstance(loaded_nodes["obs1"], ObstacleNode)
    assert isinstance(loaded_nodes["sg1"], SoftgoalNode)
    assert isinstance(loaded_nodes["spec1"], SpecificationNode)
    assert isinstance(loaded_nodes["artifact_001"], ArtifactNode)
    assert isinstance(loaded_nodes["tool_001"], ToolInvocationNode)

    # Verify data integrity
    assert loaded_nodes["g1"].goal_type == "ACHIEVE"
    assert loaded_nodes["obs1"].severity == "HIGH"
    assert loaded_nodes["sg1"].name == "Usability"
    assert loaded_nodes["spec1"].parameters[0].name == "x"
    assert loaded_nodes["artifact_001"].artifact_type == "ops_program"
    assert loaded_nodes["tool_001"].tool_name == "mech-verify"


def test_goal_with_obstacles_reference():
    """Test GoalNode references ObstacleNode IDs."""
    goal = GoalNode(
        id="g1",
        description="Safe operation",
        goal_type="MAINTAIN",
        refinement_type="AND",
        agent="Controller",
        obstacle_ids=["obs1", "obs2", "obs3"],
    )

    assert len(goal.obstacle_ids) == 3
    assert "obs1" in goal.obstacle_ids


def test_specification_derives_from_multiple():
    """Test SpecificationNode derives_from links to requirements and goals."""
    spec = SpecificationNode(
        id="spec1",
        description="Derived spec",
        derives_from=["req1", "req2", "goal1"],
    )

    assert len(spec.derives_from) == 3
    assert "req1" in spec.derives_from
    assert "goal1" in spec.derives_from
