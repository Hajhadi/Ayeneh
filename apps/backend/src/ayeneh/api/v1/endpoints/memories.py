"""Memory API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

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


@router.get("/", response_model=MemoryListResponse)
async def list_memories(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    memory_type: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.post("/search", response_model=SearchResponse)
async def search_memories(body: SearchRequest, user: Any = None) -> dict:
    return {"data": [], "total": 0}


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str, user: Any = None) -> dict:
    return {
        "id": memory_id,
        "user_id": getattr(user, "id", "anon"),
        "memory_type": "semantic",
        "content": "",
        "status": "active",
        "created_at": datetime.utcnow(),
    }


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, user: Any = None) -> None:
    pass


@router.post("/{memory_id}/archive")
async def archive_memory(memory_id: str, user: Any = None) -> dict:
    return {"id": memory_id, "status": "archived"}
