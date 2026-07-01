"""Goal Engine — domain types and value objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class GoalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class GoalPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GoalCategory(StrEnum):
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    HEALTH = "health"
    LEARNING = "learning"
    RELATIONSHIPS = "relationships"
    CREATIVE = "creative"
    FINANCIAL = "financial"
    OTHER = "other"


class GoalType(StrEnum):
    OUTCOME = "outcome"
    PROCESS = "process"
    HABIT = "habit"
    MILESTONE = "milestone"
    PROJECT = "project"


@dataclass
class GoalMilestone:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    target_value: float = 1.0
    current_value: float = 0.0
    due_date: str | None = None
    completed: bool = False
    completed_at: str | None = None

    @property
    def progress_pct(self) -> float:
        if self.target_value <= 0:
            return 1.0 if self.completed else 0.0
        return min(1.0, self.current_value / self.target_value)


@dataclass
class GoalDependency:
    dependency_id: str = ""
    dependency_type: str = "blocks"
    description: str = ""


@dataclass
class GoalHistory:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    event_type: str = ""
    old_value: str | None = None
    new_value: str | None = None
    detail: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class GoalObservation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    content: str = ""
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class GoalReview:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str = ""
    rating: float = 0.5
    notes: str = ""
    reviewer: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Goal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    description: str = ""
    status: str = GoalStatus.DRAFT
    priority: str = GoalPriority.MEDIUM
    category: str = GoalCategory.OTHER
    goal_type: str = GoalType.OUTCOME
    importance: float = 0.5
    confidence: float = 0.5
    relevance: float = 0.5
    progress: float = 0.0
    parent_goal_id: str | None = None
    deadline: str | None = None
    target_date: str | None = None
    completed_at: str | None = None
    abandoned_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_reviewed_at: str | None = None
    last_progress_at: str | None = None
    tags: list[str] = field(default_factory=list)
    related_goal_ids: list[str] = field(default_factory=list)
    dependencies: list[GoalDependency] = field(default_factory=list)
    milestones: list[GoalMilestone] = field(default_factory=list)
    history: list[GoalHistory] = field(default_factory=list)
    observations: list[GoalObservation] = field(default_factory=list)
    reviews: list[GoalReview] = field(default_factory=list)
    confidence_history: dict[str, float] = field(default_factory=dict)
    importance_history: dict[str, float] = field(default_factory=dict)

    def record_history(self, event_type: str, old: str | None, new: str | None, detail: str = "") -> GoalHistory:
        entry = GoalHistory(goal_id=self.id, event_type=event_type, old_value=old, new_value=new, detail=detail)
        self.history.append(entry)
        self.updated_at = datetime.now(UTC).isoformat()
        return entry

    @staticmethod
    def _to_naive(dt_str: str) -> datetime:
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    @property
    def is_overdue(self) -> bool:
        if not self.deadline:
            return False
        now = datetime.now(UTC).replace(tzinfo=None)
        return self._to_naive(self.deadline) < now

    @property
    def days_until_deadline(self) -> float | None:
        if not self.deadline:
            return None
        now = datetime.now(UTC).replace(tzinfo=None)
        return max(0, (self._to_naive(self.deadline) - now).total_seconds() / 86400)

    @property
    def milestone_progress(self) -> float:
        if not self.milestones:
            return 0.0
        return sum(m.progress_pct for m in self.milestones) / len(self.milestones)

    def is_blocked(self, all_goals: dict[str, Goal] | None = None) -> bool:
        if not all_goals:
            return False
        for dep in self.dependencies:
            if dep.dependency_type == "blocks":
                dep_goal = all_goals.get(dep.dependency_id)
                if dep_goal and dep_goal.status not in (GoalStatus.COMPLETED, GoalStatus.ABANDONED):
                    return True
        return False
