"""Book repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload

from ayeneh.infrastructure.persistence.models.book import BookModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BookRepositoryImpl(SQLAlchemyBaseRepository):
    """Book repository with chapter loading."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BookModel)

    async def get_with_chapters(self, book_id: object) -> BookModel | None:
        stmt = self._base_query().where(
            BookModel.id == book_id
        ).options(selectinload(BookModel.chapters))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
