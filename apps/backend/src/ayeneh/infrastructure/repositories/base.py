"""Base repository implementation with generic CRUD support."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, func, select

from ayeneh.application.ports.repository import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyBaseRepository(BaseRepository):
    """Generic SQLAlchemy repository with soft-delete awareness."""

    def __init__(self, session: AsyncSession, model_class: type) -> None:
        self._session = session
        self._model = model_class

    def _base_query(self) -> Select:
        """Return a base select with soft-delete filter."""
        stmt = select(self._model)
        if hasattr(self._model, "deleted_at"):
            stmt = stmt.where(self._model.deleted_at.is_(None))
        return stmt

    async def get_by_id(self, entity_id: Any) -> Any | None:
        stmt = self._base_query().where(self._model.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Any]:
        stmt = self._base_query()
        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key):
                    stmt = stmt.where(getattr(self._model, key) == value)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self._model)
        if hasattr(self._model, "deleted_at"):
            stmt = stmt.where(self._model.deleted_at.is_(None))
        if filters:
            for key, value in filters.items():
                if hasattr(self._model, key):
                    stmt = stmt.where(getattr(self._model, key) == value)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, entity: Any) -> Any:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: Any) -> Any:
        await self._session.flush()
        return entity

    async def delete(self, entity_id: Any) -> None:
        if hasattr(self._model, "deleted_at"):
            from datetime import datetime

            stmt = self._model.__table__.update().where(
                self._model.id == entity_id
            ).values(deleted_at=datetime.now(UTC))
            await self._session.execute(stmt)
            await self._session.flush()
