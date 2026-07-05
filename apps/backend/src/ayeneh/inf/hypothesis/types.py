"""INF-05 Hypothesis Engine types.

Defines HypothesisObject, HypothesisFamily, HypothesisResult, and
supporting value objects for the scientific hypothesis pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

HYPOTHESIS_STATUSES: list[str] = [
    'active',
    'strengthening',
    'weakening',
    'confirmed',
    'rejected',
    'archived',
]

HYPOTHESIS_SOURCES: list[str] = [
    'observed_behavior',
    'graph_structure',
    'contradiction',
    'longitudinal_trend',
    'unexpected_event',
    'prediction_failure',
    'user_question',
    'missing_explanation',
]

HYPOTHESIS_TYPES: list[str] = [
    'causal',
    'correlational',
    'structural',
    'temporal',
    'behavioral',
    'identity',
]

EVIDENCE_QUALITY_DIMENSIONS: list[str] = [
    'directness',
    'specificity',
    'temporal_proximity',
    'consistency',
    'source_reliability',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceQuality:
    """Multi-dimensional assessment of evidence quality for hypothesis testing."""

    directness: float = 0.5
    specificity: float = 0.5
    temporal_proximity: float = 0.5
    consistency: float = 0.5
    source_reliability: float = 0.5

    def overall(self) -> float:
        """Weighted average across all dimensions."""
        return (
            self.directness * 0.25
            + self.specificity * 0.20
            + self.temporal_proximity * 0.20
            + self.consistency * 0.20
            + self.source_reliability * 0.15
        )


@dataclass(frozen=True)
class PredictedObservation:
    """A concrete observation that the hypothesis predicts should exist."""

    prediction_id: str = ''
    description: str = ''
    evidence_type: str = ''
    required: bool = True


@dataclass(frozen=True)
class EvidenceGap:
    """Identifies missing evidence needed to evaluate a hypothesis."""

    gap_id: str = ''
    description: str = ''
    importance: float = 0.0  # 0–1
    collection_method: str = ''


@dataclass(frozen=True)
class HypothesisRevision:
    """A record of a hypothesis revision event."""

    revision_id: str = ''
    reason: str = ''
    old_confidence: float = 0.0
    new_confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HypothesisObject:
    """A single scientific hypothesis (INF-05)."""

    hypothesis_id: str
    originating_context: str = ''
    target_question: str = ''
    statement: str = ''
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    competing_hypotheses: tuple[str, ...] = ()
    confidence: float = 0.0
    expected_predictions: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    revision_history: tuple[dict[str, Any], ...] = ()
    current_status: str = 'active'
    version_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class HypothesisFamily:
    """A group of related hypotheses sharing a common theme."""

    family_id: str
    family_name: str = ''
    hypothesis_ids: tuple[str, ...] = ()
    shared_evidence: tuple[str, ...] = ()
    family_confidence: float = 0.0


@dataclass(frozen=True)
class HypothesisResult:
    """Complete result of the hypothesis generation pipeline."""

    hypotheses: tuple[HypothesisObject, ...] = ()
    families: tuple[HypothesisFamily, ...] = ()
    evidence_gaps: tuple[EvidenceGap, ...] = ()
    predictions: tuple[PredictedObservation, ...] = ()
    strongest_hypothesis: str = ''  # hypothesis_id
    overall_confidence: float = 0.0
    processing_metadata: dict[str, Any] = field(default_factory=dict)
