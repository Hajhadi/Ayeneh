"""Foundation types for the Ayeneh MEMO memory architecture.

This module defines the canonical MemoryObject, lifecycle state machine,
consolidation levels, relationship types, and base enumerations that all
MEM-01 through MEM-10 modules depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Lifecycle state machine
# ---------------------------------------------------------------------------

MEMORY_LIFECYCLE: list[str] = [
    'conversation',
    'candidate_memory',
    'validated_memory',
    'consolidated_memory',
    'longitudinal_memory',
    'historical_memory',
]

MEMORY_LIFECYCLE_TRANSITIONS: dict[str, list[str]] = {
    'conversation': ['candidate_memory'],
    'candidate_memory': ['validated_memory', 'conversation'],
    'validated_memory': ['consolidated_memory', 'candidate_memory'],
    'consolidated_memory': ['longitudinal_memory', 'validated_memory'],
    'longitudinal_memory': ['historical_memory', 'consolidated_memory'],
    'historical_memory': [],
}


def can_memory_transition(current: str, target: str) -> bool:
    """Return True if *target* is a legal next lifecycle state from *current*."""
    allowed = MEMORY_LIFECYCLE_TRANSITIONS.get(current, [])
    return target in allowed


# ---------------------------------------------------------------------------
# Consolidation levels
# ---------------------------------------------------------------------------

CONSOLIDATION_LEVELS: list[str] = [
    'level_0_ephemeral',
    'level_1_candidate',
    'level_2_probable',
    'level_3_stable',
    'level_4_core',
]

CONSOLIDATION_LEVEL_VALUES: dict[str, int] = {
    'level_0_ephemeral': 0,
    'level_1_candidate': 1,
    'level_2_probable': 2,
    'level_3_stable': 3,
    'level_4_core': 4,
}

# ---------------------------------------------------------------------------
# Memory types
# ---------------------------------------------------------------------------

MEMORY_TYPES: list[str] = [
    'episodic',
    'semantic_personal',
    'working',
    'consolidation',
    'evidence',
    'relationship',
    'meta_cognitive',
]

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------

RELATIONSHIP_TYPES: list[str] = [
    'supports',
    'contradicts',
    'caused_by',
    'derived_from',
    'strengthens',
    'weakens',
    'explains',
    'predicts',
    'follows',
    'precedes',
]

# ---------------------------------------------------------------------------
# Temporal scope values
# ---------------------------------------------------------------------------

TEMPORAL_SCOPES: list[str] = [
    'momentary',
    'short_term',
    'medium_term',
    'long_term',
    'historical',
    'recurring',
]

# ---------------------------------------------------------------------------
# Evidence ref (lightweight, no cog.base import)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRef:
    """Lightweight reference to an evidence object."""

    evidence_id: str
    evidence_type: str
    confidence: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Canonical Memory Object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryObject:
    """Canonical memory object shared across all MEM modules.

    Every memory — episodic, semantic, working, consolidation, evidence,
    relationship, meta-cognitive — is represented by this immutable record.
    """

    identifier: str
    memory_type: str
    creation_time: datetime
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    supporting_evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    importance_score: float = 0.0
    temporal_scope: str = 'momentary'
    associated_cognitive_objects: tuple[str, ...] = ()
    associated_episodes: tuple[str, ...] = ()
    associated_projects: tuple[str, ...] = ()
    associated_people: tuple[str, ...] = ()
    associated_places: tuple[str, ...] = ()
    associated_conversations: tuple[str, ...] = ()
    version_history: tuple[dict[str, Any], ...] = ()
    lifecycle_status: str = 'candidate_memory'
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    # -- convenience helpers -------------------------------------------------

    def is_canonical(self) -> bool:
        """Return True when the memory has reached longitudinal status."""
        return self.lifecycle_status == 'longitudinal_memory'

    def can_transition_to(self, target: str) -> bool:
        """Return True if advancing to *target* is permitted."""
        return can_memory_transition(self.lifecycle_status, target)


# ---------------------------------------------------------------------------
# Version record helper
# ---------------------------------------------------------------------------


def make_version_record(
    *,
    version_number: int,
    changed_fields: dict[str, Any],
    change_reason: str,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Create an immutable version-history entry."""
    return {
        'version_number': version_number,
        'changed_fields': changed_fields,
        'change_reason': change_reason,
        'timestamp': (timestamp or datetime.now(UTC)).isoformat(),
    }
