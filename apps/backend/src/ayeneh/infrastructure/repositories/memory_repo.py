"""Memory repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.memory import MemoryModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class MemoryRepositoryImpl(SQLAlchemyBaseRepository):
    """Memory repository with type-based queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryModel)

    async def list_by_type(self, user_id: uuid.UUID, memory_type: str) -> list[MemoryModel]:
        stmt = self._base_query().where(
            MemoryModel.user_id == user_id,
            MemoryModel.type == memory_type,
        ).order_by(MemoryModel.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
