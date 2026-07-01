"""EpistemicProfile repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.epistemic_profile import EpistemicProfileModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class EpistemicProfileRepositoryImpl(SQLAlchemyBaseRepository):
    """Epistemic profile repository with domain-specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EpistemicProfileModel)

    async def get_by_book_id(self, book_id: Any) -> EpistemicProfileModel | None:
        stmt = self._base_query().where(EpistemicProfileModel.book_id == book_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: Any) -> Sequence[EpistemicProfileModel]:
        stmt = self._base_query().where(EpistemicProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_domain(self, user_id: Any, domain: str) -> Sequence[EpistemicProfileModel]:
        stmt = self._base_query().where(
            EpistemicProfileModel.user_id == user_id,
            EpistemicProfileModel.discipline == domain,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
