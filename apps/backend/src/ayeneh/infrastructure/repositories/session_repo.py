"""Session repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.session import SessionModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SessionRepositoryImpl(SQLAlchemyBaseRepository):
    """Session repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SessionModel)
