"""Reflection API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class ReflectionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    reflection_type: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    status: str = "completed"
    created_at: datetime


class ReflectionListResponse(BaseModel):
    data: list[ReflectionResponse]
    total: int
    has_more: bool = False


class TriggerReflectionRequest(BaseModel):
    period_start: datetime | None = None
    period_end: datetime | None = None
    focus_areas: list[str] = Field(default_factory=list)


@router.get("/", response_model=ReflectionListResponse)
async def list_reflections(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.get("/{reflection_id}", response_model=ReflectionResponse)
async def get_reflection(reflection_id: str, user: Any = None) -> dict:
    return {
        "id": reflection_id,
        "user_id": getattr(user, "id", "anon"),
        "title": "",
        "content": "",
        "reflection_type": "weekly",
        "status": "completed",
        "created_at": datetime.utcnow(),
    }


@router.post("/", response_model=ReflectionResponse, status_code=202)
async def trigger_reflection(body: TriggerReflectionRequest, user: Any = None) -> dict:
    reflection_id = str(uuid.uuid4())
    return {
        "id": reflection_id,
        "user_id": getattr(user, "id", "anon"),
        "title": "",
        "content": "",
        "reflection_type": "on_demand",
        "status": "processing",
        "created_at": datetime.utcnow(),
    }
