"""Planning Structure — COG-08 support.

Defines the planning decomposition for goals: milestones, dependencies,
resources, constraints, and alternative pathways.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class PlanningStructure:
    """Planning decomposition attached to a single goal.

    Captures how the agent intends to achieve the goal, including
    milestones, resource requirements, constraints, and fallback pathways.
    """

    goal_id: str
    milestones: tuple[dict[str, Any], ...] = ()
    dependencies: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    estimated_duration_days: int = 0
    constraints: tuple[str, ...] = ()
    alternative_pathways: tuple[str, ...] = ()
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    specification_version: str = '1.0.0'
