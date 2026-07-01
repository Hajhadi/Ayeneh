"""Reflection repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.reflection import ReflectionModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class ReflectionRepositoryImpl(SQLAlchemyBaseRepository):
    """Reflection repository with user-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ReflectionModel)

    async def list_by_user(
        self, user_id: uuid.UUID, *, status: str | None = None, limit: int = 50
    ) -> list[ReflectionModel]:
        stmt = self._base_query().where(ReflectionModel.user_id == user_id)
        if status:
            stmt = stmt.where(ReflectionModel.status == status)
        stmt = stmt.order_by(ReflectionModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
