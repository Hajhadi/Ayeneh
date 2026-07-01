"""Message repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.message import MessageModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class MessageRepositoryImpl(SQLAlchemyBaseRepository):
    """Message repository with conversation-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MessageModel)

    async def list_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 50
    ) -> list[MessageModel]:
        stmt = self._base_query().where(
            MessageModel.conversation_id == conversation_id
        ).order_by(MessageModel.sequence_number).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
