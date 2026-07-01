"""Conversation service — manages conversations and messages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.infrastructure.persistence.models.conversation import ConversationModel
from ayeneh.infrastructure.persistence.models.message import MessageModel

logger = structlog.get_logger(__name__)


class ConversationService:
    """Handles conversation lifecycle and message storage.

    All persistence goes through the UnitOfWork, never directly to repositories.
    """

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def create_conversation(
        self,
        user_id: str,
        session_id: str,
        title: str = "",
        topic: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            conv = ConversationModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                session_id=uuid.UUID(session_id),
                title=title,
                topic=topic,
                status="active",
                message_count=0,
                started_at=now,
                created_at=now,
            )
            await uow.conversations.create(conv)
            await uow.commit()
            return {
                "id": str(conv.id),
                "user_id": str(conv.user_id),
                "title": conv.title,
                "topic": conv.topic,
                "status": conv.status,
                "message_count": conv.message_count,
                "created_at": conv.created_at.isoformat(),
            }

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(uuid.UUID(conversation_id))
            if conv is None:
                return None
            return {
                "id": str(conv.id),
                "user_id": str(conv.user_id),
                "title": conv.title,
                "topic": conv.topic,
                "status": conv.status,
                "message_count": conv.message_count,
                "created_at": conv.created_at.isoformat(),
            }

    async def list_conversations(
        self, user_id: str, *, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            convs = await uow.conversations.list(
                filters={"user_id": uuid.UUID(user_id), "status": "active"},
                limit=limit,
                offset=offset,
            )
            return [
                {
                    "id": str(c.id),
                    "user_id": str(c.user_id),
                    "title": c.title,
                    "topic": c.topic,
                    "status": c.status,
                    "message_count": c.message_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in convs
            ]

    async def count_conversations(self, user_id: str) -> int:
        async with self._uow_factory() as uow:
            return await uow.conversations.count(
                filters={"user_id": uuid.UUID(user_id), "status": "active"}
            )

    async def create_message(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        role: str = "user",
        token_count: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(uuid.UUID(conversation_id))
            if conv is None:
                raise ValueError(f"Conversation {conversation_id} not found")

            seq = conv.message_count + 1
            msg = MessageModel(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(conversation_id),
                user_id=uuid.UUID(user_id),
                role=role,
                content=content,
                sequence_number=seq,
                token_count=token_count,
                created_at=now,
            )
            await uow.messages.create(msg)

            conv.message_count = seq
            conv.last_activity_at = now
            await uow.conversations.update(conv)
            await uow.commit()

            return {
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "role": msg.role,
                "content": msg.content,
                "sequence_number": msg.sequence_number,
                "token_count": msg.token_count,
                "created_at": msg.created_at.isoformat(),
            }

    async def get_messages(
        self, conversation_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            msgs = await uow.messages.list_by_conversation(
                uuid.UUID(conversation_id), limit=limit
            )
            return [
                {
                    "id": str(m.id),
                    "conversation_id": str(m.conversation_id),
                    "role": m.role,
                    "content": m.content,
                    "sequence_number": m.sequence_number,
                    "token_count": m.token_count,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ]

    async def archive_conversation(self, conversation_id: str) -> None:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(uuid.UUID(conversation_id))
            if conv:
                conv.status = "archived"
                conv.ended_at = now
                await uow.conversations.update(conv)
                await uow.commit()

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> None:
        async with self._uow_factory() as uow:
            conv = await uow.conversations.get_by_id(uuid.UUID(conversation_id))
            if conv:
                conv.title = title
                await uow.conversations.update(conv)
                await uow.commit()
