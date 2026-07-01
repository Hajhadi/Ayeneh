"""Agent run repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.agent_run import AgentRunModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class AgentRunRepositoryImpl(SQLAlchemyBaseRepository):
    """Agent run repository with plan-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentRunModel)

    async def list_by_plan(self, plan_id: uuid.UUID) -> list[AgentRunModel]:
        stmt = select(AgentRunModel).where(
            AgentRunModel.plan_id == plan_id
        ).order_by(AgentRunModel.created_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
