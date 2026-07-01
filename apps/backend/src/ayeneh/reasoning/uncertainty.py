"""Uncertainty estimation — estimates confidence based on evidence quality and coverage."""

from __future__ import annotations

import structlog

from ayeneh.reasoning.types import Conflict, Evidence

logger = structlog.get_logger(__name__)


class UncertaintyEstimator:
    """Estimates uncertainty and computes calibrated confidence."""

    def estimate(
        self,
        evidence: list[Evidence],
        conflicts: list[Conflict],
        alternatives_count: int,
        source_coverage: set[str] | None = None,
    ) -> tuple[float, list[str]]:
        if not evidence:
            return 0.1, ["No evidence available"]

        quality_score = self._evidence_quality(evidence)
        agreement_score = self._agreement_score(evidence)
        coverage_score = self._coverage_score(evidence, source_coverage)
        recency_score = self._recency_score(evidence)
        conflict_penalty = self._conflict_penalty(conflicts)

        confidence = (
            quality_score * 0.3
            + agreement_score * 0.25
            + coverage_score * 0.2
            + recency_score * 0.15
            - conflict_penalty * 0.1
        )
        confidence = max(0.05, min(0.95, confidence))

        reasons = []
        if quality_score < 0.5:
            reasons.append("Low average evidence quality")
        if agreement_score < 0.5:
            reasons.append("Mixed signals in evidence")
        if coverage_score < 0.5:
            reasons.append("Limited source diversity")
        if conflict_penalty > 0.3:
            reasons.append(f"{len(conflicts)} conflict(s) detected")
        if alternatives_count > 2:
            reasons.append("Multiple competing alternatives")

        return confidence, reasons

    @staticmethod
    def _evidence_quality(evidence: list[Evidence]) -> float:
        if not evidence:
            return 0.0
        return sum(e.confidence for e in evidence) / len(evidence)

    @staticmethod
    def _agreement_score(evidence: list[Evidence]) -> float:
        if len(evidence) < 2:
            return 0.7
        confidences = [e.confidence for e in evidence]
        mean = sum(confidences) / len(confidences)
        variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
        return max(0.0, 1.0 - variance * 2)

    @staticmethod
    def _coverage_score(evidence: list[Evidence], source_coverage: set[str] | None) -> float:
        all_sources = {"goal", "memory", "knowledge", "pattern", "reflection", "blind_spot", "conversation"}
        if not source_coverage:
            source_coverage = set(e.source_type for e in evidence)
        covered = len(source_coverage & all_sources)
        return min(1.0, covered / 3)

    @staticmethod
    def _recency_score(evidence: list[Evidence]) -> float:
        if not evidence:
            return 0.0
        avg_recency = sum(e.recency_days for e in evidence) / len(evidence)
        return max(0.0, 1.0 - min(avg_recency / 180, 1.0))

    @staticmethod
    def _conflict_penalty(conflicts: list[Conflict]) -> float:
        if not conflicts:
            return 0.0
        avg_severity = sum(c.severity for c in conflicts) / len(conflicts)
        return min(1.0, avg_severity * min(len(conflicts) / 3, 1.0))
