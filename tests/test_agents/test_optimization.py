"""Tests for OptimizationAgent."""

import pytest

from src.agents.optimization import (
    OPTIMIZATION_AVAILABLE,
    OptimizationAgent,
)


class MockEngine:
    """Mock hypergraph engine for testing."""

    def __init__(self, evidence_nodes=None):
        self.evidence_nodes = evidence_nodes or []
        self.updates = {}

    def get_nodes_by_type(self, node_type):
        return self.evidence_nodes


class MockEvidence:
    """Mock Evidence node for testing."""

    def __init__(self, evidence_id, data):
        self.id = evidence_id
        self.data = data


class TestOptimizationAgent:
    """Tests for OptimizationAgent."""

    def test_init(self):
        """Test agent initialization."""
        engine = MockEngine()
        agent = OptimizationAgent(engine=engine, llm=None)
        assert agent.name == "OptimizationAgent"

    def test_no_evidence_nodes(self):
        """Test with no evidence nodes."""
        engine = MockEngine(evidence_nodes=[])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert len(mutation.nodes_to_update) == 0

    def test_info_severity_skipped(self):
        """Test that INFO severity findings are skipped."""
        evidence = MockEvidence(
            "evidence_001",
            {
                "rule_id": "mech.hole_min_diameter",
                "severity": "INFO",
                "measured_value": {"value": 1.0, "unit": "mm"},
            },
        )
        engine = MockEngine(evidence_nodes=[evidence])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert len(mutation.nodes_to_update) == 0


@pytest.mark.skipif(not OPTIMIZATION_AVAILABLE, reason="NLopt not available")
class TestOptimizationAgentWithNLopt:
    """Tests that require NLopt to be available."""

    def test_hole_diameter_optimization(self):
        """Test hole diameter optimization."""
        evidence = MockEvidence(
            "evidence_001",
            {
                "rule_id": "mech.hole_min_diameter",
                "severity": "ERROR",
                "measured_value": {"value": 0.3, "unit": "mm"},
                "limit": {"value": 0.5, "unit": "mm"},
            },
        )
        engine = MockEngine(evidence_nodes=[evidence])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert "evidence_001" in mutation.nodes_to_update
        computed_fix = mutation.nodes_to_update["evidence_001"]["data"]["computed_fix"]
        assert computed_fix["type"] == "hole_diameter"
        assert computed_fix["optimized_diameter"] >= 0.5

    def test_hole_ld_ratio_optimization(self):
        """Test hole L/D ratio optimization."""
        evidence = MockEvidence(
            "evidence_002",
            {
                "rule_id": "mech.hole_max_ld_ratio",
                "severity": "ERROR",
                "measured_value": {"value": 15.0},  # L/D ratio
                "limit": {"max_ratio": 10.0},
                "raw": {"diameter": 5.0, "depth": 75.0},
            },
        )
        engine = MockEngine(evidence_nodes=[evidence])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert "evidence_002" in mutation.nodes_to_update
        computed_fix = mutation.nodes_to_update["evidence_002"]["data"]["computed_fix"]
        assert computed_fix["type"] == "hole_ld"
        assert computed_fix["new_ld_ratio"] <= 10.0

    def test_wall_thickness_optimization(self):
        """Test wall thickness optimization."""
        evidence = MockEvidence(
            "evidence_003",
            {
                "rule_id": "mech.wall_thickness",
                "severity": "WARN",
                "measured_value": {"value": 0.8, "unit": "mm"},
                "limit": {"value": 1.0, "unit": "mm"},
            },
        )
        engine = MockEngine(evidence_nodes=[evidence])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert "evidence_003" in mutation.nodes_to_update
        computed_fix = mutation.nodes_to_update["evidence_003"]["data"]["computed_fix"]
        assert computed_fix["type"] == "wall_thickness"
        assert computed_fix["optimized_thickness"] >= 1.0

    def test_fillet_radius_optimization(self):
        """Test fillet radius optimization."""
        evidence = MockEvidence(
            "evidence_004",
            {
                "rule_id": "mech.fillet_min_radius",
                "severity": "ERROR",
                "measured_value": {"value": 0.1, "unit": "mm"},
                "limit": {"value": 0.2, "unit": "mm"},
            },
        )
        engine = MockEngine(evidence_nodes=[evidence])
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        assert "evidence_004" in mutation.nodes_to_update
        computed_fix = mutation.nodes_to_update["evidence_004"]["data"]["computed_fix"]
        assert computed_fix["type"] == "fillet_radius"
        assert computed_fix["optimized_radius"] >= 0.2

    def test_multiple_violations(self):
        """Test multiple DFM violations are all optimized."""
        evidence_nodes = [
            MockEvidence(
                "evidence_001",
                {
                    "rule_id": "mech.hole_min_diameter",
                    "severity": "ERROR",
                    "measured_value": {"value": 0.3, "unit": "mm"},
                    "limit": {"value": 0.5, "unit": "mm"},
                },
            ),
            MockEvidence(
                "evidence_002",
                {
                    "rule_id": "mech.fillet_min_radius",
                    "severity": "WARN",
                    "measured_value": {"value": 0.1, "unit": "mm"},
                    "limit": {"value": 0.2, "unit": "mm"},
                },
            ),
            MockEvidence(
                "evidence_003",
                {
                    "rule_id": "mech.hole_min_diameter",
                    "severity": "INFO",  # Should be skipped
                    "measured_value": {"value": 1.0, "unit": "mm"},
                },
            ),
        ]
        engine = MockEngine(evidence_nodes=evidence_nodes)
        agent = OptimizationAgent(engine=engine, llm=None)

        from src.agents.base import Trigger, TriggerType

        trigger = Trigger(trigger_type=TriggerType.VERIFICATION_COMPLETE, data={})
        mutation = agent.propose_mutation(trigger)

        # Should optimize 2 (not the INFO one)
        assert len(mutation.nodes_to_update) == 2
        assert "evidence_001" in mutation.nodes_to_update
        assert "evidence_002" in mutation.nodes_to_update
        assert "evidence_003" not in mutation.nodes_to_update


class TestComputeFixHelpers:
    """Tests for helper methods."""

    def test_extract_value_from_dict(self):
        """Test extracting value from dict."""
        engine = MockEngine()
        agent = OptimizationAgent(engine=engine, llm=None)

        assert agent._extract_value({"value": 1.5, "unit": "mm"}) == 1.5
        assert agent._extract_value({"value": 10}) == 10

    def test_extract_value_from_scalar(self):
        """Test extracting value from scalar."""
        engine = MockEngine()
        agent = OptimizationAgent(engine=engine, llm=None)

        assert agent._extract_value(1.5) == 1.5
        assert agent._extract_value(10) == 10.0

    def test_extract_value_none(self):
        """Test extracting value from None."""
        engine = MockEngine()
        agent = OptimizationAgent(engine=engine, llm=None)

        assert agent._extract_value(None) is None
        assert agent._extract_value({}) is None
