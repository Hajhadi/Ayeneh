"""Types for the semantic personal memory subsystem (MEM-03).

Defines SemanticMemoryObject and all associated enumerations for stable
personal knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Knowledge categories
# ---------------------------------------------------------------------------

KNOWLEDGE_CATEGORIES: list[str] = [
    'personal_interests',
    'skills',
    'expertise',
    'learning_preferences',
    'communication_style',
    'decision_style',
    'behavioral_tendencies',
    'recurring_projects',
    'long_term_goals',
    'core_values',
    'stable_beliefs',
    'identity_themes',
    'preferred_tools',
    'languages',
    'relationships',
    'health_practices',
    'research_domains',
]

# ---------------------------------------------------------------------------
# Temporal stability
# ---------------------------------------------------------------------------

TEMPORAL_STABILITY_LEVELS: list[str] = [
    'momentary',
    'short_term',
    'medium_term',
    'long_term',
    'permanent',
]

# ---------------------------------------------------------------------------
# Version record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticVersionRecord:
    """A version-history entry for semantic knowledge."""

    version_number: int
    changed_fields: dict[str, Any]
    change_reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# SemanticMemoryObject — the canonical semantic record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticMemoryObject:
    """Canonical semantic personal memory object.

    Represents stable knowledge about the person: their interests, skills,
    values, behavioral patterns, and other long-lived knowledge.
    """

    # -- identity --
    identifier: str
    knowledge_statement: str
    knowledge_category: str = 'personal_interests'

    # -- evidence & support --
    supporting_evidence: tuple[str, ...] = ()
    supporting_episodes: tuple[str, ...] = ()
    supporting_conversations: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()

    # -- confidence & importance --
    confidence: float = 0.0
    importance: float = 0.0

    # -- temporal --
    temporal_stability: str = 'long_term'
    creation_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_confirmation: datetime = field(default_factory=lambda: datetime.now(UTC))

    # -- evolution --
    revision_history: tuple[SemanticVersionRecord, ...] = ()

    # -- associations --
    associated_cognitive_objects: tuple[str, ...] = ()

    # -- explainability --
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    # -- convenience helpers --

    @property
    def is_stable(self) -> bool:
        """Return True if the knowledge has reached stable confidence."""
        return self.confidence >= 0.7 and self.temporal_stability in ('long_term', 'permanent')

    @property
    def age_days(self) -> float:
        """Return the age of this knowledge in days."""
        return (datetime.now(UTC) - self.creation_time).total_seconds() / 86400.0

    @property
    def recency_days(self) -> float:
        """Return days since last confirmation."""
        return (datetime.now(UTC) - self.last_confirmation).total_seconds() / 86400.0


# ---------------------------------------------------------------------------
# Knowledge graph node
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeNode:
    """A node in the personal knowledge graph."""

    node_id: str
    label: str
    category: str
    semantic_memory_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge graph edge
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeEdge:
    """An edge in the personal knowledge graph."""

    source_node_id: str
    target_node_id: str
    edge_type: str  # 'related_to', 'depends_on', 'contradicts', 'derives_from'
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
