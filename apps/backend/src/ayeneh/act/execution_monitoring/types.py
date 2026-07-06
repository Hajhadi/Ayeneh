"""ACT-01 Execution Monitoring types.

Defines ExecutionObject and supporting value objects for the
execution monitoring engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

EXECUTION_STATES: list[str] = [
    'prepared',
    'initialized',
    'running',
    'paused',
    'blocked',
    'delayed',
    'completed',
    'cancelled',
    'archived',
]

VALID_STATE_TRANSITIONS: dict[str, list[str]] = {
    'prepared': ['initialized', 'cancelled'],
    'initialized': ['running', 'cancelled'],
    'running': ['paused', 'blocked', 'delayed', 'completed', 'cancelled'],
    'paused': ['running', 'cancelled'],
    'blocked': ['running', 'delayed', 'cancelled'],
    'delayed': ['running', 'blocked', 'cancelled'],
    'completed': ['archived'],
    'cancelled': ['archived'],
    'archived': [],
}

DEVIATION_SEVERITY_LEVELS: list[str] = [
    'negligible',
    'minor',
    'moderate',
    'significant',
    'critical',
]

RESOURCE_CATEGORIES: list[str] = [
    'time',
    'cognitive_effort',
    'emotional_energy',
    'social_capital',
    'financial',
    'informational',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviationRecord:
    """A detected deviation from the expected execution path."""

    deviation_id: str
    deviation_type: str = ''
    severity: str = 'minor'
    description: str = ''
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expected_value: Any = None
    observed_value: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResourceConsumption:
    """Tracks consumption of a specific resource category."""

    resource_type: str = 'time'
    allocated: float = 0.0
    consumed: float = 0.0
    remaining: float = 0.0
    efficiency: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionProgress:
    """Snapshot of execution progress at a point in time."""

    progress_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    completion_ratio: float = 0.0
    milestones_achieved: tuple[str, ...] = ()
    milestones_pending: tuple[str, ...] = ()
    quality_score: float = 0.0
    velocity: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BehavioralFeedback:
    """Feedback generated from execution observation."""

    feedback_id: str
    feedback_type: str = 'informational'
    message: str = ''
    severity: str = 'info'
    actionable: bool = False
    suggested_action: str = ''
    confidence: float = 0.0
    generation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionSnapshot:
    """A point-in-time snapshot of execution state for version history."""

    snapshot_id: str
    state: str = 'prepared'
    progress: float = 0.0
    confidence: float = 0.0
    risk_level: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionObject:
    """Core execution entity tracked by ACT-01."""

    execution_id: str
    associated_plan: str = ''
    associated_goal: str = ''
    current_state: str = 'prepared'
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    expected_completion: datetime = field(default_factory=lambda: datetime.now(UTC))
    observed_progress: float = 0.0
    consumed_resources: dict[str, float] = field(default_factory=dict)
    detected_deviations: tuple[dict[str, Any], ...] = ()
    execution_confidence: float = 0.0
    risk_level: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    """Output produced by the execution monitoring pipeline."""

    execution: ExecutionObject
    state_transition: str = ''
    deviations_detected: tuple[DeviationRecord, ...] = ()
    resource_report: tuple[ResourceConsumption, ...] = ()
    progress_snapshots: tuple[ExecutionProgress, ...] = ()
    feedback: tuple[BehavioralFeedback, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
