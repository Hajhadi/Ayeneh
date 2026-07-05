"""Types for the consolidation subsystem (MEM-05).

Defines ConsolidationObject, ConsolidationCriteria, and all associated
enumerations and value objects for promoting working memories to long-term storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Consolidation criteria enumerations
# ---------------------------------------------------------------------------

CONSOLIDATION_CRITERIA: list[str] = [
    'repeated_observation',
    'behavioral_confirmation',
    'cross_context_consistency',
    'cross_episode_recurrence',
    'identity_relevance',
    'goal_relevance',
    'value_relevance',
    'longitudinal_persistence',
    'high_quality_evidence',
]

# ---------------------------------------------------------------------------
# Consolidation level enumerations (per spec hierarchy)
# ---------------------------------------------------------------------------

CONSOLIDATION_LEVEL_HIERARCHY: list[str] = [
    'observation',
    'candidate',
    'emerging_pattern',
    'validated_pattern',
    'stable_longterm',
    'core_personal_knowledge',
]

CONSOLIDATION_LEVEL_HIERARCHY_VALUES: dict[str, int] = {
    'observation': 0,
    'candidate': 1,
    'emerging_pattern': 2,
    'validated_pattern': 3,
    'stable_longterm': 4,
    'core_personal_knowledge': 5,
}

# ---------------------------------------------------------------------------
# Consolidation decision outcomes
# ---------------------------------------------------------------------------

CONSOLIDATION_DECISIONS: list[str] = [
    'promote',
    'reject',
    'defer',
    'merge',
    'split',
    'archive',
]

# ---------------------------------------------------------------------------
# Evidence aggregation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceAggregation:
    """Aggregated evidence supporting a consolidation decision."""

    aggregation_id: str
    evidence_ids: tuple[str, ...] = ()
    total_evidence_count: int = 0
    supporting_count: int = 0
    contradicting_count: int = 0
    aggregated_confidence: float = 0.0
    quality_score: float = 0.0
    diversity_score: float = 0.0

    @property
    def support_ratio(self) -> float:
        """Fraction of evidence that supports the consolidation."""
        if self.total_evidence_count <= 0:
            return 0.0
        return self.supporting_count / self.total_evidence_count

    @property
    def has_sufficient_evidence(self) -> bool:
        return self.total_evidence_count >= 2 and self.support_ratio >= 0.6


# ---------------------------------------------------------------------------
# ConsolidationObject
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsolidationObject:
    """A record of a consolidation decision.

    Tracks the before/after confidence, the evidence supporting the decision,
    which episodes and conversations contributed, and any affected cognitive
    objects.
    """

    identifier: str
    target_memory: str
    evidence_summary: str = ''
    supporting_episodes: tuple[str, ...] = ()
    supporting_conversations: tuple[str, ...] = ()
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    reason_for_promotion: str = ''
    reason_for_rejection: str = ''
    affected_cognitive_objects: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    version_history: tuple[dict[str, Any], ...] = ()

    @property
    def confidence_delta(self) -> float:
        """Change in confidence from consolidation."""
        return self.confidence_after - self.confidence_before

    @property
    def is_promoted(self) -> bool:
        return bool(self.reason_for_promotion) and not bool(self.reason_for_rejection)

    @property
    def is_rejected(self) -> bool:
        return bool(self.reason_for_rejection)


# ---------------------------------------------------------------------------
# Consolidation criteria evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsolidationCriteriaResult:
    """Result of evaluating consolidation criteria for a memory candidate."""

    memory_id: str
    criteria_met: tuple[str, ...] = ()
    criteria_failed: tuple[str, ...] = ()
    overall_score: float = 0.0
    recommendation: str = 'defer'  # one of CONSOLIDATION_DECISIONS
    evidence_aggregation: EvidenceAggregation | None = None

    @property
    def criteria_fraction(self) -> float:
        """Fraction of criteria that were met."""
        total = len(self.criteria_met) + len(self.criteria_failed)
        if total <= 0:
            return 0.0
        return len(self.criteria_met) / total


# ---------------------------------------------------------------------------
# Consolidation pipeline result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsolidationPipelineResult:
    """Result of running the full consolidation pipeline."""

    processed_count: int = 0
    promoted_count: int = 0
    rejected_count: int = 0
    deferred_count: int = 0
    merged_count: int = 0
    consolidated_objects: tuple[ConsolidationObject, ...] = ()
    affected_cognitive_objects: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def success_rate(self) -> float:
        """Fraction of processed items that were promoted."""
        if self.processed_count <= 0:
            return 0.0
        return self.promoted_count / self.processed_count


# ---------------------------------------------------------------------------
# Version history helper
# ---------------------------------------------------------------------------


def make_consolidation_version(
    *,
    version_number: int,
    changed_fields: dict[str, Any],
    change_reason: str,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Create an immutable version-history entry for a consolidation object."""
    return {
        'version_number': version_number,
        'changed_fields': changed_fields,
        'change_reason': change_reason,
        'timestamp': (timestamp or datetime.now(UTC)).isoformat(),
    }
