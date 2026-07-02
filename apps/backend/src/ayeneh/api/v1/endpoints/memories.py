"""Memory API endpoints — wired to database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ayeneh.api.deps import get_container
from ayeneh.infrastructure.persistence.models.memory import MemoryModel

router = APIRouter()


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    memory_type: str
    content: str
    source_message_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    status: str = "active"
    created_at: datetime
    updated_at: datetime | None = None


class MemoryListResponse(BaseModel):
    data: list[MemoryResponse]
    total: int
    has_more: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    memory_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    id: str
    content: str
    memory_type: str
    score: float
    source_message_ids: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    data: list[SearchResultItem]
    total: int


class CreateMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    memory_type: str = "semantic"
    confidence: float = 0.5


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    memory_type: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        query = select(MemoryModel).where(MemoryModel.deleted_at.is_(None))
        if memory_type:
            query = query.where(MemoryModel.type == memory_type)
        query = query.order_by(MemoryModel.created_at.desc()).limit(limit)

        result = await session.execute(query)
        memories = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(m.id),
                    "user_id": str(m.user_id),
                    "memory_type": m.type,
                    "content": m.content,
                    "source_message_ids": [str(s) for s in (m.source_message_ids or [])],
                    "confidence": m.confidence,
                    "status": m.status,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                }
                for m in memories
            ],
            "total": len(memories),
            "has_more": False,
        }


@router.post("/", response_model=MemoryResponse, status_code=201)
async def create_memory(body: CreateMemoryRequest, user: Any = None) -> dict:
    container = get_container()
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if container.database:
        async with container.database.session_factory() as session:
            memory = MemoryModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                type=body.memory_type,
                content=body.content,
                confidence=body.confidence,
                source_message_ids=[],
                status="active",
                embedding_version=0,
                evolution_version=1,
            )
            session.add(memory)
            await session.commit()

            return {
                "id": str(memory.id),
                "user_id": user_id,
                "memory_type": memory.type,
                "content": memory.content,
                "source_message_ids": [],
                "confidence": memory.confidence,
                "status": memory.status,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "memory_type": body.memory_type,
        "content": body.content,
        "confidence": body.confidence,
        "status": "active",
        "created_at": now,
    }


@router.post("/search", response_model=SearchResponse)
async def search_memories(body: SearchRequest, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    async with container.database.session_factory() as session:
        query = select(MemoryModel).where(MemoryModel.deleted_at.is_(None))
        if body.memory_type:
            query = query.where(MemoryModel.type == body.memory_type)
        query = query.where(MemoryModel.content.contains(body.query)).limit(body.limit)

        result = await session.execute(query)
        memories = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(m.id),
                    "content": m.content,
                    "memory_type": m.type,
                    "score": m.confidence,
                    "source_message_ids": [str(s) for s in (m.source_message_ids or [])],
                }
                for m in memories
            ],
            "total": len(memories),
        }


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": memory_id,
            "user_id": "anon",
            "memory_type": "semantic",
            "content": "",
            "status": "active",
            "created_at": datetime.now(UTC),
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(MemoryModel).where(MemoryModel.id == uuid.UUID(memory_id))
        )
        memory = result.scalar_one_or_none()

        if not memory:
            return {
                "id": memory_id,
                "user_id": "anon",
                "memory_type": "semantic",
                "content": "",
                "status": "active",
                "created_at": datetime.now(UTC),
            }

        return {
            "id": str(memory.id),
            "user_id": str(memory.user_id),
            "memory_type": memory.type,
            "content": memory.content,
            "source_message_ids": [str(s) for s in (memory.source_message_ids or [])],
            "confidence": memory.confidence,
            "status": memory.status,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
        }


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, user: Any = None) -> None:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(MemoryModel).where(MemoryModel.id == uuid.UUID(memory_id))
            )
            memory = result.scalar_one_or_none()
            if memory:
                memory.deleted_at = datetime.now(UTC)
                await session.commit()


@router.post("/{memory_id}/archive")
async def archive_memory(memory_id: str, user: Any = None) -> dict:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(MemoryModel).where(MemoryModel.id == uuid.UUID(memory_id))
            )
            memory = result.scalar_one_or_none()
            if memory:
                memory.status = "archived"
                await session.commit()

    return {"id": memory_id, "status": "archived"}
