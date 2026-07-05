"""Belief types for the Ayeneh COG architecture (COG-06).

Defines BeliefObject — an enduring cognitive proposition — and
BeliefNetwork, which captures inter-belief relationships (supports,
conflicts_with, depends_on, hierarchy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

BELIEF_CATEGORIES: list[str] = [
    'self', 'relationship', 'world', 'social', 'moral', 'competence',
    'safety', 'future', 'existential', 'learning', 'success', 'failure',
    'money', 'health', 'freedom', 'purpose', 'spiritual',
]

LIFECYCLE_STATES: list[str] = [
    'candidate', 'provisional', 'validated', 'canonical',
    'revision', 'historical',
]

BELIEF_RELATIONSHIP_TYPES: list[str] = [
    'supports', 'conflicts_with', 'depends_on', 'hierarchy',
]


# ---------------------------------------------------------------------------
# BeliefObject — enduring cognitive proposition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeliefObject:
    """An enduring belief held by the cognitive agent.

    Beliefs are distinguished from fleeting thoughts by their persistence
    across time, their resistance to revision (strength), and their
    downstream influence on attention, behaviour, and decisions.
    """

    identifier: str
    belief_statement: str
    category: str

    # Core metrics
    confidence: float = 0.0       # does the belief exist in cognition
    strength: float = 0.0         # resistance to revision
    stability: float = 0.0        # temporal persistence
    influence: float = 0.0        # effect on attention / behaviour / decisions
    identity_coupling_score: float = 0.0

    # Evidence links
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    supporting_narratives: tuple[str, ...] = ()

    # Cross-module associations
    associated_values: tuple[str, ...] = ()
    associated_goals: tuple[str, ...] = ()
    associated_identity_components: tuple[str, ...] = ()

    # Lifecycle
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


# ---------------------------------------------------------------------------
# BeliefNetwork — graph of inter-belief relationships
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeliefNetwork:
    """Directed graph of beliefs and their inter-relationships.

    *nodes* maps belief identifiers to BeliefObject instances.
    *edges* encode typed relationships (supports, conflicts_with, …).
    """

    nodes: dict[str, BeliefObject] = field(default_factory=dict)
    edges: tuple[dict[str, Any], ...] = ()
