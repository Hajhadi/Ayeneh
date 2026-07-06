"""ACT-03 Adaptive Intervention types.

Defines InterventionObject and supporting value objects for the
adaptive intervention engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

INTERVENTION_CATEGORIES: list[str] = [
    'Reminder',
    'Clarification',
    'ReflectionPrompt',
    'PlanningSuggestion',
    'RiskWarning',
    'MotivationalSupport',
    'EvidenceRequest',
    'RecoverySuggestion',
    'StrategyRevision',
    'CelebrationOfProgress',
]

INTENSITY_LEVELS: list[str] = [
    'SilentObservation',
    'PassiveLogging',
    'GentleReminder',
    'ReflectiveQuestion',
    'StructuredRecommendation',
    'ComprehensivePlanningDialogue',
]

TIMING_ASSESSMENTS: list[str] = [
    'optimal',
    'acceptable',
    'suboptimal',
    'premature',
    'too_late',
    'interrupting',
]

OUTCOME_EVALUATIONS: list[str] = [
    'effective',
    'partially_effective',
    'ineffective',
    'counterproductive',
    'pending_evaluation',
    'not_applicable',
]

DIALOGUE_STRATEGIES: list[str] = [
    'direct_suggestion',
    'socratic_questioning',
    'reflective_guidance',
    'collaborative_planning',
    'gentle_nudge',
    'celebratory_acknowledgment',
    'risk_escalation',
    'strategy_pivot',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimingAssessment:
    """Evaluation of intervention timing quality."""

    assessment_id: str
    cognitive_load: float = 0.0
    task_phase: str = ''
    emotional_intensity: float = 0.0
    goal_urgency: float = 0.0
    progress_level: float = 0.0
    environment_fitness: float = 0.0
    overall_timing: str = 'acceptable'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OpportunitySignal:
    """A detected opportunity for intervention."""

    signal_id: str
    signal_type: str = ''
    description: str = ''
    strength: float = 0.0
    urgency: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskSignal:
    """A detected risk that may warrant intervention."""

    signal_id: str
    risk_type: str = ''
    description: str = ''
    severity: float = 0.0
    probability: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterventionEvaluation:
    """Evaluation of an intervention's cost-benefit profile."""

    evaluation_id: str
    expected_benefit: float = 0.0
    potential_cost: float = 0.0
    net_value: float = 0.0
    confidence: float = 0.0
    reasoning: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DialoguePlan:
    """Strategy for how the intervention should be delivered."""

    plan_id: str
    strategy: str = 'direct_suggestion'
    intensity: str = 'GentleReminder'
    content_outline: str = ''
    follow_up_needed: bool = False
    follow_up_delay_hours: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterventionObject:
    """Core intervention entity tracked by ACT-03."""

    intervention_id: str
    trigger_event: str = ''
    associated_goal: str = ''
    associated_plan: str = ''
    associated_habit: str = ''
    intervention_type: str = ''
    expected_benefit: float = 0.0
    potential_cost: float = 0.0
    confidence: float = 0.0
    timing_assessment: str = ''
    outcome_evaluation: str = ''
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterventionResult:
    """Output produced by the adaptive intervention pipeline."""

    intervention: InterventionObject
    timing: TimingAssessment | None = None
    opportunities: tuple[OpportunitySignal, ...] = ()
    risks: tuple[RiskSignal, ...] = ()
    evaluation: InterventionEvaluation | None = None
    dialogue_plan: DialoguePlan | None = None
    pipeline_phases_completed: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
