"""Memory evolution repository — persists evolution events and lineage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.memory_evolution import (
    MemoryEvolutionEventModel,
    MemoryLineageModel,
)
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class MemoryEvolutionEventRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryEvolutionEventModel)

    async def list_by_memory(self, memory_id: uuid.UUID, limit: int = 100) -> list[MemoryEvolutionEventModel]:
        stmt = self._base_query().where(
            MemoryEvolutionEventModel.memory_id == memory_id
        ).order_by(MemoryEvolutionEventModel.created_at).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(self, user_id: uuid.UUID, *, limit: int = 100) -> list[MemoryEvolutionEventModel]:
        stmt = self._base_query().where(
            MemoryEvolutionEventModel.user_id == user_id
        ).order_by(MemoryEvolutionEventModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(self, user_id: uuid.UUID, event_type: str) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(MemoryEvolutionEventModel).where(
            MemoryEvolutionEventModel.user_id == user_id,
            MemoryEvolutionEventModel.event_type == event_type,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()


class MemoryLineageRepositoryImpl(SQLAlchemyBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryLineageModel)

    async def get_children(self, parent_id: uuid.UUID) -> list[MemoryLineageModel]:
        stmt = self._base_query().where(MemoryLineageModel.parent_id == parent_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_parents(self, child_id: uuid.UUID) -> list[MemoryLineageModel]:
        stmt = self._base_query().where(MemoryLineageModel.child_id == child_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_relation(self, parent_id: uuid.UUID, child_id: uuid.UUID) -> MemoryLineageModel | None:
        stmt = self._base_query().where(
            MemoryLineageModel.parent_id == parent_id,
            MemoryLineageModel.child_id == child_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
