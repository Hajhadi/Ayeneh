"""Pattern repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.pattern import PatternModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class PatternRepositoryImpl(SQLAlchemyBaseRepository):
    """Pattern repository with user-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PatternModel)

    async def list_by_user(
        self, user_id: uuid.UUID, *, status: str | None = None, limit: int = 100
    ) -> list[PatternModel]:
        stmt = self._base_query().where(PatternModel.user_id == user_id)
        if status:
            stmt = stmt.where(PatternModel.status == status)
        stmt = stmt.order_by(PatternModel.first_detected_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_active_by_description(
        self, user_id: uuid.UUID, description: str
    ) -> PatternModel | None:
        stmt = self._base_query().where(
            PatternModel.user_id == user_id,
            PatternModel.description == description,
            PatternModel.status == "active",
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
