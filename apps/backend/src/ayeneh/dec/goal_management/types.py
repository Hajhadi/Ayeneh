"""DEC-02 Goal Management types.

Defines GoalObject, GoalHierarchy, GoalConflict, GoalResult, and supporting
value objects for the goal management pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

GOAL_CATEGORIES: list[str] = [
    'survival',
    'health',
    'learning',
    'relationship',
    'career',
    'financial',
    'creative',
    'research',
    'spiritual',
    'meta_cognitive',
]

GOAL_LIFECYCLE: list[str] = [
    'proposed',
    'accepted',
    'planned',
    'active',
    'paused',
    'completed',
    'abandoned',
    'archived',
]

GOAL_HIERARCHY_LEVELS: list[str] = [
    'life_purpose',
    'domain_goal',
    'project_goal',
    'milestone',
    'task',
    'action',
]

GOAL_PRIORITY_LEVELS: list[str] = [
    'critical',
    'high',
    'medium',
    'low',
    'aspirational',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalDependency:
    """A dependency between two goals."""

    dependency_id: str
    source_goal: str = ''
    target_goal: str = ''
    dependency_type: str = 'supports'
    strength: float = 0.5


@dataclass(frozen=True)
class GoalConflict:
    """A detected conflict between goals."""

    conflict_id: str
    goal_a: str = ''
    goal_b: str = ''
    conflict_type: str = ''
    severity: float = 0.0
    resolution_suggestions: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoalProgressUpdate:
    """A progress update for a goal."""

    update_id: str
    goal_id: str = ''
    previous_progress: float = 0.0
    new_progress: float = 0.0
    evidence: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalObject:
    """A single goal managed by the goal management engine (DEC-02)."""

    goal_id: str
    description: str = ''
    category: str = ''
    parent_goal: str = ''
    child_goals: tuple[str, ...] = ()
    priority: float = 0.0
    current_status: str = 'proposed'
    supporting_evidence: tuple[str, ...] = ()
    motivational_sources: tuple[str, ...] = ()
    associated_values: tuple[str, ...] = ()
    associated_projects: tuple[str, ...] = ()
    progress: float = 0.0
    confidence: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoalHierarchy:
    """Reconstructed hierarchy of goals."""

    root_goals: tuple[str, ...] = ()
    parent_map: dict[str, str] = field(default_factory=dict)
    children_map: dict[str, tuple[str, ...]] = field(default_factory=dict)
    level_map: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GoalResult:
    """Complete result of the goal management pipeline."""

    goals: tuple[GoalObject, ...] = ()
    hierarchy: GoalHierarchy = field(default_factory=GoalHierarchy)
    conflicts: tuple[GoalConflict, ...] = ()
    priority_ranking: tuple[str, ...] = ()
    revision_suggestions: tuple[str, ...] = ()
    planning_interface: dict[str, Any] = field(default_factory=dict)
    processing_metadata: dict[str, Any] = field(default_factory=dict)
