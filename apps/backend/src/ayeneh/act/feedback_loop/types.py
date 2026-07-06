"""ACT-04 Feedback Loop types.

Defines FeedbackObject and supporting value objects for the
feedback loop coordinator pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

FEEDBACK_TYPES: list[str] = [
    'behavioral',
    'planning',
    'prediction',
    'memory',
    'reflection',
    'strategy',
    'habit',
    'dialogue',
    'meta_cognitive',
]

FEEDBACK_SOURCES: list[str] = [
    'execution_observation',
    'goal_outcome',
    'plan_execution',
    'strategy_review',
    'habit_check',
    'dialogue_outcome',
    'reflection_result',
    'external_input',
    'system_alert',
]

FEEDBACK_SEVERITY_LEVELS: list[str] = [
    'positive',
    'neutral',
    'minor_correction',
    'major_correction',
    'critical',
]

PROPAGATION_MODES: list[str] = [
    'immediate',
    'batched',
    'delayed',
    'on_demand',
]

LEARNING_CATEGORIES: list[str] = [
    'reinforcement',
    'correction',
    'calibration',
    'novel_pattern',
    'contradiction_resolution',
    'strategy_update',
    'habit_adjustment',
    'meta_insight',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObservedOutcome:
    """An outcome observed from the system's actions."""

    outcome_id: str
    source_event: str = ''
    outcome_type: str = ''
    description: str = ''
    expected_value: Any = None
    actual_value: Any = None
    deviation_magnitude: float = 0.0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionEvaluation:
    """Evaluation of an action taken by the system."""

    evaluation_id: str
    action_description: str = ''
    expected_outcome: str = ''
    observed_outcome: str = ''
    outcome_match: bool = False
    success_score: float = 0.0
    contributing_factors: tuple[str, ...] = ()
    failure_reasons: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReflectionEntry:
    """A reflection on past actions and outcomes."""

    reflection_id: str
    reflection_type: str = 'general'
    source_evaluations: tuple[str, ...] = ()
    insights: tuple[str, ...] = ()
    patterns_identified: tuple[str, ...] = ()
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RealityCalibration:
    """Calibration adjustment based on reality testing."""

    calibration_id: str
    calibration_type: str = 'confidence'
    previous_value: float = 0.0
    adjusted_value: float = 0.0
    adjustment_reason: str = ''
    evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeUpdate:
    """An update to the system's knowledge base."""

    update_id: str
    update_type: str = 'addition'
    affected_module: str = ''
    previous_knowledge: str = ''
    new_knowledge: str = ''
    confidence_delta: float = 0.0
    source_reflections: tuple[str, ...] = ()
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyRevision:
    """A revision to the system's strategy."""

    revision_id: str
    affected_strategy: str = ''
    revision_type: str = 'adjustment'
    previous_approach: str = ''
    new_approach: str = ''
    rationale: str = ''
    source_reflections: tuple[str, ...] = ()
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BehavioralAdaptation:
    """A behavioral adaptation resulting from feedback."""

    adaptation_id: str
    adaptation_type: str = 'habit_adjustment'
    target_behavior: str = ''
    previous_pattern: str = ''
    new_pattern: str = ''
    expected_impact: str = ''
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackObject:
    """Core feedback entity tracked by ACT-04."""

    feedback_id: str
    source_event: str = ''
    affected_modules: tuple[str, ...] = ()
    observed_evidence: tuple[str, ...] = ()
    learning_outcome: str = ''
    confidence: float = 0.0
    propagation_targets: tuple[str, ...] = ()
    applied_revisions: tuple[dict[str, Any], ...] = ()
    remaining_questions: tuple[str, ...] = ()
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackResult:
    """Output produced by the feedback loop coordinator pipeline."""

    feedback: FeedbackObject
    observed_outcomes: tuple[ObservedOutcome, ...] = ()
    action_evaluations: tuple[ActionEvaluation, ...] = ()
    reflections: tuple[ReflectionEntry, ...] = ()
    calibrations: tuple[RealityCalibration, ...] = ()
    knowledge_updates: tuple[KnowledgeUpdate, ...] = ()
    strategy_revisions: tuple[StrategyRevision, ...] = ()
    behavioral_adaptations: tuple[BehavioralAdaptation, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PropagationRecord:
    """Record of feedback propagation across modules."""

    record_id: str
    source_feedback_id: str = ''
    target_module: str = ''
    propagation_mode: str = 'immediate'
    delivery_status: str = 'pending'
    applied: bool = False
    conflict_detected: bool = False
    conflict_resolution: str = ''
    latency_ms: float = 0.0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
