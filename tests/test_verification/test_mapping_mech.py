"""Tests for mech mapping to hypergraph evidence/unknown."""

from src.hypergraph.models import EdgeType, NodeType
from src.verification.mapping_mech import map_mech_results
from verifier_core.models import Finding, Severity, Unknown


def test_map_mech_results_creates_evidence_and_unknown_edges():
    """Mapping should create Evidence/Unknown nodes and edges."""
    findings = [
        Finding(
            rule_id="mech.tier0.hole_min_diameter",
            severity=Severity.ERROR,
            message="Hole diameter below minimum",
        )
    ]
    unknowns = [
        Unknown(
            summary="PMI missing",
            impact="Cannot confirm tolerances",
            resolution_plan="Provide PMI data",
            blocking=True,
            created_by_rule_id="mech.tier0.pmi_required",
        )
    ]

    mutation = map_mech_results(
        findings=findings,
        unknowns=unknowns,
        target_id="contract_001",
        tool_name="mech-verify",
        report_id="report_001",
    )

    evidence_nodes = [
        n for n in mutation.nodes_to_add if n.node_type == NodeType.EVIDENCE
    ]
    unknown_nodes = [
        n for n in mutation.nodes_to_add if n.node_type == NodeType.UNKNOWN
    ]

    assert len(evidence_nodes) == 1
    assert len(unknown_nodes) == 1

    validates_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.VALIDATES
    ]
    depends_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.DEPENDS_ON
    ]

    assert validates_edges
    assert depends_edges


def test_map_mech_results_source_spec_ids_in_evidence_data():
    """Evidence data includes source_spec_ids from Finding."""
    findings = [
        Finding(
            rule_id="mech.tier0.hole_min_diameter",
            severity=Severity.ERROR,
            message="Hole too small",
            source_spec_ids=["S1.1.1"],
        )
    ]
    mutation = map_mech_results(
        findings=findings,
        unknowns=[],
        target_id="contract_001",
        tool_name="mech-verify",
        report_id="report_001",
    )
    evidence_nodes = [
        n for n in mutation.nodes_to_add if n.node_type == NodeType.EVIDENCE
    ]
    assert len(evidence_nodes) == 1
    assert evidence_nodes[0].data["source_spec_ids"] == ["S1.1.1"]


def test_map_mech_results_creates_spec_validates_edges():
    """With grs_mapping, creates Evidence→Specification VALIDATES edges."""
    findings = [
        Finding(
            rule_id="mech.tier0.hole_min_diameter",
            severity=Severity.ERROR,
            message="Hole too small",
            source_spec_ids=["S1.1.1", "S1.1.2"],
        )
    ]
    grs_mapping = {"S1.1.1": "spec_node_001", "S1.1.2": "spec_node_002"}
    mutation = map_mech_results(
        findings=findings,
        unknowns=[],
        target_id="contract_001",
        tool_name="mech-verify",
        report_id="report_001",
        grs_mapping=grs_mapping,
    )
    validates_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.VALIDATES
    ]
    # 1 contract edge + 2 spec edges = 3
    assert len(validates_edges) == 3
    spec_targets = {e.target_id for e in validates_edges} - {"contract_001"}
    assert spec_targets == {"spec_node_001", "spec_node_002"}


def test_map_mech_results_no_grs_mapping_no_spec_edges():
    """Without grs_mapping, no spec edges even with source_spec_ids."""
    findings = [
        Finding(
            rule_id="r1",
            severity=Severity.ERROR,
            message="m",
            source_spec_ids=["S1.1.1"],
        )
    ]
    mutation = map_mech_results(
        findings=findings,
        unknowns=[],
        target_id="contract_001",
        tool_name="mech-verify",
        report_id="report_001",
    )
    validates_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.VALIDATES
    ]
    # Only 1 contract edge
    assert len(validates_edges) == 1
    assert validates_edges[0].target_id == "contract_001"


def test_map_mech_results_unknown_spec_id_skipped():
    """Unknown grs_id (not in mapping) is skipped gracefully."""
    findings = [
        Finding(
            rule_id="r1",
            severity=Severity.ERROR,
            message="m",
            source_spec_ids=["S99.99"],
        )
    ]
    grs_mapping = {"S1.1.1": "spec_node_001"}
    mutation = map_mech_results(
        findings=findings,
        unknowns=[],
        target_id="contract_001",
        tool_name="mech-verify",
        report_id="report_001",
        grs_mapping=grs_mapping,
    )
    validates_edges = [
        e for e in mutation.edges_to_add if e.edge_type == EdgeType.VALIDATES
    ]
    # Only contract edge, unknown spec skipped
    assert len(validates_edges) == 1
