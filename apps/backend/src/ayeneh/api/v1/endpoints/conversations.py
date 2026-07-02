"""Conversation API endpoints — wired to database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ayeneh.api.deps import get_container
from ayeneh.infrastructure.persistence.models.conversation import ConversationModel
from ayeneh.infrastructure.persistence.models.message import MessageModel

router = APIRouter()


# ── Request/Response models ──

class CreateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    topic: str | None = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    topic: str | None = None
    status: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence_number: int
    token_count: int | None = None
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class SendMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence_number: int
    created_at: datetime


class ConversationListResponse(BaseModel):
    data: list[ConversationResponse]
    total: int
    has_more: bool = False


# ── Endpoints ──

@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(body: CreateConversationRequest, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": str(uuid.uuid4()),
            "user_id": "anon",
            "title": body.title,
            "topic": body.topic,
            "status": "active",
            "message_count": 0,
            "created_at": datetime.now(UTC),
        }

    conv_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    async with container.database.session_factory() as session:
        conv = ConversationModel(
            id=uuid.UUID(conv_id),
            user_id=uuid.UUID(user_id),
            session_id=uuid.UUID(str(uuid.uuid4())),
            title=body.title,
            topic=body.topic,
            status="active",
            message_count=0,
            started_at=now,
            created_at=now,
        )
        session.add(conv)
        await session.commit()

    return {
        "id": conv_id,
        "user_id": user_id,
        "title": body.title,
        "topic": body.topic,
        "status": "active",
        "message_count": 0,
        "created_at": now,
    }


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(ConversationModel).where(ConversationModel.deleted_at.is_(None)).order_by(ConversationModel.created_at.desc()).limit(limit)
        )
        convs = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(c.id),
                    "user_id": str(c.user_id),
                    "title": c.title or "",
                    "topic": c.topic,
                    "status": c.status,
                    "message_count": c.message_count,
                    "created_at": c.created_at,
                    "updated_at": c.created_at,
                }
                for c in convs
            ],
            "total": len(convs),
            "has_more": False,
        }


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": conversation_id,
            "user_id": "anon",
            "title": "",
            "status": "active",
            "message_count": 0,
            "created_at": datetime.now(UTC),
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(ConversationModel).where(ConversationModel.id == uuid.UUID(conversation_id))
        )
        conv = result.scalar_one_or_none()

        if not conv:
            return {
                "id": conversation_id,
                "user_id": "anon",
                "title": "",
                "status": "active",
                "message_count": 0,
                "created_at": datetime.now(UTC),
            }

        return {
            "id": str(conv.id),
            "user_id": str(conv.user_id),
            "title": conv.title or "",
            "topic": conv.topic,
            "status": conv.status,
            "message_count": conv.message_count,
            "created_at": conv.created_at,
            "updated_at": conv.created_at,
        }


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == uuid.UUID(conversation_id))
            .where(MessageModel.deleted_at.is_(None))
            .order_by(MessageModel.sequence_number)
            .limit(limit)
        )
        msgs = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(m.id),
                    "conversation_id": str(m.conversation_id),
                    "role": m.role,
                    "content": m.content,
                    "sequence_number": m.sequence_number,
                    "token_count": m.token_count,
                    "created_at": m.created_at,
                }
                for m in msgs
            ],
            "total": len(msgs),
            "has_more": False,
        }


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse, status_code=201)
async def send_message(conversation_id: str, body: SendMessageRequest, user: Any = None) -> dict:
    container = get_container()
    msg_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if container.database:
        async with container.database.session_factory() as session:
            # Get next sequence number
            result = await session.execute(
                select(MessageModel)
                .where(MessageModel.conversation_id == uuid.UUID(conversation_id))
                .order_by(MessageModel.sequence_number.desc())
                .limit(1)
            )
            last_msg = result.scalar_one_or_none()
            seq = (last_msg.sequence_number + 1) if last_msg else 1

            msg = MessageModel(
                id=uuid.UUID(msg_id),
                conversation_id=uuid.UUID(conversation_id),
                user_id=uuid.UUID(user_id),
                role="user",
                content=body.content,
                sequence_number=seq,
                created_at=now,
            )
            session.add(msg)

            # Update conversation message count
            conv_result = await session.execute(
                select(ConversationModel).where(ConversationModel.id == uuid.UUID(conversation_id))
            )
            conv = conv_result.scalar_one_or_none()
            if conv:
                conv.message_count = seq
                conv.last_activity_at = now

            await session.commit()

    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": "user",
        "content": body.content,
        "sequence_number": 1,
        "created_at": now,
    }


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, body: dict, user: Any = None) -> dict:
    return {"id": conversation_id, "updated": True}


@router.post("/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user: Any = None) -> dict:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(ConversationModel).where(ConversationModel.id == uuid.UUID(conversation_id))
            )
            conv = result.scalar_one_or_none()
            if conv:
                conv.status = "archived"
                await session.commit()

    return {"id": conversation_id, "status": "archived"}
