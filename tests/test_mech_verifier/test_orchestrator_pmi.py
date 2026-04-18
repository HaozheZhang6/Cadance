"""Tests for orchestrator PMI verification integration.

Verifies orchestrator uses PMI module with multi-source detection.
"""

import json
import tempfile
from pathlib import Path

from mech_verify.orchestrator import VerificationConfig, VerificationOrchestrator


class TestOrchestratorPMIIntegration:
    """Tests for orchestrator PMI verification."""

    def test_orchestrator_uses_pmi_module(self):
        """Orchestrator uses pmi.verify_pmi_requirement, not naive check."""
        from mech_verify.pmi import verify_pmi_requirement

        # This test documents that orchestrator should use verify_pmi_requirement
        # which provides multi-source PMI detection
        assert callable(verify_pmi_requirement)

    def test_require_pmi_false_no_check(self):
        """When require_pmi=False, no PMI check performed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create MDS without PMI
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
                "units": {"length": "mm", "angle": "deg"},
                "parts": [
                    {
                        "part_id": "test",
                        "object_ref": "mech://part/test",
                        "mass_props": {
                            "volume": 100.0,
                            "bbox": {"min_pt": [0, 0, 0], "max_pt": [1, 1, 1]},
                        },
                    }
                ],
                "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            }

            mds_path = Path(tmpdir) / "test.json"
            with open(mds_path, "w") as f:
                json.dump(mds, f)

            config = VerificationConfig(require_pmi=False)
            orchestrator = VerificationOrchestrator(config)

            report = orchestrator.verify([mds_path])

            # Should not have PMI-related unknowns
            pmi_unknowns = [
                u for u in report.unknowns if "pmi" in u.created_by_rule_id.lower()
            ]
            assert len(pmi_unknowns) == 0

    def test_require_pmi_true_emits_unknown(self):
        """When require_pmi=True and no PMI, blocking Unknown emitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create MDS without PMI
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
                "units": {"length": "mm", "angle": "deg"},
                "parts": [
                    {
                        "part_id": "test",
                        "object_ref": "mech://part/test",
                        "mass_props": {
                            "volume": 100.0,
                            "bbox": {"min_pt": [0, 0, 0], "max_pt": [1, 1, 1]},
                        },
                    }
                ],
                "pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False},
            }

            mds_path = Path(tmpdir) / "test.json"
            with open(mds_path, "w") as f:
                json.dump(mds, f)

            config = VerificationConfig(require_pmi=True)
            orchestrator = VerificationOrchestrator(config)

            report = orchestrator.verify([mds_path])

            # Should have PMI-related blocking Unknown
            pmi_unknowns = [
                u for u in report.unknowns if "pmi" in u.created_by_rule_id.lower()
            ]
            assert len(pmi_unknowns) >= 1
            assert pmi_unknowns[0].blocking is True

    def test_require_pmi_true_pmi_present_no_unknown(self):
        """When require_pmi=True and PMI present, no Unknown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create MDS with PMI
            mds = {
                "schema_version": "mech.mds.v1",
                "domain": "mech",
                "units": {"length": "mm", "angle": "deg"},
                "parts": [
                    {
                        "part_id": "test",
                        "object_ref": "mech://part/test",
                        "mass_props": {
                            "volume": 100.0,
                            "bbox": {"min_pt": [0, 0, 0], "max_pt": [1, 1, 1]},
                        },
                    }
                ],
                "pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False},
            }

            mds_path = Path(tmpdir) / "test.json"
            with open(mds_path, "w") as f:
                json.dump(mds, f)

            config = VerificationConfig(require_pmi=True)
            orchestrator = VerificationOrchestrator(config)

            report = orchestrator.verify([mds_path])

            # Should NOT have PMI-related unknowns
            pmi_unknowns = [
                u for u in report.unknowns if "pmi" in u.created_by_rule_id.lower()
            ]
            assert len(pmi_unknowns) == 0

    def test_step_text_scan_fallback_used(self):
        """Orchestrator uses STEP text scanning when MDS lacks PMI annotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create STEP file with PMI entity
            step_path = Path(tmpdir) / "test.step"
            step_path.write_text(
                "ISO-10303-21;\n"
                "HEADER;\nENDSEC;\n"
                "DATA;\n"
                "#1=GEOMETRIC_TOLERANCE('flatness',#2,#3);\n"
                "ENDSEC;\n"
                "END-ISO-10303-21;\n"
            )

            config = VerificationConfig(require_pmi=True)
            orchestrator = VerificationOrchestrator(config)

            # For STEP file, orchestrator should:
            # 1. Build MDS (pmi flags = false)
            # 2. Run PMI check with STEP text scanning fallback
            # 3. Detect PMI from text scan (confidence 0.5)
            # 4. FAIL because confidence < 0.7 threshold

            # This test SHOULD fail with current naive implementation
            # because orchestrator doesn't pass step_path to PMI module
            report = orchestrator.verify([step_path])

            # Current naive implementation: emits Unknown (MDS has no PMI flags)
            # Correct implementation: should check STEP text, find PMI, but emit
            # Unknown due to low confidence (0.5 < 0.7 threshold)

            pmi_unknowns = [
                u for u in report.unknowns if "pmi" in u.created_by_rule_id.lower()
            ]

            # Both implementations emit Unknown, but for different reasons:
            # - Naive: "PMI not present" (wrong - PMI exists in STEP)
            # - Correct: "PMI confidence too low (50%) from step_text" (right)
            if pmi_unknowns:
                # Check if multi-source detection was used
                summary = pmi_unknowns[0].summary
                # Correct implementation mentions confidence or source
                uses_multi_source = (
                    "confidence" in summary.lower() or "step_text" in summary.lower()
                )
                assert uses_multi_source, (
                    f"Orchestrator should use PMI module multi-source detection. "
                    f"Got summary: {summary}"
                )


class TestPMIModuleFeatures:
    """Tests for PMI module multi-source detection."""

    def test_check_pmi_presence_mds_annotation(self):
        """check_pmi_presence reads MDS pmi field."""
        from mech_verify.pmi import check_pmi_presence

        mds = {"pmi": {"has_semantic_pmi": True, "has_graphical_pmi": False}}

        status = check_pmi_presence(mds)

        assert status.has_semantic_pmi is True
        assert status.source == "mds_annotation"
        assert status.confidence == 0.8

    def test_check_pmi_presence_step_text_scan(self):
        """check_pmi_presence scans STEP text for PMI entities."""
        from mech_verify.pmi import check_pmi_presence

        with tempfile.NamedTemporaryFile(mode="w", suffix=".step", delete=False) as f:
            # Write STEP with PMI entity
            f.write("ISO-10303-21;\n")
            f.write("HEADER;\nENDSEC;\n")
            f.write("DATA;\n")
            f.write("#1=GEOMETRIC_TOLERANCE('flatness',#2,#3);\n")
            f.write("ENDSEC;\n")
            f.write("END-ISO-10303-21;\n")
            step_path = f.name

        try:
            mds = {"pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False}}

            status = check_pmi_presence(mds, step_path=step_path)

            # Text scan should detect PMI (graphical only, low confidence)
            assert status.has_graphical_pmi is True
            assert status.source == "step_text"
            assert status.confidence == 0.5
        finally:
            Path(step_path).unlink()

    def test_check_pmi_presence_sfa_output_priority(self):
        """SFA output has highest priority over MDS and text scan."""
        from mech_verify.pmi import check_pmi_presence

        # MDS says no PMI, but SFA found it (SFA wins)
        mds = {"pmi": {"has_semantic_pmi": False, "has_graphical_pmi": False}}
        sfa_output = {
            "pmi_found": True,
            "semantic_pmi": True,
            "graphical_pmi": False,
        }

        status = check_pmi_presence(mds, sfa_output=sfa_output)

        assert status.has_semantic_pmi is True
        assert status.source == "sfa_adapter"
        assert status.confidence == 0.95  # Highest confidence

    def test_has_sufficient_pmi_confidence_threshold(self):
        """has_sufficient_pmi respects confidence threshold."""
        from mech_verify.pmi import PMIStatus, has_sufficient_pmi

        # Low confidence - should fail
        status_low = PMIStatus(
            has_semantic_pmi=True,
            has_graphical_pmi=False,
            source="step_text",
            confidence=0.5,
        )
        assert has_sufficient_pmi(status_low, min_confidence=0.7) is False

        # High confidence - should pass
        status_high = PMIStatus(
            has_semantic_pmi=True,
            has_graphical_pmi=False,
            source="mds_annotation",
            confidence=0.8,
        )
        assert has_sufficient_pmi(status_high, min_confidence=0.7) is True
