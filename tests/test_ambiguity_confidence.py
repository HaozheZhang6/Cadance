"""Tests for severity-confidence matrix in AmbiguityDetectionAgent."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.ambiguity_detection import (
    SEVERITY_CONFIDENCE_MAP,
    AmbiguityDetectionAgent,
)
from src.agents.schemas import Ambiguity, AmbiguityAnalysis


class TestSeverityConfidenceMap:
    """Tests for SEVERITY_CONFIDENCE_MAP constant."""

    def test_severity_confidence_map_values(self):
        """Map has correct values: CRITICAL->0.3, HIGH->0.5, MEDIUM->0.75, LOW->0.95."""
        assert SEVERITY_CONFIDENCE_MAP["CRITICAL"] == 0.3
        assert SEVERITY_CONFIDENCE_MAP["HIGH"] == 0.5
        assert SEVERITY_CONFIDENCE_MAP["MEDIUM"] == 0.75
        assert SEVERITY_CONFIDENCE_MAP["LOW"] == 0.95

    def test_severity_confidence_map_completeness(self):
        """Map contains all 4 severity levels."""
        assert len(SEVERITY_CONFIDENCE_MAP) == 4
        assert set(SEVERITY_CONFIDENCE_MAP.keys()) == {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
        }


class TestComputeConfidenceFromSeverity:
    """Tests for _compute_confidence_from_severity helper."""

    @pytest.fixture
    def agent(self):
        """Create agent with mocked dependencies."""
        engine = MagicMock()
        llm = MagicMock()
        return AmbiguityDetectionAgent(engine, llm)

    def test_empty_ambiguities_returns_low_equivalent(self, agent):
        """No ambiguities = 0.95 (LOW equivalent)."""
        result = agent._compute_confidence_from_severity([])
        assert result == 0.95

    def test_critical_ambiguity_returns_0_3(self, agent):
        """CRITICAL severity -> 0.3 confidence."""
        amb = MagicMock(severity="CRITICAL")
        result = agent._compute_confidence_from_severity([amb])
        assert result == 0.3

    def test_high_ambiguity_returns_0_5(self, agent):
        """HIGH severity -> 0.5 confidence."""
        amb = MagicMock(severity="HIGH")
        result = agent._compute_confidence_from_severity([amb])
        assert result == 0.5

    def test_medium_ambiguity_returns_0_75(self, agent):
        """MEDIUM severity -> 0.75 confidence."""
        amb = MagicMock(severity="MEDIUM")
        result = agent._compute_confidence_from_severity([amb])
        assert result == 0.75

    def test_low_ambiguity_returns_0_95(self, agent):
        """LOW severity -> 0.95 confidence."""
        amb = MagicMock(severity="LOW")
        result = agent._compute_confidence_from_severity([amb])
        assert result == 0.95

    def test_worst_severity_wins(self, agent):
        """Multiple ambiguities: worst (lowest confidence) severity wins."""
        ambs = [
            MagicMock(severity="LOW"),
            MagicMock(severity="CRITICAL"),
            MagicMock(severity="MEDIUM"),
        ]
        result = agent._compute_confidence_from_severity(ambs)
        assert result == 0.3  # CRITICAL is worst

    def test_unknown_severity_defaults_to_0_5(self, agent):
        """Unknown severity level defaults to 0.5."""
        amb = MagicMock(severity="UNKNOWN_LEVEL")
        result = agent._compute_confidence_from_severity([amb])
        assert result == 0.5


class TestProposeMutationUsesSeverity:
    """Tests that propose_mutation uses severity-derived confidence."""

    def test_propose_mutation_uses_severity_not_llm(self):
        """Node confidence comes from severity matrix, not LLM overall_confidence."""
        engine = MagicMock()
        llm = MagicMock()

        # Create mock goal
        goal = MagicMock()
        goal.id = "goal_1"
        goal.description = "Test goal"
        goal.metadata = {}
        goal.tbd_fields = []
        goal.confidence = 1.0

        engine.get_nodes_by_type.return_value = [goal]

        agent = AmbiguityDetectionAgent(engine, llm)

        # Mock LLM response with arbitrary overall_confidence
        llm_response = AmbiguityAnalysis(
            goal_id="goal_1",
            goal_description="Test goal",
            ambiguities=[
                Ambiguity(
                    reasoning="Test",
                    ambiguity_type="VAGUENESS",
                    severity="CRITICAL",
                    location="test",
                    suggested_resolution="fix it",
                    options=["a", "b"],
                    confidence_if_resolved=0.9,
                )
            ],
            overall_confidence=0.77,  # Arbitrary LLM value - should be IGNORED
        )

        with patch.object(agent, "_analyze_goal", return_value=llm_response):
            mutation = agent.propose_mutation(MagicMock())

        # Verify confidence comes from severity matrix (CRITICAL=0.3), not LLM (0.77)
        assert "goal_1" in mutation.nodes_to_update
        assert mutation.nodes_to_update["goal_1"]["confidence"] == 0.3
