"""Blind Spot API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class BlindSpotResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: str
    severity: str
    status: str = "open"
    created_at: datetime


class BlindSpotListResponse(BaseModel):
    data: list[BlindSpotResponse]
    total: int
    has_more: bool = False


@router.get("/", response_model=BlindSpotListResponse)
async def list_blind_spots(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    category: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.get("/{blind_spot_id}", response_model=BlindSpotResponse)
async def get_blind_spot(blind_spot_id: str, user: Any = None) -> dict:
    return {
        "id": blind_spot_id,
        "user_id": getattr(user, "id", "anon"),
        "title": "",
        "description": "",
        "category": "cognitive",
        "severity": "medium",
        "status": "open",
        "created_at": datetime.utcnow(),
    }


@router.post("/analyze", status_code=202)
async def trigger_analysis(user: Any = None) -> dict:
    analysis_id = str(uuid.uuid4())
    return {"id": analysis_id, "status": "processing"}
