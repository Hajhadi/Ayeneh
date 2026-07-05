"""COG-04 Personal Knowledge Object types.

Defines the data structures for relatively stable, evidence-supported
knowledge about an individual extracted from conversational evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


KNOWLEDGE_CATEGORIES: list[str] = [
    'personal_identity_facts',
    'biographical',
    'projects',
    'education',
    'career',
    'skills',
    'languages',
    'interests',
    'preferences',
    'relationships',
    'possessions',
    'locations',
    'organizations',
    'health_logistics',
    'daily_routines',
    'creative_work',
    'research_topics',
    'learning_objectives',
    'tools',
    'technologies',
    'long_term_activities',
    'other',
]

KNOWLEDGE_VALIDATION_STATUSES: list[str] = [
    'pending',
    'provisional',
    'validated',
    'contradicted',
    'superseded',
]


@dataclass(frozen=True)
class PersonalKnowledgeObject:
    """A single piece of relatively stable knowledge about an individual (COG-04).

    Represents an extracted fact, preference, or biographical detail that has
    been inferred from one or more pieces of conversational evidence. Knowledge
    objects progress through a validation lifecycle as evidence accumulates.
    """

    identifier: str = ''
    knowledge_category: str = 'other'
    statement: str = ''
    confidence: float = 0.0
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    behavioral_evidence: tuple[str, ...] = ()
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    temporal_metadata: dict[str, Any] = field(default_factory=dict)
    revision_history: tuple[dict[str, Any], ...] = ()
    validation_status: str = 'pending'
    specification_version: str = '1.0.0'


@dataclass(frozen=True)
class KnowledgeExtractionResult:
    """Result of the personal knowledge extraction pipeline."""

    knowledge_objects: tuple[PersonalKnowledgeObject, ...] = ()
    total_extracted: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    processing_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class KnowledgeEdge:
    """A directed, typed relationship between two knowledge objects."""

    source_id: str = ''
    target_id: str = ''
    relationship: str = ''
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = ()
