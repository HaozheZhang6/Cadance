"""Compute and compare confidence scores for verification results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.uncertainty.confidence import ConfidenceClassifier, EvidenceType

from .verification_runner import VerificationResult


@dataclass
class ConfidenceScore:
    """Confidence score for a verification result."""

    overall_confidence: float
    evidence_types: list[str] = field(default_factory=list)
    evidence_sources: dict[str, int] = field(default_factory=dict)
    confidence_by_source: dict[str, float] = field(default_factory=dict)
    verified_features: int = 0
    unverified_features: int = 0
    has_blockers: bool = False
    has_blocking_unknowns: bool = False

    def describe(self) -> str:
        """Human-readable confidence description."""
        classifier = ConfidenceClassifier()
        return classifier.describe(self.overall_confidence)


@dataclass
class ConfidenceComparison:
    """Comparison of confidence scores."""

    baseline: ConfidenceScore
    enhanced: ConfidenceScore
    confidence_improvement: float
    additional_evidence: list[str] = field(default_factory=list)
    improvement_factors: dict[str, Any] = field(default_factory=dict)

    @property
    def has_improvement(self) -> bool:
        """Check if enhanced confidence is better."""
        return self.confidence_improvement > 0.01

    @property
    def improvement_percentage(self) -> float:
        """Confidence improvement as percentage."""
        if self.baseline.overall_confidence == 0:
            return 0.0
        return (self.confidence_improvement / self.baseline.overall_confidence) * 100


class ConfidenceAnalyzer:
    """Analyze confidence scores from verification results."""

    def __init__(self):
        """Initialize analyzer."""
        self.classifier = ConfidenceClassifier()

    def analyze_result(self, result: VerificationResult) -> ConfidenceScore:
        """
        Compute confidence score for verification result.

        Confidence based on:
        - Evidence types (findings, unknowns, MDS data)
        - External tool evidence
        - Verification completeness

        Args:
            result: Verification result to analyze

        Returns:
            ConfidenceScore with computed metrics
        """
        evidence_types = []
        evidence_sources = {}
        confidence_by_source = {}

        # Base confidence from verification status
        if not result.success:
            return ConfidenceScore(
                overall_confidence=0.0,
                has_blockers=True,
            )

        # Geometry backend evidence
        if result.mds:
            evidence_types.append("geometry_analysis")
            evidence_sources["geometry"] = 1
            confidence_by_source["geometry"] = self.classifier.classify(
                EvidenceType.FIRST_PRINCIPLES
            )

        # External tool evidence
        if result.report and result.report.tool_invocations:
            for invocation in result.report.tool_invocations:
                tool_name = invocation.get("tool_name", "unknown")
                if tool_name not in ["OCCT", "geometry"]:
                    evidence_types.append(f"external_tool:{tool_name}")
                    evidence_sources[tool_name] = evidence_sources.get(tool_name, 0) + 1
                    # External tools provide tested evidence
                    confidence_by_source[tool_name] = self.classifier.classify(
                        EvidenceType.TESTED_INTERNALLY
                    )

        # SHACL validation evidence
        shacl_findings = [f for f in result.findings if "shacl" in f.rule_id.lower()]
        if shacl_findings:
            evidence_types.append("shacl_validation")
            evidence_sources["shacl"] = len(shacl_findings)
            confidence_by_source["shacl"] = self.classifier.classify(
                EvidenceType.FIRST_PRINCIPLES
            )

        # Schema validation evidence
        schema_findings = [f for f in result.findings if "schema" in f.rule_id.lower()]
        if schema_findings:
            evidence_types.append("schema_validation")
            evidence_sources["schema"] = len(schema_findings)
            # Schema validation is tested/automated validation
            confidence_by_source["schema"] = self.classifier.classify(
                EvidenceType.TESTED_INTERNALLY
            )

        # DFM rules evidence
        dfm_findings = [f for f in result.findings if "dfm" in f.rule_id.lower()]
        if dfm_findings:
            evidence_types.append("dfm_rules")
            evidence_sources["dfm"] = len(dfm_findings)
            confidence_by_source["dfm"] = self.classifier.classify(
                EvidenceType.PUBLISHED_LITERATURE
            )

        # Assembly checks evidence
        asm_findings = [f for f in result.findings if "assembly" in f.rule_id.lower()]
        if asm_findings:
            evidence_types.append("assembly_checks")
            evidence_sources["assembly"] = len(asm_findings)
            confidence_by_source["assembly"] = self.classifier.classify(
                EvidenceType.FIRST_PRINCIPLES
            )

        # PMI evidence
        if result.mds and result.mds.get("pmi", {}).get("has_semantic_pmi"):
            evidence_types.append("semantic_pmi")
            evidence_sources["pmi"] = 1
            confidence_by_source["pmi"] = self.classifier.classify(
                EvidenceType.DATASHEET
            )

        # Compute overall confidence
        overall = self._compute_overall_confidence(
            confidence_by_source, result.has_blockers, result.has_blocking_unknowns
        )

        # Count verified features
        verified_features = 0
        unverified_features = 0
        if result.mds and "features" in result.mds:
            verified_features = len(result.mds["features"])
        if result.unknowns:
            unverified_features = len(result.unknowns)

        return ConfidenceScore(
            overall_confidence=overall,
            evidence_types=evidence_types,
            evidence_sources=evidence_sources,
            confidence_by_source=confidence_by_source,
            verified_features=verified_features,
            unverified_features=unverified_features,
            has_blockers=result.has_blockers,
            has_blocking_unknowns=result.has_blocking_unknowns,
        )

    def compare_results(
        self, baseline: VerificationResult, enhanced: VerificationResult
    ) -> ConfidenceComparison:
        """
        Compare confidence between baseline and enhanced verification.

        Args:
            baseline: Baseline verification (minimal checks)
            enhanced: Enhanced verification (full checks)

        Returns:
            ConfidenceComparison with improvement metrics
        """
        baseline_score = self.analyze_result(baseline)
        enhanced_score = self.analyze_result(enhanced)

        improvement = (
            enhanced_score.overall_confidence - baseline_score.overall_confidence
        )

        # Identify additional evidence
        additional_evidence = [
            e
            for e in enhanced_score.evidence_types
            if e not in baseline_score.evidence_types
        ]

        # Compute improvement factors
        improvement_factors = {
            "additional_evidence_sources": len(additional_evidence),
            "additional_verified_features": (
                enhanced_score.verified_features - baseline_score.verified_features
            ),
            "reduced_unknowns": (
                baseline_score.unverified_features - enhanced_score.unverified_features
            ),
            "new_tool_invocations": len(
                set(enhanced_score.evidence_sources.keys())
                - set(baseline_score.evidence_sources.keys())
            ),
        }

        return ConfidenceComparison(
            baseline=baseline_score,
            enhanced=enhanced_score,
            confidence_improvement=improvement,
            additional_evidence=additional_evidence,
            improvement_factors=improvement_factors,
        )

    def _compute_overall_confidence(
        self,
        confidence_by_source: dict[str, float],
        has_blockers: bool,
        has_blocking_unknowns: bool,
    ) -> float:
        """
        Compute overall confidence from source confidences.

        Uses weighted average with penalty for blockers/unknowns.
        """
        if not confidence_by_source:
            return self.classifier.classify(EvidenceType.UNKNOWN)

        # Weighted average (equal weights for now)
        overall = sum(confidence_by_source.values()) / len(confidence_by_source)

        # Apply penalties
        if has_blockers:
            overall *= 0.5  # 50% penalty for blockers
        if has_blocking_unknowns:
            overall *= 0.8  # 20% penalty for unknowns

        return max(0.0, min(1.0, overall))
