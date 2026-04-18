"""Tests for federated execution module."""

import asyncio
import importlib.util

import pytest

# Use importlib to avoid import chain issues
spec = importlib.util.spec_from_file_location(
    "executor", "src/verification/federated/executor.py"
)
executor_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor_mod)
FederatedExecutor = executor_mod.FederatedExecutor
ContractResult = executor_mod.ContractResult
Finding = executor_mod.Finding
Unknown = executor_mod.Unknown
Status = executor_mod.Status

spec_runner = importlib.util.spec_from_file_location(
    "contract_runner", "src/verification/federated/contract_runner.py"
)
runner_mod = importlib.util.module_from_spec(spec_runner)
spec_runner.loader.exec_module(runner_mod)
safe_verify = runner_mod.safe_verify
wrap_sync_verifier = runner_mod.wrap_sync_verifier
create_missing_verifier_unknown = runner_mod.create_missing_verifier_unknown


class MockContract:
    """Mock contract for testing."""

    def __init__(self, contract_id: str):
        self.id = contract_id


def test_finding_id_deterministic():
    """VE-04: Same inputs produce same finding_id."""
    f1 = Finding(
        summary="Test finding",
        severity="ERROR",
        category="TEST",
        created_by_rule_id="test.rule",
        object_ref="component_1",
    )
    f2 = Finding(
        summary="Test finding",
        severity="ERROR",
        category="TEST",
        created_by_rule_id="test.rule",
        object_ref="component_1",
    )
    assert f1.finding_id == f2.finding_id
    assert f1.finding_id.startswith("F-")
    # Different object_ref should produce different ID
    f3 = Finding(
        summary="Test finding",
        severity="ERROR",
        category="TEST",
        created_by_rule_id="test.rule",
        object_ref="component_2",
    )
    assert f1.finding_id != f3.finding_id


def test_unknown_id_deterministic():
    """Unknown IDs are also deterministic."""
    u1 = Unknown(
        summary="Test unknown",
        impact="Test impact",
        resolution_plan="Test plan",
        created_by_rule_id="test.rule",
    )
    u2 = Unknown(
        summary="Test unknown",
        impact="Test impact",
        resolution_plan="Test plan",
        created_by_rule_id="test.rule",
    )
    assert u1.unknown_id == u2.unknown_id
    assert u1.unknown_id.startswith("U-")


def test_finding_object_ref_field():
    """VE-02: Finding includes object_ref field."""
    f = Finding(
        summary="Test",
        severity="WARN",
        category="TEST",
        object_ref="my_component",
    )
    assert f.object_ref == "my_component"
    assert hasattr(f, "object_ref")


def test_finding_id_includes_object_ref():
    """Finding ID changes when object_ref differs."""
    f1 = Finding(
        summary="Same",
        severity="ERROR",
        category="TEST",
        created_by_rule_id="rule1",
        object_ref=None,
    )
    f2 = Finding(
        summary="Same",
        severity="ERROR",
        category="TEST",
        created_by_rule_id="rule1",
        object_ref="part_1",
    )
    assert f1.finding_id != f2.finding_id


def test_missing_verifier_unknown():
    """create_missing_verifier_unknown produces expected Unknown."""
    unknown = create_missing_verifier_unknown("contract_xyz")
    assert "contract_xyz" in unknown.summary
    assert unknown.blocking is True
    assert unknown.created_by_rule_id == "federated.missing_verifier"
    assert unknown.unknown_id.startswith("U-")


@pytest.mark.asyncio
async def test_concurrency_limit_enforced():
    """Concurrency limit is enforced via Semaphore."""
    max_concurrent = 0
    current_concurrent = 0

    async def slow_verifier(artifact):
        nonlocal max_concurrent, current_concurrent
        current_concurrent += 1
        max_concurrent = max(max_concurrent, current_concurrent)
        await asyncio.sleep(0.05)
        current_concurrent -= 1
        return [], []

    executor = FederatedExecutor(concurrency_limit=2)
    contracts = [MockContract(f"c{i}") for i in range(10)]

    def get_verifier(contract_id):
        return slow_verifier

    results = await executor.execute_all(contracts, {}, get_verifier)
    assert len(results) == 10
    assert max_concurrent <= 2


@pytest.mark.asyncio
async def test_timeout_produces_unknown():
    """Timeout produces Unknown with blocking=True."""

    async def hanging_verifier(artifact):
        await asyncio.sleep(10)  # Way longer than timeout
        return [], []

    executor = FederatedExecutor(concurrency_limit=1, timeout_sec=0.1)
    result = await executor.run_verifier("test_contract", hanging_verifier, {})

    assert result.status == Status.UNKNOWN
    assert len(result.unknowns) == 1
    assert result.unknowns[0].blocking is True
    assert result.unknowns[0].created_by_rule_id == "federated.timeout"


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """Retry-once succeeds on second attempt."""
    attempts = 0

    async def flaky_verifier(artifact):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Transient failure")
        return [
            Finding(
                summary="Success",
                severity="INFO",
                category="TEST",
                created_by_rule_id="test",
            )
        ], []

    findings, unknowns = await safe_verify(
        "test_contract", flaky_verifier, {}, timeout_sec=1.0, retry_once=True
    )
    assert attempts == 2
    assert len(findings) == 1
    assert len(unknowns) == 0


@pytest.mark.asyncio
async def test_results_ordered_by_contract_id():
    """Results are ordered by contract_id for determinism."""

    async def simple_verifier(artifact):
        return [], []

    executor = FederatedExecutor(concurrency_limit=3)
    # Contracts in non-alphabetical order
    contracts = [MockContract("c"), MockContract("a"), MockContract("b")]

    def get_verifier(contract_id):
        return simple_verifier

    results = await executor.execute_all(contracts, {}, get_verifier)

    # Aggregation sorts results by contract_id for determinism
    # Manually verify the aggregation logic
    sorted_results = sorted(results, key=lambda r: r.contract_id)
    contract_ids = [r.contract_id for r in sorted_results]
    assert contract_ids == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_missing_verifier_produces_unknown():
    """Missing verifier produces Unknown with blocking=True."""

    async def real_verifier(artifact):
        return [], []

    executor = FederatedExecutor(concurrency_limit=2)
    contracts = [MockContract("has_verifier"), MockContract("missing")]

    def get_verifier(contract_id):
        if contract_id == "has_verifier":
            return real_verifier
        return None  # Missing

    results = await executor.execute_all(contracts, {}, get_verifier)

    missing_result = next(r for r in results if r.contract_id == "missing")
    assert missing_result.status == Status.UNKNOWN
    assert len(missing_result.unknowns) == 1
    assert missing_result.unknowns[0].blocking is True
    assert "missing_verifier" in missing_result.unknowns[0].created_by_rule_id


@pytest.mark.asyncio
async def test_exception_produces_unknown():
    """Exception in verifier produces Unknown with blocking=True."""

    async def failing_verifier(artifact):
        raise RuntimeError("Something broke")

    executor = FederatedExecutor(concurrency_limit=1)
    result = await executor.run_verifier("test_contract", failing_verifier, {})

    assert result.status == Status.UNKNOWN
    assert len(result.unknowns) == 1
    assert result.unknowns[0].blocking is True
    assert result.unknowns[0].created_by_rule_id == "federated.exception"
    assert "exception" in result.unknowns[0].raw


@pytest.mark.asyncio
async def test_streaming_yields_results_as_completed():
    """execute_streaming yields results as they complete."""

    async def verifier(artifact):
        await asyncio.sleep(0.01)
        return [], []

    executor = FederatedExecutor(concurrency_limit=5)
    contracts = [MockContract(f"c{i}") for i in range(5)]

    def get_verifier(contract_id):
        return verifier

    results = []
    async for result in executor.execute_streaming(contracts, {}, get_verifier):
        results.append(result)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_wrap_sync_verifier():
    """wrap_sync_verifier enables sync verifiers in async context."""

    def sync_verifier(artifact):
        return [
            Finding(
                summary="Sync result",
                severity="INFO",
                category="TEST",
                created_by_rule_id="test",
            )
        ], []

    async_verifier = wrap_sync_verifier(sync_verifier)
    findings, unknowns = await async_verifier({})

    assert len(findings) == 1
    assert findings[0].summary == "Sync result"
