"""COG-05 Narrative Object types.

Defines the data structures for internal stories, self-narratives, and
meaning-making frameworks extracted from conversational evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


NARRATIVE_CATEGORIES: list[str] = [
    'self',
    'identity',
    'relationship',
    'social',
    'family',
    'career',
    'success',
    'failure',
    'victim',
    'growth',
    'existential',
    'future',
    'past',
    'world',
    'spiritual',
    'health',
    'learning',
    'money',
    'purpose',
]

NARRATIVE_TEMPLATES: list[str] = [
    'success',
    'failure',
    'victim',
    'rescuer',
    'growth',
    'hero',
    'perfection',
    'abandonment',
    'control',
    'meaning',
    'belonging',
    'freedom',
    'security',
    'justice',
]

NARRATIVE_VALIDATION_STATUSES: list[str] = [
    'candidate',
    'provisional',
    'validated',
    'contradicted',
    'dormant',
    'archived',
]


@dataclass(frozen=True)
class NarrativeObject:
    """An internal story or self-narrative that shapes cognition and behavior (COG-05).

    Represents a recurring pattern of meaning-making that the individual uses
    to interpret events, make decisions, and construct identity. Narratives are
    extracted from repeated evidence and tracked for drift, influence, and
    relationship to other narratives.
    """

    identifier: str = ''
    narrative_type: str = 'self'
    title: str = ''
    summary: str = ''
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    influence_score: float = 0.0
    template: str = ''
    core_assumptions: tuple[str, ...] = ()
    implicit_rules: tuple[str, ...] = ()
    expected_outcomes: tuple[str, ...] = ()
    behavioral_consequences: tuple[str, ...] = ()
    emotional_associations: tuple[str, ...] = ()
    identity_implications: tuple[str, ...] = ()
    related_narratives: tuple[str, ...] = ()
    associated_beliefs: tuple[str, ...] = ()
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    temporal_metadata: dict[str, Any] = field(default_factory=dict)
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


@dataclass(frozen=True)
class NarrativeEdge:
    """A directed, typed relationship between two narratives."""

    source_id: str = ''
    target_id: str = ''
    relationship: str = ''
    confidence: float = 0.5


@dataclass(frozen=True)
class NarrativeNetwork:
    """Graph connecting narratives with typed relationships."""

    nodes: dict[str, NarrativeObject] = field(default_factory=dict)
    edges: tuple[NarrativeEdge, ...] = ()


@dataclass(frozen=True)
class NarrativeExtractionResult:
    """Result of the narrative extraction pipeline."""

    narratives: tuple[NarrativeObject, ...] = ()
    network: NarrativeNetwork = field(default_factory=NarrativeNetwork)
    total_extracted: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    processing_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
