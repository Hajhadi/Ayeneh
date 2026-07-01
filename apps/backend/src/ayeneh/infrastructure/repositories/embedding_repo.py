"""Embedding repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.embedding import EmbeddingModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class EmbeddingRepositoryImpl(SQLAlchemyBaseRepository):
    """Embedding repository for vector storage."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmbeddingModel)

    async def get_by_entity(self, entity_id: uuid.UUID, entity_type: str) -> EmbeddingModel | None:
        stmt = select(EmbeddingModel).where(
            EmbeddingModel.entity_id == entity_id,
            EmbeddingModel.entity_type == entity_type,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
