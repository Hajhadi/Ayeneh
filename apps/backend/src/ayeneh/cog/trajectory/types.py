"""Cognitive Trajectory types for the Ayeneh COG architecture (COG-13).

Defines TrajectoryObject, DevelopmentalMilestone, Transformation, and
supporting structures that model how cognitive structures evolve over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

TARGET_TYPES: list[str] = [
    'belief', 'value', 'goal', 'identity', 'narrative', 'pattern',
    'project', 'learning_domain', 'meta_cognitive', 'relationship',
]

DIRECTION_TYPES: list[str] = [
    'strengthening', 'weakening', 'stabilizing',
    'fragmenting', 'integrating', 'transforming',
    'emerging', 'disappearing',
]

TRAJECTORY_LIFECYCLE_STATES: list[str] = [
    'candidate', 'emerging', 'validated', 'canonical', 'historical',
]


class ObservationWindow(str, Enum):
    CONVERSATION = 'conversation'
    WEEK = 'week'
    MONTH = 'month'
    PROJECT = 'project'
    LIFE_CHAPTER = 'life_chapter'
    ENTIRE_HISTORY = 'entire_interaction_history'


# ---------------------------------------------------------------------------
# TrajectoryObject — tracks evolution of a cognitive structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrajectoryObject:
    """Tracks how a specific cognitive structure evolves across time.

    Captures version history, transitions, rate of change, and direction
    to model the developmental trajectory of beliefs, values, goals,
    identities, narratives, and patterns.
    """

    identifier: str
    target_cognitive_object: str  # ID of what's being tracked
    target_type: str  # belief|value|goal|identity|narrative|pattern
    temporal_sequence: tuple[dict[str, Any], ...] = ()  # version snapshots over time
    major_transitions: tuple[dict[str, Any], ...] = ()
    rate_of_change: float = 0.0
    direction: str = ''  # strengthening|weakening|stabilizing|fragmenting|integrating|transforming
    confidence: float = 0.0
    historical_continuity: float = 0.0
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    specification_version: str = '1.0.0'
    observation_window: str = 'conversation'
    stability: float = 0.0
    associated_reflections: tuple[str, ...] = ()
    predicted_future_direction: str = ''


# ---------------------------------------------------------------------------
# DevelopmentalMilestone — significant transition point
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DevelopmentalMilestone:
    """A significant transition point in cognitive development.

    Marks moments where a cognitive structure underwent qualitative change,
    such as a belief revision, identity shift, or value reorganization.
    """

    milestone_id: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    evidence: tuple[str, ...] = ()
    previous_state: str = ''
    new_state: str = ''


# ---------------------------------------------------------------------------
# Transformation — structural reorganization
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Transformation:
    """A structural reorganization of cognitive structures.

    Unlike minor revisions, transformations represent fundamental shifts
    in how cognitive elements are organized or related.
    """

    transformation_id: str
    description: str
    previous_organization: str = ''
    new_organization: str = ''
    intermediate_states: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrajectoryResult:
    """Output of the COG-13 Cognitive Trajectory Engine pipeline."""

    trajectories: dict[str, TrajectoryObject]
    milestones: list[DevelopmentalMilestone]
    phases: list[dict[str, Any]]
    total_extracted: int = 0
