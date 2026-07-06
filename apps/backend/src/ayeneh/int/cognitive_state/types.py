"""INT-04 Unified Cognitive State — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


STATE_DIMENSIONS = [
    'memory',
    'inference',
    'executive',
    'action',
    'self',
    'communication',
    'context',
    'governance',
]

STATE_TRANSITIONS = [
    'idle_to_active',
    'active_to_planning',
    'planning_to_execution',
    'execution_to_reflection',
    'reflection_to_learning',
    'learning_to_architectural_update',
]

VALID_FROM_STATES = {
    'idle_to_active': ('idle',),
    'active_to_planning': ('active',),
    'planning_to_execution': ('planning',),
    'execution_to_reflection': ('execution',),
    'reflection_to_learning': ('reflection',),
    'learning_to_architectural_update': ('learning',),
}

VALID_TO_STATES = {
    'idle_to_active': 'active',
    'active_to_planning': 'planning',
    'planning_to_execution': 'execution',
    'execution_to_reflection': 'reflection',
    'reflection_to_learning': 'learning',
    'learning_to_architectural_update': 'architectural_update',
}

HEALTH_THRESHOLDS = {
    'critical': 0.3,
    'degraded': 0.6,
    'healthy': 0.8,
    'optimal': 0.95,
}


@dataclass(frozen=True)
class DimensionStatus:
    """Status of a single cognitive dimension."""

    dimension: str = ''
    active: bool = False
    confidence: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    contributing_modules: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dimension and self.dimension not in STATE_DIMENSIONS:
            raise ValueError(
                f"Invalid dimension: {self.dimension!r}. "
                f"Must be one of {STATE_DIMENSIONS}"
            )


@dataclass(frozen=True)
class StateTransition:
    """Records a single state transition event."""

    transition_id: str = ''
    transition_type: str = ''
    from_state: str = ''
    to_state: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    trigger: str = ''
    confidence: float = 0.0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.transition_type and self.transition_type not in STATE_TRANSITIONS:
            raise ValueError(
                f"Invalid transition: {self.transition_type!r}. "
                f"Must be one of {STATE_TRANSITIONS}"
            )


@dataclass(frozen=True)
class ConflictRecord:
    """A detected conflict within the cognitive state."""

    conflict_id: str = ''
    source_dimension: str = ''
    target_dimension: str = ''
    conflict_type: str = ''  # 'inconsistency', 'stale', 'contradictory'
    severity: str = 'low'  # 'low', 'medium', 'high', 'critical'
    description: str = ''
    resolution_strategy: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ArchitectureSyncRecord:
    """Record of an architecture synchronization event."""

    sync_id: str = ''
    synced_dimensions: tuple[str, ...] = ()
    conflicts_resolved: int = 0
    health_before: float = 0.0
    health_after: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of cognitive state decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    decision_points: tuple[dict[str, Any], ...] = ()
    alternative_interpretations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CognitiveStateObject:
    """Core domain object representing the unified cognitive state."""

    state_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    active_modules: tuple[str, ...] = ()
    active_goals: tuple[str, ...] = ()
    running_workflows: tuple[str, ...] = ()
    resource_status: dict[str, Any] = field(default_factory=dict)
    confidence_map: dict[str, float] = field(default_factory=dict)
    consistency_status: str = 'consistent'
    architecture_health: float = 1.0
    execution_snapshot: dict[str, Any] = field(default_factory=dict)
    revision_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CognitiveStateResult:
    """Complete result from the CognitiveStateEngine pipeline."""

    state_id: str = ''
    state_object: CognitiveStateObject | None = None
    dimension_statuses: tuple[DimensionStatus, ...] = ()
    transitions: tuple[StateTransition, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    sync_records: tuple[ArchitectureSyncRecord, ...] = ()
    global_confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def dimension_count(self) -> int:
        return len(self.dimension_statuses)
