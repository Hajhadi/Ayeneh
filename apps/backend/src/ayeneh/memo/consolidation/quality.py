"""Consolidation quality assessment (MEM-05).

Provides quality metrics and validation for consolidation decisions,
including evidence quality scoring, confidence calibration, and
consolidation health monitoring.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.consolidation.types import (
    CONSOLIDATION_CRITERIA,
    ConsolidationCriteriaResult,
    ConsolidationObject,
    EvidenceAggregation,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualityMetrics:
    """Quality metrics for a consolidation decision."""

    consolidation_id: str
    evidence_quality: float = 0.0
    confidence_calibration: float = 0.0
    criteria_coverage: float = 0.0
    temporal_consistency: float = 0.0
    cross_validation_score: float = 0.0
    overall_quality: float = 0.0


# ---------------------------------------------------------------------------
# Quality assessor
# ---------------------------------------------------------------------------


class ConsolidationQualityAssessor:
    """Assesses the quality of consolidation decisions.

    Provides metrics on evidence quality, confidence calibration,
    criteria coverage, and temporal consistency.
    """

    def __init__(self) -> None:
        self._assessment_history: list[QualityMetrics] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(
        self,
        consolidation: ConsolidationObject,
        criteria_result: ConsolidationCriteriaResult | None = None,
    ) -> QualityMetrics:
        """Assess the quality of a consolidation decision."""
        evidence_quality = self._assess_evidence_quality(consolidation)
        confidence_calibration = self._assess_confidence_calibration(consolidation)
        criteria_coverage = self._assess_criteria_coverage(criteria_result)
        temporal_consistency = self._assess_temporal_consistency(consolidation)
        cross_validation = self._assess_cross_validation(consolidation)

        overall = (
            evidence_quality * 0.25
            + confidence_calibration * 0.2
            + criteria_coverage * 0.25
            + temporal_consistency * 0.15
            + cross_validation * 0.15
        )

        metrics = QualityMetrics(
            consolidation_id=consolidation.identifier,
            evidence_quality=evidence_quality,
            confidence_calibration=confidence_calibration,
            criteria_coverage=criteria_coverage,
            temporal_consistency=temporal_consistency,
            cross_validation_score=cross_validation,
            overall_quality=overall,
        )

        self._assessment_history.append(metrics)

        logger.debug(
            'consolidation_quality_assessed',
            consolidation_id=consolidation.identifier,
            overall_quality=overall,
        )

        return metrics

    def assess_batch(
        self,
        consolidations: list[ConsolidationObject],
        criteria_results: list[ConsolidationCriteriaResult] | None = None,
    ) -> list[QualityMetrics]:
        """Assess a batch of consolidation decisions."""
        criteria_results = criteria_results or []
        criteria_map = {cr.memory_id: cr for cr in criteria_results}

        results: list[QualityMetrics] = []
        for cons in consolidations:
            cr = criteria_map.get(cons.target_memory)
            metrics = self.assess(cons, cr)
            results.append(metrics)

        return results

    def get_average_quality(self) -> float:
        """Return the average quality across all assessments."""
        if not self._assessment_history:
            return 0.0
        return sum(m.overall_quality for m in self._assessment_history) / len(
            self._assessment_history
        )

    def get_assessment_history(self) -> list[QualityMetrics]:
        """Return the full assessment history."""
        return list(self._assessment_history)

    # ------------------------------------------------------------------
    # Quality dimensions
    # ------------------------------------------------------------------

    def _assess_evidence_quality(self, consolidation: ConsolidationObject) -> float:
        """Assess the quality of evidence supporting the consolidation."""
        evidence_count = len(consolidation.supporting_episodes) + len(
            consolidation.supporting_conversations
        )
        if evidence_count <= 0:
            return 0.0
        if evidence_count >= 5:
            return 1.0
        return evidence_count / 5.0

    def _assess_confidence_calibration(self, consolidation: ConsolidationObject) -> float:
        """Assess whether confidence changes are well-calibrated."""
        delta = consolidation.confidence_delta
        if consolidation.is_promoted:
            # For promotions, positive delta is good
            return min(1.0, max(0.0, 0.5 + delta))
        elif consolidation.is_rejected:
            # For rejections, negative delta is expected
            return min(1.0, max(0.0, 0.5 - delta))
        return 0.5

    def _assess_criteria_coverage(
        self,
        criteria_result: ConsolidationCriteriaResult | None,
    ) -> float:
        """Assess how well the consolidation criteria were covered."""
        if criteria_result is None:
            return 0.0
        return criteria_result.criteria_fraction

    def _assess_temporal_consistency(self, consolidation: ConsolidationObject) -> float:
        """Assess temporal consistency of the consolidation."""
        # Check that supporting episodes span a reasonable time range
        if not consolidation.supporting_episodes:
            return 0.3
        # More episodes generally means better temporal consistency
        count = len(consolidation.supporting_episodes)
        return min(1.0, count / 3.0)

    def _assess_cross_validation(self, consolidation: ConsolidationObject) -> float:
        """Assess cross-validation across different sources."""
        sources = set()
        for ep in consolidation.supporting_episodes:
            sources.add('episode')
        for conv in consolidation.supporting_conversations:
            sources.add('conversation')
        for cog in consolidation.affected_cognitive_objects:
            sources.add('cognitive')

        if len(sources) <= 1:
            return 0.3
        return min(1.0, len(sources) / 3.0)
