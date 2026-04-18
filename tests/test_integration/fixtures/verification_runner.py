"""Run mech_verify on STEP files and collect results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.mech_verifier.mech_verify.orchestrator import (
    VerificationConfig,
    VerificationOrchestrator,
    VerificationReport,
)
from verifier_core.models import Finding, Severity, Unknown


@dataclass
class VerificationResult:
    """Result from mech_verify execution."""

    success: bool
    status: str  # PASS, FAIL, UNKNOWN
    findings: list[Finding] = field(default_factory=list)
    unknowns: list[Unknown] = field(default_factory=list)
    mds: dict[str, Any] | None = None
    report: VerificationReport | None = None
    error: str | None = None

    @property
    def has_blockers(self) -> bool:
        """Check if any blocker findings."""
        return any(f.severity == Severity.BLOCKER for f in self.findings)

    @property
    def has_errors(self) -> bool:
        """Check if any error findings."""
        return any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        """Check if any warning findings."""
        return any(f.severity == Severity.WARN for f in self.findings)

    @property
    def has_blocking_unknowns(self) -> bool:
        """Check if any blocking unknowns."""
        return any(u.blocking for u in self.unknowns)

    def count_findings_by_severity(self) -> dict[str, int]:
        """Count findings by severity."""
        counts = {"BLOCKER": 0, "ERROR": 0, "WARN": 0, "INFO": 0}
        for finding in self.findings:
            severity_str = (
                finding.severity.value
                if hasattr(finding.severity, "value")
                else str(finding.severity)
            )
            if severity_str in counts:
                counts[severity_str] += 1
        return counts


class VerificationRunner:
    """Run mech_verify with various configurations."""

    def __init__(self, config: VerificationConfig | None = None):
        """Initialize runner with optional config."""
        self.config = config or VerificationConfig()

    def verify_step(
        self,
        step_path: Path,
        manifest_path: Path | None = None,
        ops_program_path: Path | None = None,
        enable_shacl: bool = False,
        require_pmi: bool = False,
        use_external_tools: bool = False,
    ) -> VerificationResult:
        """
        Verify STEP file with mech_verify.

        Args:
            step_path: Path to STEP file
            manifest_path: Optional CadQuery manifest
            ops_program_path: Optional ops program JSON
            enable_shacl: Enable SHACL validation
            require_pmi: Require PMI data
            use_external_tools: Use external tool adapters

        Returns:
            VerificationResult with findings and status
        """
        config = VerificationConfig(
            validate_schema=self.config.validate_schema,
            shacl=enable_shacl or self.config.shacl,
            require_pmi=require_pmi or self.config.require_pmi,
            use_external_tools=use_external_tools or self.config.use_external_tools,
            units_length=self.config.units_length,
            units_angle=self.config.units_angle,
            cadquery_manifest=manifest_path or self.config.cadquery_manifest,
            ops_program=ops_program_path or self.config.ops_program,
        )

        try:
            orchestrator = VerificationOrchestrator(config)
            report = orchestrator.verify([step_path])

            return VerificationResult(
                success=True,
                status=report.status,
                findings=report.findings,
                unknowns=report.unknowns,
                mds=report.mds,
                report=report,
                error=None,
            )

        except Exception as e:
            return VerificationResult(
                success=False,
                status="UNKNOWN",
                error=f"Verification failed: {e}",
            )

    def verify_multiple(
        self, step_paths: list[Path], **kwargs
    ) -> list[VerificationResult]:
        """Verify multiple STEP files."""
        results = []
        for step_path in step_paths:
            result = self.verify_step(step_path, **kwargs)
            results.append(result)
        return results

    def compare_results(
        self, baseline: VerificationResult, enhanced: VerificationResult
    ) -> dict[str, Any]:
        """
        Compare two verification results.

        Args:
            baseline: Baseline verification result
            enhanced: Enhanced verification result (with additional checks)

        Returns:
            Comparison metrics
        """
        baseline_counts = baseline.count_findings_by_severity()
        enhanced_counts = enhanced.count_findings_by_severity()

        return {
            "baseline_status": baseline.status,
            "enhanced_status": enhanced.status,
            "baseline_findings": baseline_counts,
            "enhanced_findings": enhanced_counts,
            "additional_findings": {
                k: enhanced_counts[k] - baseline_counts[k]
                for k in baseline_counts.keys()
            },
            "baseline_unknowns": len(baseline.unknowns),
            "enhanced_unknowns": len(enhanced.unknowns),
            "baseline_blocking_unknowns": sum(
                1 for u in baseline.unknowns if u.blocking
            ),
            "enhanced_blocking_unknowns": sum(
                1 for u in enhanced.unknowns if u.blocking
            ),
        }
