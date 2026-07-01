"""GoalService — single owner of all goal business rules."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.goal.domain import (
    Goal,
    GoalDependency,
    GoalHistory,
    GoalMilestone,
    GoalReview,
    GoalStatus,
)

logger = structlog.get_logger(__name__)


@dataclass
class GoalStats:
    total: int = 0
    active: int = 0
    completed: int = 0
    abandoned: int = 0
    overdue: int = 0
    blocked: int = 0
    paused: int = 0
    avg_progress: float = 0.0
    completion_rate: float = 0.0
    by_category: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)


class GoalService:
    """Single owner of all goal business rules and persistence."""

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def create_goal(self, user_id: str, title: str, **kwargs: Any) -> Goal:
        goal = Goal(user_id=user_id, title=title, **kwargs)
        goal.record_history("created", None, "draft", "Goal created")
        goal.confidence_history = {"initial": goal.confidence}
        goal.importance_history = {"initial": goal.importance}
        await self._save_goal(goal)
        logger.info("goal_created", goal_id=goal.id, title=title)
        return goal

    async def update_goal(self, goal_id: str, **updates: Any) -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        for key, value in updates.items():
            if hasattr(goal, key) and value is not None:
                old = getattr(goal, key)
                if old != value:
                    goal.record_history(f"updated_{key}", str(old), str(value))
                    setattr(goal, key, value)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def activate_goal(self, goal_id: str) -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        if goal.status not in (GoalStatus.DRAFT, GoalStatus.PAUSED, GoalStatus.BLOCKED):
            raise ValueError(f"Cannot activate from {goal.status}")
        old = goal.status
        goal.status = GoalStatus.ACTIVE
        goal.record_history("status_changed", old, GoalStatus.ACTIVE)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def pause_goal(self, goal_id: str, reason: str = "") -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        old = goal.status
        goal.status = GoalStatus.PAUSED
        goal.record_history("status_changed", old, GoalStatus.PAUSED, reason)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def complete_goal(self, goal_id: str) -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        old = goal.status
        goal.status = GoalStatus.COMPLETED
        goal.progress = 1.0
        goal.completed_at = datetime.now(UTC).isoformat()
        goal.record_history("status_changed", old, GoalStatus.COMPLETED)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def abandon_goal(self, goal_id: str, reason: str = "") -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        old = goal.status
        goal.status = GoalStatus.ABANDONED
        goal.abandoned_at = datetime.now(UTC).isoformat()
        goal.record_history("status_changed", old, GoalStatus.ABANDONED, reason)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def archive_goal(self, goal_id: str) -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        old = goal.status
        goal.status = GoalStatus.ARCHIVED
        goal.record_history("status_changed", old, GoalStatus.ARCHIVED)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def update_progress(self, goal_id: str, progress: float, note: str = "") -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        old_p = goal.progress
        goal.progress = max(0.0, min(1.0, progress))
        goal.last_progress_at = datetime.now(UTC).isoformat()
        goal.record_history("progress_changed", f"{old_p:.2f}", f"{goal.progress:.2f}", note)
        if goal.progress >= 1.0 and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(UTC).isoformat()
            goal.record_history("status_changed", GoalStatus.ACTIVE, GoalStatus.COMPLETED, "auto-complete")
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def add_milestone(self, goal_id: str, title: str, target_value: float = 1.0) -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        m = GoalMilestone(title=title, target_value=target_value)
        goal.milestones.append(m)
        goal.record_history("milestone_added", None, m.id, title)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def add_dependency(self, goal_id: str, dependency_id: str, dep_type: str = "blocks") -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        goal.dependencies.append(GoalDependency(dependency_id=dependency_id, dependency_type=dep_type))
        goal.record_history("dependency_added", None, dependency_id, dep_type)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def add_review(self, goal_id: str, rating: float, notes: str = "") -> Goal:
        goal = await self._get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Goal {goal_id} not found")
        review = GoalReview(goal_id=goal_id, rating=rating, notes=notes)
        goal.reviews.append(review)
        goal.last_reviewed_at = datetime.now(UTC).isoformat()
        goal.record_history("reviewed", None, f"{rating:.2f}", notes)
        goal.updated_at = datetime.now(UTC).isoformat()
        await self._save_goal(goal)
        return goal

    async def get_goal(self, goal_id: str) -> Goal | None:
        return await self._get_goal(goal_id)

    async def list_goals(self, user_id: str, **filters: Any) -> list[Goal]:
        async with self._uow_factory() as uow:
            clean = {k: v for k, v in filters.items() if v is not None}
            models = await uow.goals.list_by_user(uuid.UUID(user_id), **clean)
            return [self._model_to_goal(m) for m in models]

    async def get_active_goals(self, user_id: str) -> list[Goal]:
        return await self.list_goals(user_id, status="active")

    async def get_overdue_goals(self, user_id: str) -> list[Goal]:
        async with self._uow_factory() as uow:
            models = await uow.goals.find_overdue(uuid.UUID(user_id))
            return [self._model_to_goal(m) for m in models]

    async def get_stalled_goals(self, user_id: str, stall_days: int = 30) -> list[Goal]:
        async with self._uow_factory() as uow:
            models = await uow.goals.find_stalled(uuid.UUID(user_id), stall_days)
            return [self._model_to_goal(m) for m in models]

    async def get_stats(self, user_id: str) -> GoalStats:
        async with self._uow_factory() as uow:
            all_m = await uow.goals.list_by_user(uuid.UUID(user_id), limit=1000)
            all_g = [self._model_to_goal(m) for m in all_m]
            now = datetime.now(UTC)
            active = [g for g in all_g if g.status == "active"]
            overdue = [g for g in all_g if g.status == "active" and g.deadline and datetime.fromisoformat(g.deadline) < now]
            by_cat: dict[str, int] = {}
            by_pri: dict[str, int] = {}
            for g in all_g:
                by_cat[g.category] = by_cat.get(g.category, 0) + 1
                by_pri[g.priority] = by_pri.get(g.priority, 0) + 1
            return GoalStats(
                total=len(all_g), active=len(active),
                completed=sum(1 for g in all_g if g.status == "completed"),
                abandoned=sum(1 for g in all_g if g.status == "abandoned"),
                overdue=len(overdue),
                blocked=sum(1 for g in all_g if g.status == "blocked"),
                paused=sum(1 for g in all_g if g.status == "paused"),
                avg_progress=sum(g.progress for g in active) / max(len(active), 1),
                completion_rate=sum(1 for g in all_g if g.status == "completed") / max(len(all_g), 1),
                by_category=by_cat, by_priority=by_pri,
            )

    async def get_history(self, goal_id: str) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            events = await uow.goal_history.list_by_goal(uuid.UUID(goal_id))
            return [{"event_type": e.event_type, "old_value": e.old_value,
                     "new_value": e.new_value, "detail": e.detail,
                     "created_at": e.created_at.isoformat() if e.created_at else ""} for e in events]

    async def _get_goal(self, goal_id: str) -> Goal | None:
        async with self._uow_factory() as uow:
            m = await uow.goals.get_by_id(uuid.UUID(goal_id))
            return self._model_to_goal(m) if m else None

    @staticmethod
    def _parse_dt(val: str | None) -> datetime | None:
        if not val:
            return None
        dt = datetime.fromisoformat(val)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    async def _save_goal(self, goal: Goal) -> None:
        async with self._uow_factory() as uow:
            m = await uow.goals.get_by_id(uuid.UUID(goal.id))
            if m:
                self._update_model(m, goal)
            else:
                m = self._goal_to_model(goal)
                await uow.goals.create(m)
            for entry in goal.history:
                if entry.id:
                    existing = await uow.goal_history.list_by_goal(uuid.UUID(goal.id), limit=10000)
                    existing_ids = {str(h.id) for h in existing}
                    if entry.id not in existing_ids:
                        from ayeneh.infrastructure.persistence.models.goal import GoalHistoryModel
                        h_model = GoalHistoryModel(
                            id=uuid.UUID(entry.id),
                            goal_id=uuid.UUID(entry.goal_id),
                            event_type=entry.event_type,
                            old_value=entry.old_value,
                            new_value=entry.new_value,
                            detail=entry.detail,
                            created_at=datetime.fromisoformat(entry.created_at) if entry.created_at else datetime.now(UTC),
                        )
                        await uow.goal_history.create(h_model)
            await uow.commit()

    def _goal_to_model(self, g: Goal) -> Any:
        from ayeneh.infrastructure.persistence.models.goal import GoalModel
        return GoalModel(
            id=uuid.UUID(g.id), user_id=uuid.UUID(g.user_id),
            title=g.title, description=g.description,
            status=g.status, priority=g.priority, category=g.category,
            goal_type=g.goal_type, importance=g.importance, confidence=g.confidence,
            relevance=g.relevance, progress=g.progress, tags=g.tags,
            related_goal_ids=g.related_goal_ids,
            milestones=[{"id": m.id, "title": m.title, "target_value": m.target_value,
                         "current_value": m.current_value, "completed": m.completed}
                        for m in g.milestones],
            dependencies=[{"dependency_id": d.dependency_id, "dependency_type": d.dependency_type}
                           for d in g.dependencies],
            confidence_history=g.confidence_history,
            importance_history=g.importance_history,
            created_at=datetime.fromisoformat(g.created_at) if g.created_at else datetime.now(UTC),
            updated_at=datetime.fromisoformat(g.updated_at) if g.updated_at else datetime.now(UTC),
            parent_goal_id=uuid.UUID(g.parent_goal_id) if g.parent_goal_id else None,
            deadline=self._parse_dt(g.deadline),
            target_date=self._parse_dt(g.target_date),
            completed_at=self._parse_dt(g.completed_at),
            abandoned_at=self._parse_dt(g.abandoned_at),
            last_reviewed_at=self._parse_dt(g.last_reviewed_at),
            last_progress_at=self._parse_dt(g.last_progress_at),
            evolution_version=1,
        )

    def _model_to_goal(self, m: Any) -> Goal:
        return Goal(
            id=str(m.id), user_id=str(m.user_id),
            title=m.title, description=m.description,
            status=m.status, priority=m.priority, category=m.category,
            goal_type=m.goal_type, importance=m.importance, confidence=m.confidence,
            relevance=m.relevance, progress=m.progress,
            tags=m.tags or [], related_goal_ids=m.related_goal_ids or [],
            milestones=[GoalMilestone(**d) for d in (m.milestones or []) if isinstance(d, dict)],
            dependencies=[GoalDependency(**d) for d in (m.dependencies or []) if isinstance(d, dict)],
            confidence_history=m.confidence_history or {},
            importance_history=m.importance_history or {},
            parent_goal_id=str(m.parent_goal_id) if m.parent_goal_id else None,
            deadline=m.deadline.isoformat() if m.deadline else None,
            target_date=m.target_date.isoformat() if m.target_date else None,
            completed_at=m.completed_at.isoformat() if m.completed_at else None,
            abandoned_at=m.abandoned_at.isoformat() if m.abandoned_at else None,
            last_reviewed_at=m.last_reviewed_at.isoformat() if m.last_reviewed_at else None,
            last_progress_at=m.last_progress_at.isoformat() if m.last_progress_at else None,
            created_at=m.created_at.isoformat() if m.created_at else "",
            updated_at=m.updated_at.isoformat() if m.updated_at else "",
        )

    def _update_model(self, m: Any, g: Goal) -> None:
        m.title, m.description = g.title, g.description
        m.status, m.priority = g.status, g.priority
        m.category, m.goal_type = g.category, g.goal_type
        m.importance, m.confidence, m.relevance = g.importance, g.confidence, g.relevance
        m.progress = g.progress
        m.tags, m.related_goal_ids = g.tags, g.related_goal_ids
        m.deadline = self._parse_dt(g.deadline)
        m.target_date = self._parse_dt(g.target_date)
        m.completed_at = self._parse_dt(g.completed_at)
        m.abandoned_at = self._parse_dt(g.abandoned_at)
        m.last_reviewed_at = self._parse_dt(g.last_reviewed_at)
        m.last_progress_at = self._parse_dt(g.last_progress_at)
        m.milestones = [{"id": x.id, "title": x.title, "target_value": x.target_value,
                         "current_value": x.current_value, "completed": x.completed}
                        for x in g.milestones]
        m.dependencies = [{"dependency_id": d.dependency_id, "dependency_type": d.dependency_type}
                           for d in g.dependencies]
        m.confidence_history = g.confidence_history
        m.importance_history = g.importance_history
        m.updated_at = datetime.fromisoformat(g.updated_at) if g.updated_at else datetime.now(UTC)
        m.evolution_version = getattr(m, "evolution_version", 0) + 1
