"""Pytest fixtures for CadQuery tool tests.

Provides both mock and real gateway fixtures:
- mock_gateway: Fast, no external deps (default for unit tests)
- real_gateway: Uses SubprocessCadQueryBackend (for integration tests)

Usage:
    # Unit test (fast)
    def test_something(mock_gateway):
        tool = CadQueryExecTool(backend="gateway", gateway=mock_gateway)

    # Integration test (slow, needs venv)
    @pytest.mark.integration
    def test_real_execution(real_gateway):
        tool = CadQueryExecTool(backend="gateway", gateway=real_gateway)
"""

from unittest.mock import Mock

import pytest

from src.tools.gateway.protocol import ExecutionResult


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )


@pytest.fixture
def mock_gateway():
    """Mock ToolGateway for fast unit tests.

    Returns a mock gateway that returns successful results.
    Configure with mock_gateway.execute.return_value = ... for specific tests.
    """
    from src.tools.gateway import ToolGateway

    gateway = Mock(spec=ToolGateway)
    gateway.execute.return_value = ExecutionResult(
        success=True,
        geometry_props={
            "volume": 1000.0,
            "face_count": 6,
            "edge_count": 12,
            "vertex_count": 8,
            "bounding_box": {"xlen": 10.0, "ylen": 10.0, "zlen": 10.0},
        },
        step_path=None,
        execution_time_ms=50.0,
    )
    return gateway


@pytest.fixture(scope="session")
def real_gateway():
    """Real ToolGateway with SubprocessCadQueryBackend.

    Session-scoped to avoid recreating venv for each test.
    Use for integration tests only.

    Skips if backend is not available (venv creation failed).
    """
    from src.tools.gateway import ToolGateway
    from src.tools.gateway.backends import SubprocessCadQueryBackend

    gateway = ToolGateway()
    backend = SubprocessCadQueryBackend()

    # Check if backend is available (may create venv lazily)
    if not backend.is_available():
        pytest.skip("SubprocessCadQueryBackend not available (CadQuery venv missing)")

    gateway.register("cadquery", backend)
    return gateway


@pytest.fixture
def real_cadquery_tool(real_gateway):
    """CadQueryExecTool configured with real gateway backend."""
    from src.tools.cadquery_tool import CadQueryExecTool

    return CadQueryExecTool(backend="gateway", gateway=real_gateway)


@pytest.fixture
def mock_cadquery_tool(mock_gateway):
    """CadQueryExecTool configured with mock gateway backend."""
    from src.tools.cadquery_tool import CadQueryExecTool

    return CadQueryExecTool(backend="gateway", gateway=mock_gateway)
