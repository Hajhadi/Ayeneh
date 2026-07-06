"""ACT-02 Habit Formation types.

Defines HabitObject and supporting value objects for the
habit formation engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

HABIT_LIFECYCLE: list[str] = [
    'proposed',
    'initiated',
    'developing',
    'strengthening',
    'stable',
    'weakening',
    'dormant',
    'retired',
]

CUE_CATEGORIES: list[str] = [
    'Time',
    'Location',
    'PreviousActivity',
    'SocialEnvironment',
    'EmotionalState',
    'EnvironmentalSignal',
]

REINFORCEMENT_TYPES: list[str] = [
    'positive_outcome',
    'negative_outcome',
    'neutral_outcome',
    'anticipated_reward',
    'social_recognition',
    'intrinsic_satisfaction',
]

COMPETITION_RESOLUTION_STRATEGIES: list[str] = [
    'prioritize_stronger',
    'time_separation',
    'cue_discrimination',
    'merge_behaviors',
    'retire_weaker',
]

HABIT_LIFECYCLE_TRANSITIONS: dict[str, list[str]] = {
    'proposed': ['initiated', 'retired'],
    'initiated': ['developing', 'retired'],
    'developing': ['strengthening', 'weakening', 'retired'],
    'strengthening': ['stable', 'weakening'],
    'stable': ['weakening', 'retired'],
    'weakening': ['dormant', 'stable', 'retired'],
    'dormant': ['initiated', 'retired'],
    'retired': [],
}


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CueInstance:
    """A specific cue triggering a habit behavior."""

    cue_id: str
    cue_category: str = 'Time'
    cue_description: str = ''
    cue_strength: float = 0.0
    frequency: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReinforcementRecord:
    """A reinforcement event for a habit."""

    reinforcement_id: str
    reinforcement_type: str = 'positive_outcome'
    intensity: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    description: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitCompetition:
    """Represents competition between two habits."""

    competition_id: str
    habit_a: str = ''
    habit_b: str = ''
    competition_type: str = 'competing'
    resolution_strategy: str = 'prioritize_stronger'
    resolution_outcome: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitStrengthSnapshot:
    """Point-in-time measurement of habit strength."""

    snapshot_id: str
    strength_value: float = 0.0
    consistency_score: float = 0.0
    context_stability: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitEcologyRelation:
    """Relationship between two habits in the ecology."""

    relation_id: str
    habit_a: str = ''
    habit_b: str = ''
    relation_type: str = 'neutral'
    strength: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitPublication:
    """Published result of habit formation for downstream consumption."""

    publication_id: str
    habit_id: str = ''
    habit_status: str = 'proposed'
    strength: float = 0.0
    recommendation: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitObject:
    """Core habit entity tracked by ACT-02."""

    habit_id: str
    associated_goal: str = ''
    associated_behavior: str = ''
    primary_cue: str = ''
    secondary_cues: tuple[str, ...] = ()
    expected_reward: str = ''
    observed_reinforcement: float = 0.0
    habit_strength: float = 0.0
    context_stability: float = 0.0
    behavioral_consistency: float = 0.0
    current_status: str = 'proposed'
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HabitResult:
    """Output produced by the habit formation pipeline."""

    habit: HabitObject
    lifecycle_transition: str = ''
    cue_instances: tuple[CueInstance, ...] = ()
    reinforcement_records: tuple[ReinforcementRecord, ...] = ()
    competitions: tuple[HabitCompetition, ...] = ()
    strength_snapshots: tuple[HabitStrengthSnapshot, ...] = ()
    publications: tuple[HabitPublication, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
