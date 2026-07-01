"""Observation repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.observation import ObservationModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class ObservationRepositoryImpl(SQLAlchemyBaseRepository):
    """Observation repository with user-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ObservationModel)

    async def list_by_user(
        self, user_id: uuid.UUID, *, status: str | None = None, limit: int = 100
    ) -> list[ObservationModel]:
        stmt = self._base_query().where(ObservationModel.user_id == user_id)
        if status:
            stmt = stmt.where(ObservationModel.status == status)
        stmt = stmt.order_by(ObservationModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
