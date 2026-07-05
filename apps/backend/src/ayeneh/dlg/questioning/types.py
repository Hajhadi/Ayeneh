"""DLG-05 Question Generation types.

Defines QuestionObject, QuestionObjectives, and QuestionCategories
for the Socratic questioning pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

QUESTION_OBJECTIVES: list[str] = [
    'clarify_ambiguity',
    'collect_evidence',
    'differentiate_observation_from_interpretation',
    'explore_behavioral_patterns',
    'reveal_hidden_assumptions',
    'challenge_narratives',
    'understand_identity',
    'support_planning',
    'resolve_contradictions',
    'generate_hypotheses',
    'expand_reflection',
]

QUESTION_CATEGORIES: list[str] = [
    'clarification',
    'evidence',
    'reflection',
    'behavior',
    'narrative',
    'identity',
    'reality_calibration',
    'planning',
    'prediction',
    'meta_cognitive',
]

SOCRATIC_STEPS: list[str] = [
    'observation',
    'evidence',
    'interpretation',
    'alternative_interpretation',
    'underlying_assumption',
    'broader_pattern',
    'identity_relationship',
    'reality_calibration',
    'meta_cognitive_reflection',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestionIdentifier:
    """Unique identifier for a question."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class QuestionType:
    """Classification of question type."""

    primary_type: str = 'open_ended'
    secondary_types: tuple[str, ...] = ()
    socratic_step: str = ''
    complexity: int = 1


@dataclass(frozen=True)
class PrimaryObjective:
    """Primary objective for asking this question."""

    objective: str = ''
    rationale: str = ''
    expected_outcome: str = ''
    priority: float = 0.5


@dataclass(frozen=True)
class AssociatedCognitiveObjects:
    """Cognitive objects associated with this question."""

    belief_ids: tuple[str, ...] = ()
    narrative_ids: tuple[str, ...] = ()
    goal_ids: tuple[str, ...] = ()
    identity_component_ids: tuple[str, ...] = ()
    behavioral_pattern_ids: tuple[str, ...] = ()
    prediction_ids: tuple[str, ...] = ()
    reality_object_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelevantEvidence:
    """Evidence referenced or relevant to this question."""

    evidence_ids: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    evidence_strengths: tuple[float, ...] = ()
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetUncertainty:
    """The uncertainty this question aims to address."""

    uncertainty_id: str = ''
    uncertainty_type: str = ''
    description: str = ''
    current_confidence: float = 0.0
    target_confidence: float = 0.0


@dataclass(frozen=True)
class ExpectedInformationGain:
    """Expected information gain from the answer."""

    clarity_gain: float = 0.0
    evidence_gain: float = 0.0
    insight_gain: float = 0.0
    relationship_gain: float = 0.0
    overall_gain: float = 0.0


@dataclass(frozen=True)
class VersionMetadata:
    """Version tracking for the question object."""

    schema_version: str = '1.0.0'
    engine_version: str = '1.0.0'
    build_number: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestionObject:
    """A generated question for Socratic dialogue (DLG-05)."""

    question_identifier: QuestionIdentifier = field(default_factory=QuestionIdentifier)
    conversation_identifier: str = ''
    question_text: str = ''
    question_type: QuestionType = field(default_factory=QuestionType)
    primary_objective: PrimaryObjective = field(default_factory=PrimaryObjective)
    associated_cognitive_objects: AssociatedCognitiveObjects = field(
        default_factory=AssociatedCognitiveObjects,
    )
    relevant_evidence: RelevantEvidence = field(default_factory=RelevantEvidence)
    target_uncertainty: TargetUncertainty = field(default_factory=TargetUncertainty)
    expected_information_gain: ExpectedInformationGain = field(
        default_factory=ExpectedInformationGain,
    )
    estimated_cognitive_load: float = 0.3
    estimated_reflection_value: float = 0.5
    confidence: float = 0.5
    alternative_questions: tuple[str, ...] = ()
    follow_up_strategy: str = ''
    version_metadata: VersionMetadata = field(default_factory=VersionMetadata)
