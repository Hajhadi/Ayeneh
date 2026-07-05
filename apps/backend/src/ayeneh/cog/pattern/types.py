"""Behavioral Pattern types for the Ayeneh COG architecture (COG-11).

Defines PatternObject, BehavioralLoop, MetaPattern, and supporting structures
that model recurring cognitive and behavioral regularities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

PATTERN_TYPES: list[str] = [
    'behavioral_loop', 'cognitive_loop', 'fractal',
    'recursive', 'meta_pattern',
]

PATTERN_LIFECYCLE_STATES: list[str] = [
    'candidate', 'emerging', 'validated', 'canonical',
    'revised', 'deprecated', 'historical',
]


# ---------------------------------------------------------------------------
# PatternObject — a single detected pattern
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PatternObject:
    """A recurring cognitive or behavioral regularity detected from evidence.

    Patterns capture stable structures that repeat across time and context,
    including loops, fractals, and recursive structures.
    """

    identifier: str
    pattern_description: str
    pattern_type: str  # behavioral_loop|cognitive_loop|fractal|recursive|meta_pattern
    frequency: int = 0
    consistency: float = 0.0
    confidence: float = 0.0
    stability: float = 0.0
    influence: float = 0.0
    trigger_conditions: tuple[str, ...] = ()
    termination_conditions: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ()
    supporting_behaviors: tuple[str, ...] = ()
    supporting_decisions: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    associated_narratives: tuple[str, ...] = ()
    associated_beliefs: tuple[str, ...] = ()
    associated_values: tuple[str, ...] = ()
    associated_goals: tuple[str, ...] = ()
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


# ---------------------------------------------------------------------------
# BehavioralLoop — closed feedback loop
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BehavioralLoop:
    """Closed feedback loop: Trigger → Narrative → Belief → Emotion →
    Decision → Behavior → Outcome → Reinforcement.
    """

    loop_id: str
    trigger: str
    narrative_activation: str
    belief_activation: str
    emotion: str
    decision: str
    behavior: str
    outcome: str
    reinforcement: str
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# MetaPattern — pattern spanning multiple domains
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaPattern:
    """A pattern that spans multiple cognitive or behavioral domains."""

    pattern_id: str
    description: str
    domain_patterns: tuple[str, ...] = ()  # IDs of domain-specific patterns
    confidence: float = 0.0
    similarity_score: float = 0.0  # cross-domain similarity


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PatternResult:
    """Output of the COG-11 Behavioral Pattern Engine pipeline."""

    patterns: dict[str, PatternObject]
    loops: dict[str, BehavioralLoop]
    meta_patterns: dict[str, MetaPattern]
    total_extracted: int = 0
    lifecycle_summary: dict[str, int] = field(default_factory=dict)
