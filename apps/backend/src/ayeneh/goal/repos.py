"""Goal repositories — persistence operations for goals."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.goal import GoalEvolutionEventModel, GoalHistoryModel, GoalModel, GoalReviewModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid
    from sqlalchemy.ext.asyncio import AsyncSession


class GoalRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoalModel)

    async def list_by_user(
        self, user_id: uuid.UUID, *, status: str | None = None,
        category: str | None = None, priority: str | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[GoalModel]:
        stmt = self._base_query().where(GoalModel.user_id == user_id)
        if status:
            stmt = stmt.where(GoalModel.status == status)
        if category:
            stmt = stmt.where(GoalModel.category == category)
        if priority:
            stmt = stmt.where(GoalModel.priority == priority)
        stmt = stmt.order_by(GoalModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID, *, status: str | None = None) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(GoalModel).where(GoalModel.user_id == user_id)
        if status:
            stmt = stmt.where(GoalModel.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_overdue(self, user_id: uuid.UUID) -> list[GoalModel]:
        from sqlalchemy import and_
        from datetime import UTC, datetime
        now = datetime.now(UTC)
        stmt = self._base_query().where(and_(
            GoalModel.user_id == user_id,
            GoalModel.status == "active",
            GoalModel.deadline < now,
        ))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_stalled(self, user_id: uuid.UUID, stall_days: int = 30) -> list[GoalModel]:
        from sqlalchemy import and_, func
        from datetime import UTC, datetime, timedelta
        cutoff = datetime.now(UTC) - timedelta(days=stall_days)
        stmt = self._base_query().where(and_(
            GoalModel.user_id == user_id,
            GoalModel.status == "active",
            GoalModel.last_progress_at < cutoff,
        ))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class GoalEvolutionEventRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoalEvolutionEventModel)

    async def list_by_goal(self, goal_id: uuid.UUID, limit: int = 100) -> list[GoalEvolutionEventModel]:
        stmt = select(GoalEvolutionEventModel).where(
            GoalEvolutionEventModel.goal_id == goal_id
        ).order_by(GoalEvolutionEventModel.created_at).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 100) -> list[GoalEvolutionEventModel]:
        stmt = select(GoalEvolutionEventModel).where(
            GoalEvolutionEventModel.user_id == user_id
        ).order_by(GoalEvolutionEventModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(self, user_id: uuid.UUID, event_type: str) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(GoalEvolutionEventModel).where(
            GoalEvolutionEventModel.user_id == user_id,
            GoalEvolutionEventModel.event_type == event_type,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class GoalHistoryRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoalHistoryModel)

    async def list_by_goal(self, goal_id: uuid.UUID, limit: int = 100) -> list[GoalHistoryModel]:
        stmt = select(GoalHistoryModel).where(
            GoalHistoryModel.goal_id == goal_id
        ).order_by(GoalHistoryModel.created_at).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class GoalReviewRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoalReviewModel)

    async def list_by_goal(self, goal_id: uuid.UUID, limit: int = 50) -> list[GoalReviewModel]:
        stmt = select(GoalReviewModel).where(
            GoalReviewModel.goal_id == goal_id
        ).order_by(GoalReviewModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
