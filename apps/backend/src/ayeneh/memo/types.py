"""Shared types for all MEM memory modules.

Provides lightweight value objects used across episodic, semantic,
working-memory, and other MEM subsystems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Temporal types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimeRange:
    """A bounded interval in time."""

    start: datetime
    end: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.end is None:
            return None
        return (self.end - self.start).total_seconds()

    @property
    def is_closed(self) -> bool:
        return self.end is not None


# ---------------------------------------------------------------------------
# Evidence & provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRecord:
    """A single piece of supporting evidence."""

    evidence_id: str
    evidence_type: str
    source: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProvenanceRecord:
    """Tracks how a memory was derived."""

    source_ids: tuple[str, ...] = ()
    derivation_method: str = ''
    derivation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    agent: str = ''


# ---------------------------------------------------------------------------
# Association types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Association:
    """A typed link between two memory objects."""

    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    bidirectional: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssociationGroup:
    """A cluster of related associations."""

    group_id: str
    label: str
    association_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Confidence & importance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfidenceRecord:
    """Tracks how confidence in a memory has evolved."""

    initial_confidence: float = 0.0
    current_confidence: float = 0.0
    confidence_history: tuple[dict[str, Any], ...] = ()
    confidence_source: str = ''

    @property
    def confidence_delta(self) -> float:
        return self.current_confidence - self.initial_confidence


@dataclass(frozen=True)
class ImportanceRecord:
    """Tracks importance scoring over time."""

    initial_importance: float = 0.0
    current_importance: float = 0.0
    importance_history: tuple[dict[str, Any], ...] = ()
    importance_source: str = ''


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExplainabilityRecord:
    """Metadata explaining why a memory exists or was promoted."""

    reason: str = ''
    contributing_factors: tuple[str, ...] = ()
    explanation_text: str = ''
    confidence_justification: str = ''


# ---------------------------------------------------------------------------
# Version tracking
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionRecord:
    """An immutable version-history entry."""

    version_number: int
    changed_fields: dict[str, Any]
    change_reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Observer / tracker types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    """A raw observation from the environment or conversation."""

    observation_id: str
    content: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    observation_type: str = 'conversation_turn'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    """A discrete event extracted from observations."""

    event_id: str
    description: str
    timestamp: datetime
    event_type: str = 'behavior'
    confidence: float = 1.0
    source_observations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
