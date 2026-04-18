"""Tests for NLopt optimizer tool adapter.

TDD: Write tests first, then implement.
"""

# Import to verify optimization module is available (uses scipy fallback)


class TestNLoptOptimizerToolBasics:
    """Basic tool interface tests."""

    def test_tool_instantiation(self):
        """Tool can be instantiated."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        assert tool is not None

    def test_tool_name(self):
        """Tool has correct name."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        assert tool.name == "nlopt_optimizer"

    def test_tool_capabilities(self):
        """Tool declares required capabilities."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        cap_names = [c.name for c in tool.capabilities]

        assert "dfm_optimization" in cap_names
        assert "clearance_optimization" in cap_names
        assert "parameter_optimization" in cap_names

    def test_tool_is_deterministic(self):
        """Tool should be deterministic (same input -> same output)."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        assert tool.is_deterministic is True

    def test_tool_cost_estimate(self):
        """Tool provides cost estimate."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        assert tool.cost_estimate >= 0


class TestNLoptOptimizerToolSchemas:
    """Test input/output schemas."""

    def test_input_schema_exists(self):
        """Tool has input schema."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        schema = tool.input_schema
        assert schema is not None
        assert "properties" in schema

    def test_output_schema_exists(self):
        """Tool has output schema."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        schema = tool.output_schema
        assert schema is not None

    def test_input_schema_requires_operation(self):
        """Input schema requires operation field."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        schema = tool.input_schema
        assert "operation" in schema.get("required", [])


class TestNLoptOptimizerToolExecution:
    """Test tool execution."""

    def test_execute_dfm_hole_optimization(self):
        """Execute hole DFM optimization."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "dfm_optimization",
                "feature_type": "hole",
                "current_params": {"diameter": 5.0, "depth": 60.0},
                "constraints": {"max_ld_ratio": 10.0, "min_diameter": 1.0},
            }
        )

        assert result.success
        assert result.data["optimized_params"]["diameter"] >= 5.99  # Tolerance
        assert result.data["constraints_satisfied"]

    def test_execute_dfm_wall_optimization(self):
        """Execute wall thickness optimization."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "dfm_optimization",
                "feature_type": "wall",
                "current_params": {"thickness": 0.8},
                "constraints": {"min_thickness": 1.0},
            }
        )

        assert result.success is True
        assert result.data["optimized_params"]["thickness"] >= 1.0

    def test_execute_dfm_fillet_optimization(self):
        """Execute fillet radius optimization."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "dfm_optimization",
                "feature_type": "fillet",
                "current_params": {"radius": 0.1},
                "constraints": {"min_radius": 0.2, "max_radius": 5.0},
            }
        )

        assert result.success is True
        assert result.data["optimized_params"]["radius"] >= 0.2

    def test_execute_clearance_optimization(self):
        """Execute clearance optimization."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "clearance_optimization",
                "part_a_bbox": {"min": [0, 0, 0], "max": [10, 10, 10]},
                "part_b_bbox": {"min": [8, 0, 0], "max": [18, 10, 10]},
                "min_clearance": 2.0,
                "max_translation": 20.0,
            }
        )

        assert result.success
        assert "translation" in result.data
        assert result.data["achieved_clearance"] >= 1.99  # Tolerance

    def test_execute_parameter_optimization(self):
        """Execute generic parameter optimization."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "parameter_optimization",
                "parameters": ["x", "y"],
                "bounds": {"x": [0.0, 10.0], "y": [0.0, 10.0]},
                "objective": "minimize_sum",  # x + y
                "constraints": [
                    {"type": "inequality", "expr": "x + y >= 5"}  # sum >= 5
                ],
            }
        )

        assert result.success is True
        assert result.data["optimal_x"] + result.data["optimal_y"] >= 4.99

    def test_execute_invalid_operation(self):
        """Invalid operation returns error."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute({"operation": "invalid_op"})

        assert result.success is False
        assert "error" in result.data or result.error is not None


class TestNLoptOptimizerToolValidation:
    """Test input validation."""

    def test_validate_dfm_inputs_valid(self):
        """Valid DFM inputs pass validation."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        valid = tool.validate_inputs(
            {
                "operation": "dfm_optimization",
                "feature_type": "hole",
                "current_params": {"diameter": 5.0, "depth": 60.0},
            }
        )
        assert valid is True

    def test_validate_dfm_inputs_missing_feature_type(self):
        """Missing feature_type fails validation."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        valid = tool.validate_inputs(
            {
                "operation": "dfm_optimization",
                "current_params": {"diameter": 5.0},
            }
        )
        assert valid is False

    def test_validate_clearance_inputs_valid(self):
        """Valid clearance inputs pass validation."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        valid = tool.validate_inputs(
            {
                "operation": "clearance_optimization",
                "part_a_bbox": {"min": [0, 0, 0], "max": [10, 10, 10]},
                "part_b_bbox": {"min": [8, 0, 0], "max": [18, 10, 10]},
            }
        )
        assert valid is True

    def test_validate_clearance_inputs_missing_bbox(self):
        """Missing bbox fails validation."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        valid = tool.validate_inputs(
            {
                "operation": "clearance_optimization",
                "part_a_bbox": {"min": [0, 0, 0], "max": [10, 10, 10]},
                # missing part_b_bbox
            }
        )
        assert valid is False


class TestNLoptOptimizerToolRegistry:
    """Test tool registry integration."""

    def test_register_tool(self):
        """Tool can be registered."""
        from src.tools import ToolRegistry
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        registry = ToolRegistry()
        tool = NLoptOptimizerTool()
        registry.register(tool)

        retrieved = registry.get_tool("nlopt_optimizer")
        assert retrieved is not None
        assert retrieved.name == "nlopt_optimizer"

    def test_find_by_capability(self):
        """Tool found by capability search."""
        from src.tools import ToolRegistry
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        registry = ToolRegistry()
        registry.register(NLoptOptimizerTool())

        # find_tools_by_capability takes a string, not ToolCapability
        tools = registry.find_tools_by_capability("dfm_optimization")
        assert len(tools) >= 1
        assert any(t.name == "nlopt_optimizer" for t in tools)
