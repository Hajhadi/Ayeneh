"""Meta-Cognition types for the Ayeneh COG architecture (COG-16).

Defines MetaCognitiveObject, AwarenessEvent, ObserverEpisode, and
CognitiveTransparency — the core data structures for modelling a
person's relationship with their own thinking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

AWARENESS_LEVELS: dict[int, str] = {
    0: 'no_observable_awareness',
    1: 'awareness_after_event',
    2: 'awareness_during_event',
    3: 'awareness_before_automatic_activation',
    4: 'stable_observation_without_identification',
    5: 'longitudinal_integration_across_contexts',
}

META_COGNITIVE_LIFECYCLE_STATES: list[str] = [
    'candidate', 'provisional', 'validated', 'canonical',
    'revision', 'historical',
]


# ---------------------------------------------------------------------------
# MetaCognitiveObject — awareness of a cognitive process
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaCognitiveObject:
    """An object representing awareness of a specific cognitive process.

    Captures what the person recognises about their own thinking, the level
    of awareness, and supporting evidence across conversations.
    """

    identifier: str
    observed_cognitive_process: str
    awareness_description: str
    awareness_level: int = 0
    confidence: float = 0.0
    stability: float = 0.0
    context: str = ''
    supporting_evidence: tuple[str, ...] = ()
    supporting_conversations: tuple[str, ...] = ()
    observed_behavioral_effects: tuple[str, ...] = ()
    associated_reflections: tuple[str, ...] = ()
    associated_narratives: tuple[str, ...] = ()
    associated_beliefs: tuple[str, ...] = ()
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


# ---------------------------------------------------------------------------
# AwarenessEvent — a discrete moment of recognising cognition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AwarenessEvent:
    """A single event where a cognitive process was recognised."""

    event_id: str
    recognized_process: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    awareness_level: int = 1
    evidence: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# ObserverEpisode — a sustained period of meta-cognitive observation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObserverEpisode:
    """A sustained episode of observing one's own cognitive processes."""

    episode_id: str
    duration_s: float = 0.0
    context: str = ''
    observed_processes: tuple[str, ...] = ()
    behavioral_consequences: tuple[str, ...] = ()
    associated_reflections: tuple[str, ...] = ()
    recovery_following_loss: bool = False


# ---------------------------------------------------------------------------
# CognitiveTransparency — observability of the internal cognitive system
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveTransparency:
    """Estimates how observable the internal cognitive system is.

    Higher transparency means the person has clearer access to their own
    cognitive processes, enabling better self-regulation and decision-making.
    """

    narrative_visibility: float = 0.0
    belief_visibility: float = 0.0
    identity_visibility: float = 0.0
    behavioral_visibility: float = 0.0
    decision_visibility: float = 0.0
    prediction_visibility: float = 0.0
    reflection_quality: float = 0.0
    overall_transparency: float = 0.0
