"""User repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UserRepositoryImpl(SQLAlchemyBaseRepository):
    """User repository with email lookup."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = self._base_query().where(UserModel.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
