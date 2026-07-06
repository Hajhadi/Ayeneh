"""DEC-03 Planning Engine types.

Defines PlanObject, PlanResult, and supporting value objects for the
planning engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

PLANNING_HORIZONS: list[str] = [
    'immediate',
    'daily',
    'weekly',
    'project',
    'quarterly',
    'long_term',
]

DEPENDENCY_TYPES: list[str] = [
    'sequential',
    'parallel',
    'conditional',
    'resource_dependent',
    'knowledge_dependent',
]

TASK_STATUSES: list[str] = [
    'pending',
    'in_progress',
    'completed',
    'blocked',
    'deferred',
    'cancelled',
]

PLAN_LIFECYCLE: list[str] = [
    'draft',
    'active',
    'paused',
    'completed',
    'abandoned',
    'revised',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskDependency:
    """A dependency between two tasks."""

    dependency_id: str
    source_task: str = ''
    target_task: str = ''
    dependency_type: str = 'sequential'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduleSlot:
    """A time slot in the generated schedule."""

    slot_id: str
    task_id: str = ''
    start_offset_hours: float = 0.0
    duration_hours: float = 0.0
    resource_required: str = ''
    priority: float = 0.0


@dataclass(frozen=True)
class PlanRiskAssessment:
    """Risk assessment for a plan."""

    risk_id: str
    description: str = ''
    probability: float = 0.0
    impact: float = 0.0
    mitigations: tuple[str, ...] = ()
    affected_tasks: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanObject:
    """A single plan produced by the planning engine (DEC-03)."""

    plan_id: str
    associated_goal: str = ''
    planning_horizon: str = 'daily'
    milestones: tuple[dict[str, Any], ...] = ()
    tasks: tuple[dict[str, Any], ...] = ()
    dependencies: tuple[dict[str, Any], ...] = ()
    constraints: tuple[dict[str, Any], ...] = ()
    estimated_duration: float = 0.0
    required_resources: tuple[dict[str, Any], ...] = ()
    risk_assessment: tuple[dict[str, Any], ...] = ()
    progress: float = 0.0
    confidence: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanResult:
    """Complete result of the planning pipeline."""

    plan: PlanObject = field(default_factory=lambda: PlanObject(plan_id=''))
    schedule: tuple[ScheduleSlot, ...] = ()
    risks: tuple[PlanRiskAssessment, ...] = ()
    critical_path: tuple[str, ...] = ()
    summary: str = ''
    processing_metadata: dict[str, Any] = field(default_factory=dict)
