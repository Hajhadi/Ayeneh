"""DLG-04 Reflection Timing types.

Defines ReflectionOpportunity, ReflectionTriggers, ReflectionCategories,
and ReflectionIntensity for the reflection timing pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

REFLECTION_TRIGGERS: list[str] = [
    'recurring_behavioral_pattern',
    'repeated_narrative',
    'identity_contradiction',
    'goal_inconsistency',
    'reality_distortion',
    'repeated_cognitive_loop',
    'major_developmental_transition',
    'unexpected_insight',
    'project_phase_completion',
]

REFLECTION_CATEGORIES: list[str] = [
    'behavioral',
    'narrative',
    'identity',
    'reality_calibration',
    'goal',
    'decision',
    'relationship',
    'meta_cognitive',
    'project',
]

REFLECTION_INTENSITY_LEVELS: list[str] = [
    'gentle',
    'exploratory',
    'pattern_proposal',
    'deep_cognitive_intervention',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OpportunityIdentifier:
    """Unique identifier for a reflection opportunity."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class DetectedPattern:
    """A pattern detected by the reflection trigger detector."""

    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ''
    description: str = ''
    frequency: int = 0
    strength: float = 0.0
    evidence_count: int = 0
    first_detected: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_detected: datetime = field(default_factory=lambda: datetime.now(UTC))
    related_episodes: tuple[str, ...] = ()
    related_behaviors: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReflectionEvidence:
    """Evidence supporting a reflection opportunity."""

    evidence_id: str = ''
    evidence_type: str = ''
    description: str = ''
    strength: float = 0.0
    source: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AlternativeTimingOption:
    """An alternative timing for delivering a reflection."""

    timing_id: str = ''
    description: str = ''
    estimated_benefit: float = 0.0
    estimated_risk: float = 0.0
    delay_turns: int = 0
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class EstimatedReadiness:
    """Assessment of user readiness for reflection."""

    cognitive_load: float = 0.0
    emotional_stability: float = 0.5
    openness_score: float = 0.5
    defensiveness_level: float = 0.0
    overall_readiness: float = 0.5


@dataclass(frozen=True)
class EstimatedBenefit:
    """Assessment of potential benefit from reflection."""

    self_awareness_gain: float = 0.0
    behavior_change_potential: float = 0.0
    narrative_coherence_gain: float = 0.0
    identity_clarity_gain: float = 0.0
    overall_benefit: float = 0.0


@dataclass(frozen=True)
class EstimatedRisk:
    """Assessment of potential risk from reflection."""

    emotional_disruption: float = 0.0
    defensiveness_trigger: float = 0.0
    trust_damage: float = 0.0
    overwhelm_risk: float = 0.0
    overall_risk: float = 0.0


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReflectionOpportunity:
    """A detected opportunity for reflection (DLG-04)."""

    opportunity_identifier: OpportunityIdentifier = field(
        default_factory=OpportunityIdentifier,
    )
    conversation_identifier: str = ''
    detected_pattern: DetectedPattern = field(default_factory=DetectedPattern)
    relevant_episodes: tuple[str, ...] = ()
    relevant_evidence: tuple[ReflectionEvidence, ...] = ()
    suggested_reflection: str = ''
    reflection_category: str = 'behavioral'
    estimated_readiness: EstimatedReadiness = field(default_factory=EstimatedReadiness)
    estimated_benefit: EstimatedBenefit = field(default_factory=EstimatedBenefit)
    estimated_risk: EstimatedRisk = field(default_factory=EstimatedRisk)
    urgency: float = 0.0
    confidence: float = 0.0
    alternative_timing_options: tuple[AlternativeTimingOption, ...] = ()
    version_metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trigger type mapping
# ---------------------------------------------------------------------------

TRIGGER_TO_CATEGORY: dict[str, str] = {
    'recurring_behavioral_pattern': 'behavioral',
    'repeated_narrative': 'narrative',
    'identity_contradiction': 'identity',
    'goal_inconsistency': 'goal',
    'reality_distortion': 'reality_calibration',
    'repeated_cognitive_loop': 'meta_cognitive',
    'major_developmental_transition': 'identity',
    'unexpected_insight': 'meta_cognitive',
    'project_phase_completion': 'project',
}


# ---------------------------------------------------------------------------
# Reflection Intensity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReflectionIntensity:
    """Intensity level for a reflection intervention."""

    level: int = 1  # 1=Gentle, 2=Exploratory, 3=PatternProposal, 4=DeepCognitiveIntervention
    label: str = 'gentle'
    max_depth: int = 1
    follow_up_required: bool = False

    @classmethod
    def gentle(cls) -> ReflectionIntensity:
        return cls(level=1, label='gentle', max_depth=1, follow_up_required=False)

    @classmethod
    def exploratory(cls) -> ReflectionIntensity:
        return cls(level=2, label='exploratory', max_depth=2, follow_up_required=True)

    @classmethod
    def pattern_proposal(cls) -> ReflectionIntensity:
        return cls(
            level=3, label='pattern_proposal', max_depth=3, follow_up_required=True,
        )

    @classmethod
    def deep_cognitive_intervention(cls) -> ReflectionIntensity:
        return cls(
            level=4,
            label='deep_cognitive_intervention',
            max_depth=4,
            follow_up_required=True,
        )
