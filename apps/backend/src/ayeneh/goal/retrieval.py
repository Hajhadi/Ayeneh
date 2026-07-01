"""GoalRetrievalService — hybrid ranking for goal retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.goal.domain import Goal, GoalStatus

logger = structlog.get_logger(__name__)


@dataclass
class GoalRetrievalResult:
    goals: list[Goal]
    total: int
    query: str


@dataclass
class GoalRankingWeights:
    importance: float = 0.25
    urgency: float = 0.25
    progress: float = 0.15
    recency: float = 0.15
    confidence: float = 0.10
    manual_priority: float = 0.10

    PRIORITY_MAP = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}


class GoalRetrievalService:
    """Retrieves and ranks goals by composite score."""

    def __init__(self, goal_service: Any, weights: GoalRankingWeights | None = None) -> None:
        self._goal_service = goal_service
        self._weights = weights or GoalRankingWeights()

    async def retrieve(
        self, user_id: str, query: str = "",
        *, category: str | None = None, priority: str | None = None,
        include_completed: bool = False, limit: int = 20,
    ) -> GoalRetrievalResult:
        status = "active" if not include_completed else None
        goals = await self._goal_service.list_goals(user_id, status=status, category=category, priority=priority, limit=100)
        ranked = sorted(goals, key=lambda g: self._score(g), reverse=True)
        return GoalRetrievalResult(goals=ranked[:limit], total=len(ranked), query=query)

    async def retrieve_urgent(self, user_id: str, limit: int = 10) -> list[Goal]:
        goals = await self._goal_service.get_active_goals(user_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        urgent = []
        for g in goals:
            if g.deadline:
                dl = datetime.fromisoformat(g.deadline)
                if dl.tzinfo:
                    dl = dl.replace(tzinfo=None)
                days_left = (dl - now).total_seconds() / 86400
                if days_left <= 7:
                    urgent.append(g)
        return sorted(urgent, key=lambda g: g.days_until_deadline or 999)[:limit]

    async def retrieve_blocked(self, user_id: str) -> list[Goal]:
        goals = await self._goal_service.list_goals(user_id, status="blocked")
        return goals

    async def retrieve_by_deadline(self, user_id: str, within_days: int = 30) -> list[Goal]:
        goals = await self._goal_service.get_active_goals(user_id)
        now = datetime.now(UTC)
        return [
            g for g in goals if g.deadline
            and (datetime.fromisoformat(g.deadline) - now).total_seconds() / 86400 <= within_days
        ]

    def _score(self, goal: Goal) -> float:
        w = self._weights
        importance_score = goal.importance
        urgency_score = 0.0
        if goal.deadline:
            days_left = goal.days_until_deadline or 365
            urgency_score = max(0.0, 1.0 - days_left / 30)
        progress_score = goal.progress
        recency_score = 0.0
        if goal.last_progress_at:
            days_since = (datetime.now(UTC) - datetime.fromisoformat(goal.last_progress_at)).total_seconds() / 86400
            recency_score = max(0.0, 1.0 - days_since / 90)
        confidence_score = goal.confidence
        priority_score = GoalRankingWeights.PRIORITY_MAP.get(goal.priority, 0.5)

        return (
            w.importance * importance_score
            + w.urgency * urgency_score
            + w.progress * progress_score
            + w.recency * recency_score
            + w.confidence * confidence_score
            + w.manual_priority * priority_score
        )
