"""Conversation Understanding types for the Ayeneh COG architecture (COG-01).

Defines the atomic conversation primitives — segments, semantic objects,
entities, and claims — that feed the evidence extraction pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Semantic tag lists for cognitive precursor detection
# ---------------------------------------------------------------------------

NARRATIVE_PRECURSORS: list[str] = [
    'it always happens', 'every time', 'i always', 'never changes',
]

IDENTITY_PRECURSORS: list[str] = [
    'i am', 'i am the kind of', 'thats just how i am',
]

BELIEF_PRECURSORS: list[str] = [
    'i believe', 'i think that', 'i know that', 'its obvious that',
]

VALUE_PRECURSORS: list[str] = [
    'what matters is', 'the important thing', 'i value', 'i care about',
]

GOAL_PRECURSORS: list[str] = [
    'i want to', 'i need to', 'i plan to', 'my goal is',
]

META_COGNITIVE_SIGNALS: list[str] = [
    'i notice that', 'i realize', 'i am aware that', 'i see that',
]


# ---------------------------------------------------------------------------
# ConversationSegment — smallest processing unit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConversationSegment:
    """An atomic unit of a conversation (one speaker utterance)."""

    segment_id: str
    conversation_id: str
    speaker: str
    text: str
    timestamp: datetime
    sequence_number: int
    language: str = 'en'


# ---------------------------------------------------------------------------
# SemanticObject — output of linguistic analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SemanticObject:
    """A normalised linguistic object extracted from a segment."""

    object_id: str
    surface_form: str
    normalized_form: str
    object_type: str  # entity|event|claim|action|temporal_ref|location|person
    confidence: float = 0.0
    offsets: tuple[int, int] = (0, 0)


# ---------------------------------------------------------------------------
# Entity — named entity with resolution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Entity:
    """A resolved named entity with alias support."""

    entity_id: str
    name: str
    entity_type: str  # person|organization|project|place|concept|event
    aliases: tuple[str, ...] = ()
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Claim — proposition with epistemic markers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Claim:
    """A factual or attitudinal claim extracted from conversation."""

    claim_id: str
    text: str
    speaker: str
    timestamp: datetime
    epistemic_marker: str = 'observation'
    confidence: float = 0.5
    is_self_report: bool = False
    negated: bool = False
    uncertainty_markers: tuple[str, ...] = ()
