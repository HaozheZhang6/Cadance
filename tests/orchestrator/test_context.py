from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.orchestrator.context import AgentContext, BudgetAllocation, BudgetUsage


def test_agent_context_is_immutable(tmp_path: Path) -> None:
    budget = BudgetAllocation(
        cost_usd=1.0,
        time_seconds=10.0,
        token_budget=100,
        sigma_threshold=0.7,
        max_retries=1,
    )
    ctx = AgentContext(
        agent_id="agent_001",
        agent_type="decomposition",
        dag_node_id="node_001",
        goal="Test goal",
        parent_contracts=[],
        resolved_constraints=set(),
        budget=budget,
        workspace=tmp_path / "agent_001",
        model="mock",
        max_turns=3,
        temperature=0.3,
    )

    with pytest.raises(FrozenInstanceError):
        ctx.agent_id = "new_id"  # type: ignore[misc]


def test_budget_helpers() -> None:
    budget = BudgetAllocation(
        cost_usd=10.0,
        time_seconds=100.0,
        token_budget=1000,
        sigma_threshold=0.7,
        max_retries=2,
    )
    usage = BudgetUsage(cost_usd=8.5, time_seconds=20.0, tokens=100)

    assert budget.is_warning(usage)
    assert not budget.is_exceeded(usage)

    usage.add(cost_usd=3.0)
    assert budget.is_exceeded(usage)
