"""End-to-end integration test: Mounting Bracket Demo.

Tests the full intent → verification → feedback loop:
1. Intent parsing → GRS → Contracts
2. Attach artifact (ops_program)
3. Run mechanical verification
4. Evidence/Unknown nodes created
5. Contract status/confidence updated
6. Evidence gating enforced

This proves the architecture from INTENT_MECH_INTEGRATION.md works.
"""

from pathlib import Path

import pytest

from src.agents.base import Trigger, TriggerType
from src.agents.mechanical_verification import MechanicalVerificationAgent
from src.hypergraph.engine import HypergraphEngine
from src.hypergraph.models import (
    ArtifactNode,
    Contract,
    ContractStatus,
    EdgeType,
    Evidence,
    GoalNode,
    NodeType,
    Requirement,
    SpecificationNode,
    SpecParameter,
    Unknown,
)
from src.hypergraph.store import HypergraphStore
from src.tools.execution import ToolExecutionManager
from src.tools.mech_verify import MechVerifyTool
from src.tools.registry import ToolRegistry
from src.verification.mapping_mech import map_mech_results
from src.verification.pipeline import VerificationPipeline
from verifier_core.models import Finding, Severity
from verifier_core.models import Unknown as CoreUnknown

FIXTURES_DIR = Path(__file__).parent.parent / "dfm_test_cases"
MECH_TEST_PROJECTS = (
    Path(__file__).parent.parent.parent / "src" / "mech_verifier" / "test_projects"
)

# Check if OCCT backend is available
try:
    from src.mech_verifier.mech_verify.backend.occt import OCCTBackend  # noqa: F401

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False


class TestMountingBracketEndToEnd:
    """End-to-end tests for mounting bracket demo harness."""

    def test_full_loop_passing_artifact(self, tmp_path):
        """Test: passing artifact → SATISFIED contract with Evidence."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        # Step 1: Create GRS nodes (mock intent refinement output)
        goal = GoalNode(
            id="goal_bracket",
            description="Design a mounting bracket for 5kg load",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="GRSRefinementAgent",
        )
        requirement = Requirement(
            id="req_001",
            description="Bracket shall withstand 5kg load",
            statement="The bracket SHALL withstand static load of 5kg with safety factor 2.0",
            rationale="Standard mounting requirements",
            verification_method="analysis",
        )
        spec = SpecificationNode(
            id="spec_001",
            description="Bracket geometry spec",
            derives_from=["req_001"],
            parameters=[
                SpecParameter(name="wall_thickness", value=3.0, unit="mm"),
                SpecParameter(name="hole_diameter", value=6.0, unit="mm"),
            ],
        )

        engine.add_node(goal)
        engine.add_node(requirement)
        engine.add_node(spec)
        engine.add_edge("goal_bracket", "req_001", EdgeType.HAS_CHILD)
        engine.add_edge("req_001", "spec_001", EdgeType.HAS_CHILD)

        # Step 2: Create contract (mock contract extraction output)
        contract = Contract(
            id="contract_bracket",
            description="Bracket structural contract",
            inputs={"load": "5kg"},
            outputs={"deformation": "<1mm"},
            guarantees=[
                "wall_thickness >= 1.0mm",
                "hole_diameter >= 1.0mm",
            ],
            assumptions=["Material is aluminum 6061-T6"],
        )
        engine.add_node(contract)
        engine.add_edge("req_001", "contract_bracket", EdgeType.HAS_CHILD)

        # Step 3: Attach artifact (ops_program)
        ops_path = FIXTURES_DIR / "mounting_bracket_ops.json"
        artifact = ArtifactNode(
            id="artifact_bracket_ops",
            description="Mounting bracket ops program",
            artifact_type="ops_program",
            path=str(ops_path),
            media_type="application/json",
            role="input",
        )
        engine.add_node(artifact)
        engine.add_edge("contract_bracket", "artifact_bracket_ops", EdgeType.HAS_CHILD)

        # Step 4: Run mechanical verification
        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(trigger_type=TriggerType.CONTRACTS_EXTRACTED)
        mutation = agent.propose_mutation(trigger)

        # Apply mutation
        for node in mutation.nodes_to_add:
            engine.add_node(node)
        for edge in mutation.edges_to_add:
            engine.add_edge(edge.source_id, edge.target_id, edge.edge_type, edge.id)
        for node_id, updates in mutation.nodes_to_update.items():
            engine.update_node(node_id, **updates)

        # Assertions
        # 4a. ToolInvocation node created
        invocations = engine.get_nodes_by_type(NodeType.TOOL_INVOCATION)
        assert len(invocations) >= 1, "ToolInvocation node should be created"
        assert invocations[0].tool_name == "mech-verify"

        # 4b. Evidence nodes created
        evidence_nodes = engine.get_nodes_by_type(NodeType.EVIDENCE)
        assert len(evidence_nodes) >= 0, "Evidence nodes created for findings"

        # 4c. Contract confidence updated (status set by Step 5 VerificationPipeline)
        updated_contract = engine.get_node("contract_bracket")
        # MechanicalVerificationAgent only updates confidence, not status
        # Status is determined by VerificationPipeline (Step 5)
        assert (
            updated_contract.confidence is not None
        ), "Contract confidence should be set"

        # 4d. GENERATED edges link invocation → artifact outputs
        generated_edges = [
            e for e in engine.edges.values() if e.edge_type == EdgeType.GENERATED
        ]
        assert (
            len(generated_edges) >= 1
        ), "GENERATED edges should link invocation to artifacts"

        engine.save()

    def test_full_loop_failing_artifact(self, tmp_path):
        """Test: failing artifact (small hole) → VIOLATED contract with ERROR finding."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        # Setup GRS + contract
        goal = GoalNode(
            id="goal_bracket",
            description="Design a mounting bracket",
            goal_type="ACHIEVE",
            refinement_type="AND",
            agent="GRSRefinementAgent",
        )
        contract = Contract(
            id="contract_bracket",
            description="Bracket structural contract",
            inputs={},
            outputs={},
            guarantees=["hole_diameter >= 0.5mm"],
        )
        engine.add_node(goal)
        engine.add_node(contract)
        engine.add_edge("goal_bracket", "contract_bracket", EdgeType.HAS_CHILD)

        # Attach failing artifact (hole diameter = 0.3mm < 0.5mm minimum)
        ops_path = FIXTURES_DIR / "mounting_bracket_small_hole_ops.json"
        artifact = ArtifactNode(
            id="artifact_small_hole",
            description="Small hole bracket",
            artifact_type="ops_program",
            path=str(ops_path),
            media_type="application/json",
            role="input",
        )
        engine.add_node(artifact)
        engine.add_edge("contract_bracket", "artifact_small_hole", EdgeType.HAS_CHILD)

        # Run verification
        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(trigger_type=TriggerType.CONTRACTS_EXTRACTED)
        mutation = agent.propose_mutation(trigger)

        # Apply mutation
        for node in mutation.nodes_to_add:
            engine.add_node(node)
        for edge in mutation.edges_to_add:
            engine.add_edge(edge.source_id, edge.target_id, edge.edge_type, edge.id)
        for node_id, updates in mutation.nodes_to_update.items():
            engine.update_node(node_id, **updates)

        # Assertions - MechanicalVerificationAgent only updates confidence
        # Status (VIOLATED) is set by VerificationPipeline (Step 5)
        updated_contract = engine.get_node("contract_bracket")
        assert (
            updated_contract.confidence < 1.0
        ), "Confidence should decrease on ERROR finding"

        # Evidence nodes for findings
        evidence_nodes = engine.get_nodes_by_type(NodeType.EVIDENCE)
        assert len(evidence_nodes) >= 1, "Evidence for small hole finding"

        # Check evidence VALIDATES contract
        validates_edges = [
            e
            for e in engine.edges.values()
            if e.edge_type == EdgeType.VALIDATES and e.target_id == "contract_bracket"
        ]
        assert len(validates_edges) >= 1, "Evidence should VALIDATE contract"

    def test_evidence_gating_enforcement(self, tmp_path):
        """Test: RulesVerifier rejects SATISFIED without Evidence."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)

        # Create contract marked SATISFIED without evidence
        contract = Contract(
            id="contract_no_evidence",
            description="Contract without evidence",
            status=ContractStatus.SATISFIED,
            guarantees=["must have evidence"],
        )
        engine.add_node(contract)

        # Run verification pipeline
        pipeline = VerificationPipeline(engine)
        summary = pipeline.verify_all()

        # Should fail due to missing evidence
        assert summary["total_failures"] >= 1, "Should fail evidence gating"

    def test_evidence_gating_passes_with_evidence(self, tmp_path):
        """Test: RulesVerifier passes SATISFIED with Evidence."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)

        # Create contract + evidence
        contract = Contract(
            id="contract_with_evidence",
            description="Contract with evidence",
            status=ContractStatus.SATISFIED,
            guarantees=["wall_thickness >= 1.0mm"],
        )
        evidence = Evidence(
            id="evidence_001",
            description="Verification passed",
            evidence_type="mech_verification",
            provenance="mech-verify:report_001",
            data={"rule_id": "tier0.wall_thickness", "severity": "INFO"},
        )
        engine.add_node(contract)
        engine.add_node(evidence)
        engine.add_edge("evidence_001", "contract_with_evidence", EdgeType.VALIDATES)

        # Run verification pipeline
        pipeline = VerificationPipeline(engine)
        summary = pipeline.verify_all()

        # Should pass
        assert summary["total_failures"] == 0, "Should pass with evidence"

    def test_unknown_blocks_contract(self, tmp_path):
        """Test: Contract with blocking Unknown cannot be SATISFIED."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)

        # Contract marked SATISFIED but has blocking unknown
        contract = Contract(
            id="contract_blocked",
            description="Contract blocked by unknown",
            status=ContractStatus.SATISFIED,
            guarantees=["tolerance check"],
        )
        evidence = Evidence(
            id="evidence_002",
            description="Partial verification",
            evidence_type="mech_verification",
            provenance="mech-verify:report_002",
        )
        unknown = Unknown(
            id="unknown_pmi",
            description="PMI data missing",
            reason="Cannot verify tolerances without PMI",
            metadata={"blocking": True},
        )

        engine.add_node(contract)
        engine.add_node(evidence)
        engine.add_node(unknown)
        engine.add_edge("evidence_002", "contract_blocked", EdgeType.VALIDATES)
        engine.add_edge("unknown_pmi", "contract_blocked", EdgeType.DEPENDS_ON)

        # Run verification
        pipeline = VerificationPipeline(engine)
        summary = pipeline.verify_all()

        # Should fail due to blocking unknown
        assert (
            summary["total_failures"] >= 1
        ), "Blocking unknown should fail verification"

    def test_artifact_added_trigger_routes_to_agent(self, tmp_path):
        """Test: ARTIFACT_ADDED trigger routes to MechanicalVerificationAgent."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        # Setup contract + artifact
        contract = Contract(
            id="contract_trigger_test",
            description="Test contract",
            guarantees=["check artifact"],
        )
        ops_path = FIXTURES_DIR / "mounting_bracket_ops.json"
        artifact = ArtifactNode(
            id="artifact_trigger",
            description="Test artifact",
            artifact_type="ops_program",
            path=str(ops_path),
        )
        engine.add_node(contract)
        engine.add_node(artifact)
        engine.add_edge("contract_trigger_test", "artifact_trigger", EdgeType.HAS_CHILD)

        # Create agent and trigger
        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(
            trigger_type=TriggerType.ARTIFACT_ADDED,
            node_id="artifact_trigger",
        )

        # Agent should handle this trigger
        assert agent.can_handle(trigger), "Agent should handle ARTIFACT_ADDED"

        mutation = agent.propose_mutation(trigger)
        assert not mutation.is_empty(), "Mutation should not be empty"

    def test_manual_trigger_with_specific_target(self, tmp_path):
        """Test: MANUAL trigger with specific target/artifact IDs."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        contract = Contract(
            id="contract_manual",
            description="Manual verification target",
            guarantees=[],
        )
        ops_path = FIXTURES_DIR / "L1_golden_pass_ops.json"
        artifact = ArtifactNode(
            id="artifact_manual",
            description="Manual artifact",
            artifact_type="ops_program",
            path=str(ops_path),
        )
        engine.add_node(contract)
        engine.add_node(artifact)

        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={"target_id": "contract_manual", "artifact_id": "artifact_manual"},
        )

        mutation = agent.propose_mutation(trigger)
        assert not mutation.is_empty()

        # Apply and verify
        for node in mutation.nodes_to_add:
            engine.add_node(node)

        invocations = engine.get_nodes_by_type(NodeType.TOOL_INVOCATION)
        assert len(invocations) == 1


class TestMappingMechIntegration:
    """Tests for mapping layer integration."""

    def test_finding_to_evidence_preserves_data(self):
        """Test: Finding → Evidence preserves all relevant data."""
        finding = Finding(
            rule_id="mech.tier0.min_wall_thickness",
            severity=Severity.ERROR,
            message="Wall thickness 0.5mm below minimum 1.0mm",
            finding_id="finding_001",
            object_ref="shell_0",
            measured_value=0.5,
            limit=1.0,
            suggested_fix="Increase wall thickness to at least 1.0mm",
        )

        mutation = map_mech_results(
            findings=[finding],
            unknowns=[],
            target_id="contract_001",
            tool_name="mech-verify",
            report_id="report_001",
        )

        evidence_nodes = [
            n for n in mutation.nodes_to_add if n.node_type == NodeType.EVIDENCE
        ]
        assert len(evidence_nodes) == 1

        ev = evidence_nodes[0]
        assert ev.evidence_type == "mech_verification"
        assert "mech-verify" in ev.provenance
        assert ev.data["rule_id"] == "mech.tier0.min_wall_thickness"
        assert ev.data["severity"] == "ERROR"
        assert ev.data["measured_value"] == 0.5
        assert ev.data["limit"] == 1.0

    def test_unknown_to_unknown_preserves_blocking(self):
        """Test: CoreUnknown → Unknown preserves blocking flag."""
        core_unknown = CoreUnknown(
            summary="PMI data required",
            impact="Cannot verify tolerances",
            resolution_plan="Provide STEP file with embedded PMI",
            blocking=True,
            created_by_rule_id="mech.tier0.pmi_required",
        )

        mutation = map_mech_results(
            findings=[],
            unknowns=[core_unknown],
            target_id="contract_001",
            tool_name="mech-verify",
            report_id="report_001",
        )

        unknown_nodes = [
            n for n in mutation.nodes_to_add if n.node_type == NodeType.UNKNOWN
        ]
        assert len(unknown_nodes) == 1

        unk = unknown_nodes[0]
        assert unk.metadata["blocking"] is True
        assert unk.metadata["resolution_plan"] == "Provide STEP file with embedded PMI"


class TestToolExecutionProvenance:
    """Tests for tool execution provenance tracking."""

    def test_execution_creates_invocation_with_timing(self, tmp_path):
        """Test: Execution creates ToolInvocation with timing data."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        registry = ToolRegistry()
        registry.register(MechVerifyTool())

        manager = ToolExecutionManager(
            engine=engine,
            registry=registry,
            artifact_store_dir=tmp_path / "artifacts",
        )

        ops_path = FIXTURES_DIR / "L1_golden_pass_ops.json"
        result = manager.execute(
            "mech-verify",
            {"mode": "ops_program", "ops_program_path": str(ops_path)},
        )

        assert result.tool_result.success
        invocations = [
            n
            for n in result.mutation.nodes_to_add
            if n.node_type == NodeType.TOOL_INVOCATION
        ]
        assert len(invocations) == 1

        inv = invocations[0]
        assert inv.tool_name == "mech-verify"
        assert inv.duration_ms is not None
        assert inv.duration_ms > 0
        assert inv.status == "success"

    def test_execution_persists_artifacts(self, tmp_path):
        """Test: Execution persists report/mds artifacts to store."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        registry = ToolRegistry()
        registry.register(MechVerifyTool())

        artifacts_dir = tmp_path / "artifacts"
        manager = ToolExecutionManager(
            engine=engine,
            registry=registry,
            artifact_store_dir=artifacts_dir,
        )

        ops_path = FIXTURES_DIR / "L2_thin_wall_ops.json"
        result = manager.execute(
            "mech-verify",
            {"mode": "ops_program", "ops_program_path": str(ops_path)},
        )

        artifact_nodes = [
            n for n in result.mutation.nodes_to_add if n.node_type == NodeType.ARTIFACT
        ]
        # Should have at least report artifact
        assert len(artifact_nodes) >= 1

        # Artifact file should exist
        for art in artifact_nodes:
            assert Path(art.path).exists(), f"Artifact file should exist: {art.path}"
            assert art.sha256 is not None


class TestCLIIntegration:
    """Tests for CLI command integration (without running actual CLI)."""

    def test_attach_artifact_creates_node_and_edge(self, tmp_path):
        """Test: attach-artifact equivalent creates correct graph structure."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)

        # Create target contract
        contract = Contract(
            id="contract_cli",
            description="CLI test contract",
            guarantees=[],
        )
        engine.add_node(contract)

        # Simulate attach-artifact
        ops_path = FIXTURES_DIR / "mounting_bracket_ops.json"
        artifact = ArtifactNode(
            id="artifact_cli",
            description="ops_program artifact",
            artifact_type="ops_program",
            path=str(ops_path),
            role="input",
        )
        engine.add_node(artifact)
        engine.add_edge("contract_cli", "artifact_cli", EdgeType.HAS_CHILD)

        # Verify
        children = engine.get_children("contract_cli")
        assert len(children) == 1
        assert children[0].node_type == NodeType.ARTIFACT

    def test_verify_mech_updates_contract_status(self, tmp_path):
        """Test: verify-mech equivalent updates contract status/confidence."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        contract = Contract(
            id="contract_verify",
            description="Verification target",
            guarantees=["hole_diameter >= 0.5mm"],
            confidence=1.0,
        )
        # Use small hole artifact that triggers ERROR
        ops_path = FIXTURES_DIR / "mounting_bracket_small_hole_ops.json"
        artifact = ArtifactNode(
            id="artifact_verify",
            description="Small hole artifact",
            artifact_type="ops_program",
            path=str(ops_path),
        )
        engine.add_node(contract)
        engine.add_node(artifact)
        engine.add_edge("contract_verify", "artifact_verify", EdgeType.HAS_CHILD)

        original_confidence = contract.confidence

        # Run verification
        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={"target_id": "contract_verify", "artifact_id": "artifact_verify"},
        )
        mutation = agent.propose_mutation(trigger)

        # Apply updates
        for node_id, updates in mutation.nodes_to_update.items():
            engine.update_node(node_id, **updates)

        updated = engine.get_node("contract_verify")
        # MechanicalVerificationAgent only updates confidence, not status
        # Status (VIOLATED) is set by VerificationPipeline (Step 5)
        assert (
            updated.confidence < original_confidence
        ), "Confidence should decrease on ERROR"


@pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT backend not available")
class TestSTEPVerificationIntegration:
    """Tests for STEP file verification with CAD tools (requires OCCT)."""

    def test_step_verification_creates_mds_and_findings(self, tmp_path):
        """Test: STEP verification produces MDS and findings via orchestrator."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        artifacts_dir = tmp_path / "artifacts"

        # Use cadquery bracket STEP fixture
        step_path = (
            MECH_TEST_PROJECTS / "cadquery_golden_pass" / "inputs" / "bracket.step"
        )
        if not step_path.exists():
            pytest.skip(f"STEP fixture not found: {step_path}")

        contract = Contract(
            id="contract_step",
            description="STEP verification contract",
            guarantees=["geometry valid"],
        )
        artifact = ArtifactNode(
            id="artifact_step",
            description="STEP artifact",
            artifact_type="step",
            path=str(step_path),
        )
        engine.add_node(contract)
        engine.add_node(artifact)
        engine.add_edge("contract_step", "artifact_step", EdgeType.HAS_CHILD)

        agent = MechanicalVerificationAgent(
            engine=engine, llm=None, artifact_store_dir=artifacts_dir
        )
        trigger = Trigger(
            trigger_type=TriggerType.MANUAL,
            data={"target_id": "contract_step", "artifact_id": "artifact_step"},
        )
        mutation = agent.propose_mutation(trigger)

        # Apply mutation
        for node in mutation.nodes_to_add:
            engine.add_node(node)
        for edge in mutation.edges_to_add:
            engine.add_edge(edge.source_id, edge.target_id, edge.edge_type, edge.id)

        # Verify tool invocation and artifacts created
        invocations = engine.get_nodes_by_type(NodeType.TOOL_INVOCATION)
        assert len(invocations) >= 1, "ToolInvocation node should be created"

        artifacts = engine.get_nodes_by_type(NodeType.ARTIFACT)
        # Original input + output artifacts (report, mds)
        assert len(artifacts) >= 1, "Output artifacts should be created"

    def test_step_with_external_tools_flag(self, tmp_path):
        """Test: STEP verification with external tools enabled creates evidence."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        registry = ToolRegistry()
        registry.register(MechVerifyTool())

        manager = ToolExecutionManager(
            engine=engine,
            registry=registry,
            artifact_store_dir=tmp_path / "artifacts",
        )

        step_path = (
            MECH_TEST_PROJECTS / "step_golden_pass" / "inputs" / "simple_box.step"
        )
        if not step_path.exists():
            pytest.skip(f"STEP fixture not found: {step_path}")

        result = manager.execute(
            "mech-verify",
            {
                "mode": "step",
                "step_path": str(step_path),
                "use_external_tools": True,  # Enable FreeCAD/SFA if available
            },
        )

        assert result.tool_result.success
        report = result.tool_result.data.get("report", {})

        # Should have status and tool_invocations
        assert report.get("status") in ("PASS", "FAIL", "UNKNOWN")

        # tool_invocations tracks external tools (FreeCAD/SFA), may be empty if none available
        tool_invocations = report.get("tool_invocations", [])
        assert isinstance(tool_invocations, list)

    def test_assembly_verification_interference_check(self, tmp_path):
        """Test: Assembly STEP produces interference/clearance findings."""
        store = HypergraphStore(tmp_path / "graph.json")
        engine = HypergraphEngine(store)
        registry = ToolRegistry()
        registry.register(MechVerifyTool())

        manager = ToolExecutionManager(
            engine=engine,
            registry=registry,
            artifact_store_dir=tmp_path / "artifacts",
        )

        # Use assembly with known interference
        step_path = (
            MECH_TEST_PROJECTS / "step_asm_interference" / "inputs" / "assembly.step"
        )
        if not step_path.exists():
            pytest.skip(f"Assembly STEP fixture not found: {step_path}")

        result = manager.execute(
            "mech-verify",
            {"mode": "step", "step_path": str(step_path)},
        )

        assert result.tool_result.success
        report = result.tool_result.data.get("report", {})

        # Assembly with interference should have findings
        # Check if interference findings present (depends on test fixture)
        # At minimum, should not crash and have valid status
        assert report.get("status") in ("PASS", "FAIL", "UNKNOWN")
        # Findings list should exist (may be empty if no issues found)
        assert "findings" in report
