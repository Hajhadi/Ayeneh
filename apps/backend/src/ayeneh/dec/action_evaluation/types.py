"""DEC-04 Action Evaluation — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


OUTCOME_CATEGORIES = [
    'successful',
    'partially_successful',
    'neutral',
    'unexpectedly_beneficial',
    'unexpectedly_harmful',
    'failed',
    'inconclusive',
]

COMPARISON_DIMENSIONS = [
    'magnitude',
    'timing',
    'scope',
    'reversibility',
    'side_effects',
]

EVIDENCE_TYPES = [
    'direct_observation',
    'measured_outcome',
    'testimonial',
    'comparative_data',
    'contextual_indicator',
]


@dataclass(frozen=True)
class OutcomeCategory:
    """Classifies the outcome of an executed action."""

    category: str = 'inconclusive'
    sub_category: str = ''
    confidence: float = 0.0
    reasoning: str = ''

    def __post_init__(self) -> None:
        if self.category not in OUTCOME_CATEGORIES:
            raise ValueError(
                f"Invalid outcome category: {self.category!r}. "
                f"Must be one of {OUTCOME_CATEGORIES}"
            )


@dataclass(frozen=True)
class DeviationComponent:
    """Single dimension of deviation between expected and observed outcomes."""

    dimension: str = ''
    expected_value: Any = None
    observed_value: Any = None
    magnitude: float = 0.0
    direction: str = ''  # 'positive', 'negative', 'neutral'
    explanation: str = ''


@dataclass(frozen=True)
class EvidenceItem:
    """A piece of evidence supporting an evaluation."""

    evidence_id: str = ''
    evidence_type: str = 'direct_observation'
    source: str = ''
    description: str = ''
    reliability: float = 0.5
    relevance: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(
                f"Invalid evidence type: {self.evidence_type!r}. "
                f"Must be one of {EVIDENCE_TYPES}"
            )


@dataclass(frozen=True)
class LessonLearned:
    """A lesson extracted from an action evaluation."""

    lesson_id: str = ''
    lesson_text: str = ''
    lesson_type: str = ''  # 'reliable_habit', 'recurring_mistake', 'high_performing_strategy', 'context_sensitive', 'skill_development'
    confidence: float = 0.0
    supporting_evaluations: tuple[str, ...] = ()
    applicability_conditions: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class RecommendedRevision:
    """A revision recommended based on evaluation results."""

    revision_id: str = ''
    target_plan_id: str = ''
    revision_type: str = ''  # 'modify', 'replace', 'supplement', 'abandon'
    description: str = ''
    rationale: str = ''
    priority: float = 0.5
    confidence: float = 0.5


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of an evaluation decision."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    alternative_interpretations: tuple[str, ...] = ()
    bias_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComparisonResult:
    """Result of comparing expected vs observed outcomes."""

    overall_match: float = 0.0
    dimensions: tuple[DeviationComponent, ...] = ()
    category: OutcomeCategory = field(default_factory=OutcomeCategory)
    summary: str = ''


@dataclass(frozen=True)
class ActionEvaluationResult:
    """Complete result from the ActionEvaluationEngine pipeline."""

    evaluation_id: str = ''
    evaluation_object: ActionEvaluationObject | None = None
    comparison: ComparisonResult | None = None
    lessons: tuple[LessonLearned, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()

    @property
    def has_lessons(self) -> bool:
        return len(self.lessons) > 0


@dataclass(frozen=True)
class ActionEvaluationObject:
    """Core domain object for an action evaluation."""

    evaluation_id: str = ''
    associated_action: str = ''
    associated_plan: str = ''
    associated_goal: str = ''
    expected_outcome: str = ''
    observed_outcome: str = ''
    deviation_analysis: tuple[dict[str, Any], ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    lessons_learned: tuple[str, ...] = ()
    confidence: float = 0.0
    recommended_revisions: tuple[dict[str, Any], ...] = ()
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)
