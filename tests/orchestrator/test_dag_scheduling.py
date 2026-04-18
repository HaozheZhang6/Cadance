from __future__ import annotations

from src.orchestrator.context import BudgetAllocation
from src.orchestrator.dag import DAG, DAGNode


def _budget() -> BudgetAllocation:
    return BudgetAllocation(
        cost_usd=1.0,
        time_seconds=10.0,
        token_budget=100,
        sigma_threshold=0.7,
        max_retries=1,
    )


def test_group_by_coupling() -> None:
    dag = DAG()
    n1 = DAGNode(
        id="n1",
        agent_type="decomposition",
        goal="root",
        parent_id=None,
        budget=_budget(),
    )
    n2 = DAGNode(
        id="n2",
        agent_type="decomposition",
        goal="child",
        parent_id="n1",
        coupling_groups=["shared"],
        budget=_budget(),
    )
    n3 = DAGNode(
        id="n3",
        agent_type="decomposition",
        goal="child2",
        parent_id="n1",
        coupling_groups=["shared"],
        budget=_budget(),
    )
    dag.add_node(n1)
    dag.add_node(n2)
    dag.add_node(n3)

    ready = dag.get_ready_nodes()
    groups = dag.group_by_coupling(ready)

    assert any({"n2", "n3"} == {n.id for n in group} for group in groups)


def test_topological_sort_respects_dependencies() -> None:
    dag = DAG()
    n1 = DAGNode(
        id="n1",
        agent_type="decomposition",
        goal="root",
        parent_id=None,
        budget=_budget(),
    )
    n2 = DAGNode(
        id="n2",
        agent_type="cad",
        goal="leaf",
        parent_id="n1",
        budget=_budget(),
    )
    dag.add_node(n1)
    dag.add_node(n2)
    dag.add_edge("n1", "n2")

    order = dag.topological_sort()
    assert order.index("n1") < order.index("n2")
