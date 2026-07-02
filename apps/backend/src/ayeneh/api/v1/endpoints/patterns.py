"""Pattern API endpoints — wired to database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from ayeneh.api.deps import get_container
from ayeneh.infrastructure.persistence.models.pattern import PatternModel

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


class CreatePatternRequest(BaseModel):
    description: str
    strength: float = 0.5
    evidence_count: int = 0


@router.get("/", response_model=PatternListResponse)
async def list_patterns(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    pattern_type: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(PatternModel)
            .where(PatternModel.deleted_at.is_(None))
            .order_by(PatternModel.created_at.desc())
            .limit(limit)
        )
        patterns = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(p.id),
                    "user_id": str(p.user_id),
                    "name": p.description[:50] if p.description else "",
                    "description": p.description,
                    "pattern_type": "cognitive",
                    "confidence": p.strength,
                    "evidence_count": p.evidence_count,
                    "status": p.status,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in patterns
            ],
            "total": len(patterns),
            "has_more": False,
        }


@router.post("/", response_model=PatternResponse, status_code=201)
async def create_pattern(body: CreatePatternRequest, user: Any = None) -> dict:
    container = get_container()
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if container.database:
        async with container.database.session_factory() as session:
            pattern = PatternModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                description=body.description,
                strength=body.strength,
                evidence_count=body.evidence_count,
                status="active",
                first_detected_at=now,
            )
            session.add(pattern)
            await session.commit()

            return {
                "id": str(pattern.id),
                "user_id": user_id,
                "name": pattern.description[:50],
                "description": pattern.description,
                "pattern_type": "cognitive",
                "confidence": pattern.strength,
                "evidence_count": pattern.evidence_count,
                "status": pattern.status,
                "created_at": pattern.created_at,
                "updated_at": pattern.updated_at,
            }

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": body.description[:50],
        "description": body.description,
        "pattern_type": "cognitive",
        "confidence": body.strength,
        "evidence_count": body.evidence_count,
        "status": "active",
        "created_at": now,
    }


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(pattern_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": pattern_id,
            "user_id": "anon",
            "name": "",
            "description": "",
            "pattern_type": "cognitive",
            "confidence": 0.0,
            "evidence_count": 0,
            "status": "active",
            "created_at": datetime.now(UTC),
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(PatternModel).where(PatternModel.id == uuid.UUID(pattern_id))
        )
        pattern = result.scalar_one_or_none()

        if not pattern:
            return {
                "id": pattern_id,
                "user_id": "anon",
                "name": "",
                "description": "",
                "pattern_type": "cognitive",
                "confidence": 0.0,
                "evidence_count": 0,
                "status": "active",
                "created_at": datetime.now(UTC),
            }

        return {
            "id": str(pattern.id),
            "user_id": str(pattern.user_id),
            "name": pattern.description[:50],
            "description": pattern.description,
            "pattern_type": "cognitive",
            "confidence": pattern.strength,
            "evidence_count": pattern.evidence_count,
            "status": pattern.status,
            "created_at": pattern.created_at,
            "updated_at": pattern.updated_at,
        }


@router.get("/{pattern_id}/timeline")
async def get_pattern_timeline(pattern_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(PatternModel).where(PatternModel.id == uuid.UUID(pattern_id))
        )
        pattern = result.scalar_one_or_none()

        if not pattern:
            return {"data": [], "total": 0}

        timeline = [
            {
                "date": pattern.first_detected_at.isoformat(),
                "event": "Pattern detected",
                "details": pattern.description,
            }
        ]

        if pattern.updated_at and pattern.updated_at != pattern.first_detected_at:
            timeline.append({
                "date": pattern.updated_at.isoformat(),
                "event": "Pattern updated",
                "details": f"Strength: {pattern.strength}",
            })

        return {"data": timeline, "total": len(timeline)}
