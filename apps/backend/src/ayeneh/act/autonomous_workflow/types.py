"""ACT-05 Autonomous Workflow types.

Defines WorkflowObject and supporting value objects for the
autonomous workflow engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

WORKFLOW_PHASES: list[str] = [
    'initialization',
    'preparation',
    'execution',
    'monitoring',
    'adaptation',
    'completion',
    'maintenance',
    'archival',
]

WORKFLOW_STATUSES: list[str] = [
    'active',
    'paused',
    'completed',
    'failed',
    'cancelled',
    'archived',
]

WORKFLOW_PRIORITIES: list[str] = [
    'critical',
    'high',
    'medium',
    'low',
    'background',
]

DEPENDENCY_TYPES: list[str] = [
    'blocking',
    'non_blocking',
    'data_dependency',
    'resource_dependency',
    'temporal',
]

PHASE_VALID_TRANSITIONS: dict[str, list[str]] = {
    'initialization': ['preparation', 'cancelled'],
    'preparation': ['execution', 'cancelled'],
    'execution': ['monitoring', 'adaptation', 'completion', 'cancelled'],
    'monitoring': ['adaptation', 'execution', 'completion', 'cancelled'],
    'adaptation': ['execution', 'monitoring', 'cancelled'],
    'completion': ['maintenance', 'archival'],
    'maintenance': ['execution', 'archival'],
    'archival': [],
}


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalNode:
    """A node in the workflow goal graph."""

    node_id: str
    goal_description: str = ''
    priority: float = 0.0
    status: str = 'pending'
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySelection:
    """Selected strategy for a workflow phase."""

    selection_id: str
    strategy_name: str = ''
    strategy_type: str = 'default'
    confidence: float = 0.0
    rationale: str = ''
    alternatives: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanningStep:
    """A step within a workflow plan."""

    step_id: str
    description: str = ''
    order: int = 0
    status: str = 'pending'
    estimated_duration_ms: float = 0.0
    actual_duration_ms: float = 0.0
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionRecord:
    """Record of a workflow execution step."""

    record_id: str
    step_id: str = ''
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = 'running'
    output: str = ''
    error: str = ''
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MonitoringCheckpoint:
    """A monitoring checkpoint in the workflow."""

    checkpoint_id: str
    phase: str = ''
    progress: float = 0.0
    health_status: str = 'healthy'
    alerts: tuple[str, ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdaptationRecord:
    """Record of a workflow adaptation."""

    adaptation_id: str
    trigger: str = ''
    previous_state: str = ''
    new_state: str = ''
    rationale: str = ''
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowObject:
    """Core workflow entity tracked by ACT-05."""

    workflow_id: str
    associated_goals: tuple[str, ...] = ()
    associated_plans: tuple[str, ...] = ()
    current_phase: str = 'initialization'
    execution_history: tuple[dict[str, Any], ...] = ()
    dependencies: tuple[dict[str, Any], ...] = ()
    responsible_modules: tuple[str, ...] = ()
    current_status: str = 'active'
    priority: float = 0.0
    progress: float = 0.0
    confidence: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowResult:
    """Output produced by the autonomous workflow engine pipeline."""

    workflow: WorkflowObject
    goal_graph: tuple[GoalNode, ...] = ()
    strategy_selections: tuple[StrategySelection, ...] = ()
    planning_steps: tuple[PlanningStep, ...] = ()
    execution_records: tuple[ExecutionRecord, ...] = ()
    monitoring_checkpoints: tuple[MonitoringCheckpoint, ...] = ()
    adaptations: tuple[AdaptationRecord, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
