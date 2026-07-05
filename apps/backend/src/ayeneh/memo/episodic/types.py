"""Types for the episodic memory subsystem (MEM-02).

Defines EpisodeObject, MilestoneObject, LifeChapter, and all associated
enums and value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Episode enumerations
# ---------------------------------------------------------------------------

EPISODE_CATEGORIES: list[str] = [
    'research',
    'learning',
    'career',
    'relationship',
    'health',
    'travel',
    'creative',
    'spiritual_practice',
    'personal_crisis',
    'major_insight',
    'identity_transition',
]

EPISODE_STATES: list[str] = [
    'candidate',
    'active',
    'paused',
    'completed',
    'abandoned',
    'archived',
]

EPISODE_OUTCOMES: list[str] = [
    'completed_successfully',
    'partially_completed',
    'abandoned',
    'interrupted',
    'still_unknown',
]

EPISODE_RELATIONSHIPS: list[str] = [
    'continues',
    'extends',
    'caused_by',
    'enabled',
    'blocked',
    'overlaps',
    'depends_on',
    'revises',
    'inspires',
    'terminates',
]

# ---------------------------------------------------------------------------
# Episode state machine
# ---------------------------------------------------------------------------

EPISODE_STATE_TRANSITIONS: dict[str, list[str]] = {
    'candidate': ['active', 'abandoned'],
    'active': ['paused', 'completed', 'abandoned'],
    'paused': ['active', 'abandoned'],
    'completed': ['archived'],
    'abandoned': ['archived'],
    'archived': [],
}


def can_episode_transition(current: str, target: str) -> bool:
    """Return True if advancing to *target* is permitted from *current*."""
    return target in EPISODE_STATE_TRANSITIONS.get(current, [])


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MilestoneObject:
    """A significant marker within an episode."""

    milestone_id: str
    description: str
    timestamp: datetime
    evidence: tuple[str, ...] = ()
    previous_state: str = ''
    new_state: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Episode relationship
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EpisodeRelationship:
    """A typed directional link between two episodes."""

    source_episode_id: str
    target_episode_id: str
    relationship_type: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Life chapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifeChapter:
    """A high-level grouping of episodes that form a coherent life period."""

    chapter_id: str
    title: str
    beginning: datetime
    major_episodes: tuple[str, ...] = ()
    turning_points: tuple[str, ...] = ()
    developmental_themes: tuple[str, ...] = ()
    long_term_outcomes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EpisodeObject — the canonical episodic record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EpisodeObject:
    """Canonical episodic memory object.

    Every episode in the system — a research session, a conversation,
    a life event — is represented by this immutable record.
    """

    # -- identity --
    identifier: str
    title: str
    summary: str = ''

    # -- temporal --
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    estimated_duration: float | None = None  # seconds

    # -- context --
    primary_context: str = ''
    primary_project: str = ''
    primary_people: tuple[str, ...] = ()
    primary_places: tuple[str, ...] = ()

    # -- supporting material --
    supporting_conversations: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()

    # -- content highlights --
    major_decisions: tuple[str, ...] = ()
    major_behaviors: tuple[str, ...] = ()
    major_reflections: tuple[str, ...] = ()

    # -- associations --
    associated_narratives: tuple[str, ...] = ()
    associated_beliefs: tuple[str, ...] = ()
    associated_goals: tuple[str, ...] = ()
    associated_identity_components: tuple[str, ...] = ()

    # -- outcome --
    outcome: str = 'still_unknown'

    # -- meta --
    open_questions: tuple[str, ...] = ()
    confidence: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    state: str = 'candidate'
    category: str = 'learning'

    # -- relationships to other episodes --
    episode_relationships: tuple[EpisodeRelationship, ...] = ()

    # -- milestones --
    milestones: tuple[MilestoneObject, ...] = ()

    # -- explainability --
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    # -- convenience helpers --

    @property
    def is_active(self) -> bool:
        return self.state == 'active'

    @property
    def is_completed(self) -> bool:
        return self.state == 'completed'

    def can_transition_to(self, target: str) -> bool:
        return can_episode_transition(self.state, target)
