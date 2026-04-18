"""Tests for tool integration."""

import pytest

from src.tools.base import ToolCapability, ToolResult
from src.tools.mock_cad import MockCADTool
from src.tools.registry import ToolRegistry


class TestToolResult:
    """Tests for ToolResult."""

    def test_result_creation(self):
        """Result should be creatable."""
        result = ToolResult(
            success=True,
            data={"output": "test"},
            message="Success",
        )
        assert result.success is True
        assert result.data["output"] == "test"

    def test_failed_result(self):
        """Failed result should capture error."""
        result = ToolResult(
            success=False,
            data={},
            message="Failed",
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"


class TestToolCapability:
    """Tests for ToolCapability."""

    def test_capability_creation(self):
        """Capability should be creatable."""
        cap = ToolCapability(
            name="create_geometry",
            description="Create 3D geometry",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert cap.name == "create_geometry"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return ToolRegistry()

    def test_registry_creation(self, registry):
        """Registry should be creatable."""
        assert registry is not None

    def test_register_tool(self, registry):
        """Registry should register tools."""
        tool = MockCADTool()
        registry.register(tool)

        assert registry.get_tool("MockCAD") is not None

    def test_get_nonexistent_tool(self, registry):
        """Registry should return None for unknown tools."""
        result = registry.get_tool("nonexistent")
        assert result is None

    def test_list_capabilities(self, registry):
        """Registry should list all capabilities."""
        tool = MockCADTool()
        registry.register(tool)

        capabilities = registry.list_capabilities()
        assert len(capabilities) > 0

    def test_list_tools(self, registry):
        """Registry should list all tools."""
        tool = MockCADTool()
        registry.register(tool)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "MockCAD"

    def test_find_tools_for_capability(self, registry):
        """Registry should find tools by capability."""
        tool = MockCADTool()
        registry.register(tool)

        tools = registry.find_tools_by_capability("create_geometry")
        assert len(tools) >= 1


class TestMockCADTool:
    """Tests for MockCADTool."""

    @pytest.fixture
    def tool(self):
        """Create mock CAD tool."""
        return MockCADTool()

    def test_tool_creation(self, tool):
        """Tool should be creatable."""
        assert tool is not None
        assert tool.name == "MockCAD"

    def test_tool_has_capabilities(self, tool):
        """Tool should have capabilities defined."""
        caps = tool.capabilities
        assert len(caps) > 0

    def test_tool_is_deterministic(self, tool):
        """Tool should report determinism."""
        assert tool.is_deterministic is True

    def test_tool_has_cost_estimate(self, tool):
        """Tool should have cost estimate."""
        assert 0.0 <= tool.cost_estimate <= 1.0

    def test_validate_valid_inputs(self, tool):
        """Tool should validate correct inputs."""
        inputs = {
            "geometry_type": "box",
            "dimensions": {"width": 10, "height": 5, "depth": 3},
        }
        assert tool.validate_inputs(inputs) is True

    def test_validate_invalid_inputs(self, tool):
        """Tool should reject invalid inputs."""
        inputs = {"invalid": "data"}
        assert tool.validate_inputs(inputs) is False

    def test_execute_creates_geometry(self, tool):
        """Tool should execute and return result."""
        inputs = {
            "geometry_type": "box",
            "dimensions": {"width": 10, "height": 5, "depth": 3},
        }
        result = tool.execute(inputs)

        assert result.success is True
        assert "geometry_id" in result.data

    def test_execute_with_invalid_inputs(self, tool):
        """Tool should fail gracefully with invalid inputs."""
        inputs = {"invalid": "data"}
        result = tool.execute(inputs)

        assert result.success is False
        assert result.error is not None

    def test_tool_input_schema(self, tool):
        """Tool should have input schema."""
        schema = tool.input_schema
        assert "type" in schema
        assert schema["type"] == "object"

    def test_tool_output_schema(self, tool):
        """Tool should have output schema."""
        schema = tool.output_schema
        assert "type" in schema
