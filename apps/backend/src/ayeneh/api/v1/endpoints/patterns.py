"""Pattern API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class PatternResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    pattern_type: str
    confidence: float
    evidence_count: int
    status: str = "active"
    created_at: datetime
    updated_at: datetime | None = None


class PatternListResponse(BaseModel):
    data: list[PatternResponse]
    total: int
    has_more: bool = False


class PatternTimelineItem(BaseModel):
    date: datetime
    event: str
    details: str


@router.get("/", response_model=PatternListResponse)
async def list_patterns(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    pattern_type: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(pattern_id: str, user: Any = None) -> dict:
    return {
        "id": pattern_id,
        "user_id": getattr(user, "id", "anon"),
        "name": "",
        "description": "",
        "pattern_type": "cognitive",
        "confidence": 0.0,
        "evidence_count": 0,
        "status": "active",
        "created_at": datetime.utcnow(),
    }


@router.get("/{pattern_id}/timeline")
async def get_pattern_timeline(pattern_id: str, user: Any = None) -> dict:
    return {"data": [], "total": 0}
