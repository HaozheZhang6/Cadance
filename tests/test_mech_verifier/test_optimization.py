"""Tests for nlopt-based optimization in mech_verifier.

TDD: Write tests first, then implement.
"""

import numpy as np

# Import optimization module (uses scipy fallback if nlopt not installed)


class TestConstraintDefinition:
    """Test constraint definition and serialization."""

    def test_create_bound_constraint(self):
        """Bound constraint: min <= x <= max."""
        from mech_verify.optimization.constraints import BoundConstraint

        c = BoundConstraint(name="wall_thickness", min_val=1.0, max_val=10.0)
        assert c.name == "wall_thickness"
        assert c.min_val == 1.0
        assert c.max_val == 10.0
        assert c.is_satisfied(5.0) is True
        assert c.is_satisfied(0.5) is False
        assert c.is_satisfied(15.0) is False

    def test_create_inequality_constraint(self):
        """Inequality constraint: g(x) <= 0."""
        from mech_verify.optimization.constraints import InequalityConstraint

        # L/D ratio constraint: L/D - 10 <= 0
        def ld_ratio_func(params):
            length, diameter = params["length"], params["diameter"]
            return length / diameter - 10.0

        c = InequalityConstraint(name="ld_ratio", func=ld_ratio_func)
        assert c.is_satisfied({"length": 50.0, "diameter": 10.0}) is True  # 5 <= 10
        assert c.is_satisfied({"length": 150.0, "diameter": 10.0}) is False  # 15 > 10

    def test_create_equality_constraint(self):
        """Equality constraint: h(x) = 0."""
        from mech_verify.optimization.constraints import EqualityConstraint

        # Volume constraint: V - target = 0
        def volume_func(params):
            return params["volume"] - 1000.0

        c = EqualityConstraint(name="target_volume", func=volume_func, tolerance=1e-3)
        assert c.is_satisfied({"volume": 1000.0}) is True
        assert c.is_satisfied({"volume": 999.999}) is True
        assert c.is_satisfied({"volume": 900.0}) is False


class TestOptimizationProblem:
    """Test optimization problem setup."""

    def test_create_problem_with_bounds(self):
        """Create problem with parameter bounds."""
        from mech_verify.optimization.constraints import BoundConstraint
        from mech_verify.optimization.problem import OptimizationProblem

        prob = OptimizationProblem(
            name="hole_optimization",
            parameters=["diameter", "depth"],
            bounds=[
                BoundConstraint("diameter", min_val=1.0, max_val=50.0),
                BoundConstraint("depth", min_val=5.0, max_val=100.0),
            ],
        )
        assert prob.n_params == 2
        assert prob.lower_bounds == [1.0, 5.0]
        assert prob.upper_bounds == [50.0, 100.0]

    def test_create_problem_with_objective(self):
        """Create problem with objective function."""
        from mech_verify.optimization.constraints import BoundConstraint
        from mech_verify.optimization.problem import OptimizationProblem

        # Minimize material (proxy: minimize hole volume)
        def hole_volume(params):
            d, h = params
            return np.pi * (d / 2) ** 2 * h

        prob = OptimizationProblem(
            name="minimize_hole",
            parameters=["diameter", "depth"],
            bounds=[
                BoundConstraint("diameter", min_val=1.0, max_val=50.0),
                BoundConstraint("depth", min_val=5.0, max_val=100.0),
            ],
            objective=hole_volume,
            minimize=True,
        )
        assert prob.objective is not None
        assert prob.minimize is True

    def test_problem_with_inequality_constraints(self):
        """Problem with inequality constraints."""
        from mech_verify.optimization.constraints import (
            BoundConstraint,
            InequalityConstraint,
        )
        from mech_verify.optimization.problem import OptimizationProblem

        # L/D ratio <= 10
        def ld_constraint(params):
            d, h = params
            return h / d - 10.0  # h/d - 10 <= 0

        prob = OptimizationProblem(
            name="constrained_hole",
            parameters=["diameter", "depth"],
            bounds=[
                BoundConstraint("diameter", min_val=1.0, max_val=50.0),
                BoundConstraint("depth", min_val=5.0, max_val=100.0),
            ],
            inequality_constraints=[
                InequalityConstraint("ld_ratio", func=ld_constraint),
            ],
        )
        assert len(prob.inequality_constraints) == 1


class TestNLoptSolver:
    """Test NLopt solver wrapper."""

    def test_solver_available(self):
        """Solver should report availability."""
        from mech_verify.optimization.solver import NLoptSolver

        solver = NLoptSolver()
        assert solver.is_available() is True

    def test_solve_unconstrained_minimization(self):
        """Solve simple unconstrained minimization."""
        from mech_verify.optimization.constraints import BoundConstraint
        from mech_verify.optimization.problem import OptimizationProblem
        from mech_verify.optimization.solver import NLoptSolver

        # Minimize (x-3)^2 + (y-4)^2
        def objective(params):
            x, y = params
            return (x - 3) ** 2 + (y - 4) ** 2

        prob = OptimizationProblem(
            name="simple_min",
            parameters=["x", "y"],
            bounds=[
                BoundConstraint("x", min_val=-10.0, max_val=10.0),
                BoundConstraint("y", min_val=-10.0, max_val=10.0),
            ],
            objective=objective,
            minimize=True,
        )

        solver = NLoptSolver(algorithm="LD_SLSQP")
        result = solver.solve(prob, x0=[0.0, 0.0])

        assert result.success
        assert abs(result.x[0] - 3.0) < 0.01
        assert abs(result.x[1] - 4.0) < 0.01

    def test_solve_with_inequality_constraint(self):
        """Solve with inequality constraint."""
        from mech_verify.optimization.constraints import (
            BoundConstraint,
            InequalityConstraint,
        )
        from mech_verify.optimization.problem import OptimizationProblem
        from mech_verify.optimization.solver import NLoptSolver

        # Minimize x + y subject to x + y >= 5 (i.e., 5 - x - y <= 0)
        def objective(params):
            return params[0] + params[1]

        def constraint(params):
            return 5.0 - params[0] - params[1]  # 5 - x - y <= 0

        prob = OptimizationProblem(
            name="constrained_min",
            parameters=["x", "y"],
            bounds=[
                BoundConstraint("x", min_val=0.0, max_val=10.0),
                BoundConstraint("y", min_val=0.0, max_val=10.0),
            ],
            objective=objective,
            inequality_constraints=[InequalityConstraint("sum_min", func=constraint)],
            minimize=True,
        )

        solver = NLoptSolver(algorithm="LD_SLSQP")
        result = solver.solve(prob, x0=[1.0, 1.0])

        assert result.success is True
        assert abs(result.x[0] + result.x[1] - 5.0) < 0.01

    def test_solver_returns_optimization_result(self):
        """Solver returns structured result."""
        from mech_verify.optimization.constraints import BoundConstraint
        from mech_verify.optimization.problem import OptimizationProblem
        from mech_verify.optimization.solver import NLoptSolver, OptimizationResult

        def objective(params):
            return sum(p**2 for p in params)

        prob = OptimizationProblem(
            name="quadratic",
            parameters=["x"],
            bounds=[BoundConstraint("x", min_val=-10.0, max_val=10.0)],
            objective=objective,
            minimize=True,
        )

        solver = NLoptSolver()
        result = solver.solve(prob, x0=[5.0])

        assert isinstance(result, OptimizationResult)
        assert hasattr(result, "success")
        assert hasattr(result, "x")
        assert hasattr(result, "fun")
        assert hasattr(result, "n_iterations")
        assert hasattr(result, "message")


class TestDFMOptimization:
    """Test DFM-specific optimization scenarios."""

    def test_optimize_hole_for_ld_ratio(self):
        """Optimize hole diameter to satisfy L/D ratio constraint."""
        from mech_verify.optimization.dfm import optimize_hole_parameters

        # Hole with depth=60mm, current diameter=5mm -> L/D=12 (violates max 10)
        result = optimize_hole_parameters(
            current_diameter=5.0,
            current_depth=60.0,
            max_ld_ratio=10.0,
            min_diameter=1.0,
            max_diameter=50.0,
        )

        assert result.success
        # New diameter should be ~6mm to get L/D <= 10 (with tolerance)
        assert result.optimized_diameter >= 5.99
        assert result.new_ld_ratio <= 10.01

    def test_optimize_wall_thickness(self):
        """Optimize feature to meet min wall thickness."""
        from mech_verify.optimization.dfm import optimize_wall_thickness

        # Current wall=0.8mm, need min 1.0mm
        result = optimize_wall_thickness(
            current_thickness=0.8,
            min_thickness=1.0,
            adjustment_range=(-0.5, 2.0),
        )

        assert result.success is True
        assert result.optimized_thickness >= 1.0

    def test_optimize_fillet_radius(self):
        """Optimize fillet radius within constraints."""
        from mech_verify.optimization.dfm import optimize_fillet_radius

        # Current fillet=0.1mm, need min 0.2mm, max 5.0mm
        result = optimize_fillet_radius(
            current_radius=0.1,
            min_radius=0.2,
            max_radius=5.0,
            target_stress_reduction=0.3,  # 30% stress reduction target
        )

        assert result.success is True
        assert result.optimized_radius >= 0.2
        assert result.optimized_radius <= 5.0


class TestClearanceOptimization:
    """Test assembly clearance optimization."""

    def test_optimize_clearance_translation(self):
        """Find translation to achieve minimum clearance."""
        from mech_verify.optimization.assembly import optimize_clearance

        # Two boxes: A at origin, B nearby
        # Find translation for B to achieve min clearance
        result = optimize_clearance(
            part_a_bbox={"min": [0, 0, 0], "max": [10, 10, 10]},
            part_b_bbox={"min": [9, 0, 0], "max": [19, 10, 10]},  # 1mm overlap in X
            min_clearance=2.0,
            max_translation=10.0,
        )

        assert result.success
        # B should be translated ~3mm in +X (1mm overlap + 2mm clearance)
        # Use tolerance for floating point
        assert result.translation[0] >= 2.99 or result.achieved_clearance >= 1.99

    def test_optimize_interference_elimination(self):
        """Find transform to eliminate interference."""
        from mech_verify.optimization.assembly import eliminate_interference

        # Two overlapping parts
        result = eliminate_interference(
            part_a_bbox={"min": [0, 0, 0], "max": [10, 10, 10]},
            part_b_bbox={"min": [5, 5, 5], "max": [15, 15, 15]},  # 5mm interference
            allow_rotation=False,
            max_translation=20.0,
        )

        assert result.success is True
        assert result.interference_volume < 1e-6  # Effectively zero


class TestOptimizationTool:
    """Test tool adapter for LLM consumption."""

    def test_tool_registration(self):
        """Tool should be registerable."""
        from src.tools import ToolRegistry
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        registry = ToolRegistry()
        tool = NLoptOptimizerTool()
        registry.register(tool)

        assert registry.get_tool("nlopt_optimizer") is not None

    def test_tool_capabilities(self):
        """Tool should declare optimization capabilities."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        caps = [c.name for c in tool.capabilities]

        assert "dfm_optimization" in caps
        assert "clearance_optimization" in caps
        assert "parameter_optimization" in caps

    def test_tool_execute_dfm_optimization(self):
        """Execute DFM optimization via tool."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "dfm_optimization",
                "feature_type": "hole",
                "current_params": {"diameter": 5.0, "depth": 60.0},
                "constraints": {"max_ld_ratio": 10.0},
            }
        )

        assert result.success
        assert "optimized_params" in result.data
        assert result.data["optimized_params"]["diameter"] >= 5.99  # Tolerance

    def test_tool_execute_clearance_optimization(self):
        """Execute clearance optimization via tool."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        result = tool.execute(
            {
                "operation": "clearance_optimization",
                "part_a_bbox": {"min": [0, 0, 0], "max": [10, 10, 10]},
                "part_b_bbox": {"min": [9, 0, 0], "max": [19, 10, 10]},
                "min_clearance": 2.0,
            }
        )

        assert result.success is True
        assert "translation" in result.data

    def test_tool_input_validation(self):
        """Tool should validate inputs."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()

        # Missing required field
        assert tool.validate_inputs({"operation": "dfm_optimization"}) is False

        # Valid input
        assert (
            tool.validate_inputs(
                {
                    "operation": "dfm_optimization",
                    "feature_type": "hole",
                    "current_params": {"diameter": 5.0, "depth": 60.0},
                }
            )
            is True
        )

    def test_tool_graceful_unavailable(self):
        """Tool handles nlopt unavailability gracefully."""
        from src.tools.nlopt_optimizer import NLoptOptimizerTool

        tool = NLoptOptimizerTool()
        # Even if nlopt import fails, tool should exist and report unavailability
        assert hasattr(tool, "is_available")


class TestIntegrationWithMDS:
    """Test integration with MDS and verification pipeline."""

    def test_suggest_fixes_from_findings(self):
        """Generate optimization suggestions from DFM findings."""
        from mech_verify.optimization.integration import suggest_fixes_from_findings
        from verifier_core.models import Finding, Severity

        findings = [
            Finding(
                rule_id="DFM-HOLE-LD",
                severity=Severity.WARN,
                message="Hole L/D ratio 12.0 exceeds max 10.0",
                object_ref="mech://feature/hole_001",
                measured_value=12.0,
                limit=10.0,
            ),
            Finding(
                rule_id="DFM-WALL-MIN",
                severity=Severity.ERROR,
                message="Wall thickness 0.8mm below min 1.0mm",
                object_ref="mech://feature/wall_001",
                measured_value=0.8,
                limit=1.0,
            ),
        ]

        suggestions = suggest_fixes_from_findings(findings)

        assert len(suggestions) == 2
        assert suggestions[0].finding_id == "DFM-HOLE-LD"
        assert suggestions[0].optimization_type == "hole_parameter"
        assert suggestions[1].finding_id == "DFM-WALL-MIN"
        assert suggestions[1].optimization_type == "wall_thickness"
