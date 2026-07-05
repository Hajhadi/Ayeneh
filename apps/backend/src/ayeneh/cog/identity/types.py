"""Identity Graph types for the Ayeneh COG architecture (COG-09).

Defines IdentityComponent, ObserverSelf, and IdentityGraph — the core
data structures that model a person's evolving cognitive self-understanding
and the meta-cognitive capacity to observe thoughts without identifying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

IDENTITY_LIFECYCLE_STATES: list[str] = [
    'candidate', 'emerging', 'validated', 'canonical',
    'revised', 'deprecated', 'historical',
]

IDENTITY_COMPONENT_TYPES: list[str] = [
    'role', 'trait', 'value_alignment', 'skill', 'relationship',
    'narrative_thread', 'belief_anchor', 'emotional_pattern',
    'goal_derived', 'memory_rooted',
]

LIFECYCLE_STATES: list[str] = [
    'candidate', 'emerging', 'validated', 'canonical',
    'revised', 'deprecated', 'historical',
]


# ---------------------------------------------------------------------------
# IdentityComponent — a single unit of self-understanding
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdentityComponent:
    """A single element of the evolving identity graph.

    Each component represents a piece of self-understanding that has been
    detected from evidence and may be linked to beliefs, values, goals,
    and narratives.
    """

    identifier: str
    identity_statement: str
    confidence: float = 0.0
    stability: float = 0.0
    centrality: float = 0.0  # influence on decisions/goals/narratives
    influence: float = 0.0
    observer_strength: float = 0.0  # meta-cognitive observing capacity
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    supporting_beliefs: tuple[str, ...] = ()
    supporting_values: tuple[str, ...] = ()
    supporting_goals: tuple[str, ...] = ()
    supporting_narratives: tuple[str, ...] = ()
    narrative_identification_score: float = 0.0  # fusion between narrative and identity
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


# ---------------------------------------------------------------------------
# ObserverSelf — meta-cognitive observing capacity
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObserverSelf:
    """Architectural construct — capacity to observe thoughts without identifying.

    Tracks the strength and stability of the observer perspective, which
    enables de-identification from automatic cognitive content.
    """

    confidence: float = 0.0
    stability: float = 0.0
    observation_episodes: int = 0
    average_episode_duration_s: float = 0.0
    de_identification_level: float = 0.0  # 0.0 = fully identified, 1.0 = fully observed


# ---------------------------------------------------------------------------
# IdentityGraph — the full graph of identity components
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdentityGraph:
    """Complete graph representing the evolving identity structure.

    Components are keyed by identifier. Edges represent relationships
    between components (support, contradiction, influence, etc.).
    """

    components: dict[str, IdentityComponent] = field(default_factory=dict)
    edges: tuple[dict[str, Any], ...] = ()
    observer_self: ObserverSelf = field(default_factory=ObserverSelf)
    coherence_score: float = 0.0  # structural consistency across cognitive subsystems


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdentityResult:
    """Output of the COG-09 Identity Graph Engine pipeline."""

    components: dict[str, IdentityComponent]
    graph: IdentityGraph
    observer_self: ObserverSelf
    coherence_score: float
    total_components: int = 0
    lifecycle_summary: dict[str, int] = field(default_factory=dict)
