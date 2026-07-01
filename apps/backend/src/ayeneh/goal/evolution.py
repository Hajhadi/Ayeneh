"""GoalEvolutionService — evolution rules for goals, separate from MemoryEvolutionService."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.goal.domain import GoalStatus

logger = structlog.get_logger(__name__)


@dataclass
class GoalEvolutionConfig:
    aging_halflife_days: float = 180.0
    strengthen_factor: float = 0.05
    weaken_factor: float = 0.03
    min_confidence: float = 0.1
    stale_days: int = 60


@dataclass
class GoalEvolutionResult:
    aged: int = 0
    strengthened: int = 0
    weakened: int = 0
    overdue_detected: int = 0
    stale_detected: int = 0


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


class GoalEvolutionService:
    """Evolution rules for goals — independent from MemoryEvolutionService."""

    def __init__(self, goal_service: Any, config: GoalEvolutionConfig | None = None) -> None:
        self._goal_service = goal_service
        self._config = config or GoalEvolutionConfig()

    async def run_daily(self, user_id: str) -> GoalEvolutionResult:
        result = GoalEvolutionResult()
        goals = await self._goal_service.get_active_goals(user_id)
        now = _naive_now()

        for goal in goals:
            if goal.deadline and _parse_dt(goal.deadline) < now:
                await self._goal_service.update_goal(
                    goal.id, confidence=max(0.0, goal.confidence - self._config.weaken_factor)
                )
                result.overdue_detected += 1

            if goal.last_progress_at:
                days_since = (now - _parse_dt(goal.last_progress_at)).total_seconds() / 86400
                if days_since > self._config.stale_days:
                    await self._goal_service.update_goal(
                        goal.id,
                        confidence=max(self._config.min_confidence, goal.confidence - self._config.weaken_factor),
                    )
                    result.stale_detected += 1

            age_days = (now - _parse_dt(goal.created_at)).total_seconds() / 86400
            decay = 0.5 ** (age_days / self._config.aging_halflife_days)
            new_conf = max(self._config.min_confidence, goal.confidence * decay)
            if abs(new_conf - goal.confidence) > 0.01:
                await self._goal_service.update_goal(goal.id, confidence=new_conf)
                result.aged += 1

        logger.info("goal_daily_evolution", user_id=user_id, **vars(result))
        return result

    async def run_weekly(self, user_id: str) -> GoalEvolutionResult:
        result = GoalEvolutionResult()
        goals = await self._goal_service.get_active_goals(user_id)

        for goal in goals:
            if goal.progress > 0 and goal.progress < 1.0:
                new_conf = min(1.0, goal.confidence + self._config.strengthen_factor)
                if new_conf > goal.confidence:
                    await self._goal_service.update_goal(goal.id, confidence=new_conf)
                    result.strengthened += 1

            if goal.progress == 0:
                new_conf = max(self._config.min_confidence, goal.confidence - self._config.weaken_factor * 2)
                if new_conf < goal.confidence:
                    await self._goal_service.update_goal(goal.id, confidence=new_conf)
                    result.weakened += 1

        logger.info("goal_weekly_evolution", user_id=user_id, **vars(result))
        return result

    async def run_monthly(self, user_id: str) -> GoalEvolutionResult:
        result = GoalEvolutionResult()
        completed = await self._goal_service.list_goals(user_id, status="completed")
        for goal in completed:
            await self._goal_service.archive_goal(goal.id)
            result.aged += 1
        logger.info("goal_monthly_evolution", user_id=user_id, completed_archived=result.aged)
        return result
