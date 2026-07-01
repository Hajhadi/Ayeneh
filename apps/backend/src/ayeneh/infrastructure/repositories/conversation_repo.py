"""Conversation repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.conversation import ConversationModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class ConversationRepositoryImpl(SQLAlchemyBaseRepository):
    """Conversation repository with active conversation lookup."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ConversationModel)

    async def get_active_by_user(self, user_id: uuid.UUID) -> ConversationModel | None:
        stmt = self._base_query().where(
            ConversationModel.user_id == user_id,
            ConversationModel.status == "active",
        ).order_by(ConversationModel.started_at.desc())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
