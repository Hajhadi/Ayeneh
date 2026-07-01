"""Conversation API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

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
    conv_id = str(uuid.uuid4())
    return {
        "id": conv_id,
        "user_id": getattr(user, "id", "anon"),
        "title": body.title,
        "topic": body.topic,
        "status": "active",
        "message_count": 0,
        "created_at": datetime.utcnow(),
    }


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, user: Any = None) -> dict:
    return {
        "id": conversation_id,
        "user_id": getattr(user, "id", "anon"),
        "title": "",
        "status": "active",
        "message_count": 0,
        "created_at": datetime.utcnow(),
    }


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse, status_code=201)
async def send_message(conversation_id: str, body: SendMessageRequest, user: Any = None) -> dict:
    msg_id = str(uuid.uuid4())
    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "role": "user",
        "content": body.content,
        "sequence_number": 1,
        "created_at": datetime.utcnow(),
    }


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, body: dict, user: Any = None) -> dict:
    return {"id": conversation_id, "updated": True}


@router.post("/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, user: Any = None) -> dict:
    return {"id": conversation_id, "status": "archived"}
