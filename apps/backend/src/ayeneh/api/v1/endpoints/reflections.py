"""Reflection API endpoints — wired to database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ayeneh.api.deps import get_container
from ayeneh.infrastructure.persistence.models.reflection import ReflectionModel

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


class CreateReflectionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=50000)
    reflection_type: str = "weekly"


@router.get("/", response_model=ReflectionListResponse)
async def list_reflections(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(ReflectionModel)
            .where(ReflectionModel.deleted_at.is_(None))
            .order_by(ReflectionModel.created_at.desc())
            .limit(limit)
        )
        reflections = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(r.id),
                    "user_id": str(r.user_id),
                    "title": r.title,
                    "content": r.narrative,
                    "reflection_type": "weekly",
                    "period_start": r.period_start,
                    "period_end": r.period_end,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in reflections
            ],
            "total": len(reflections),
            "has_more": False,
        }


@router.post("/", response_model=ReflectionResponse, status_code=201)
async def create_reflection(body: CreateReflectionRequest, user: Any = None) -> dict:
    container = get_container()
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if container.database:
        async with container.database.session_factory() as session:
            reflection = ReflectionModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                title=body.title,
                narrative=body.content,
                period_start=now,
                period_end=now,
                status="completed",
                evidence_snapshot=[],
                created_at=now,
            )
            session.add(reflection)
            await session.commit()

            return {
                "id": str(reflection.id),
                "user_id": user_id,
                "title": reflection.title,
                "content": reflection.narrative,
                "reflection_type": body.reflection_type,
                "period_start": reflection.period_start,
                "period_end": reflection.period_end,
                "status": reflection.status,
                "created_at": reflection.created_at,
            }

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": body.title,
        "content": body.content,
        "reflection_type": body.reflection_type,
        "period_start": now,
        "period_end": now,
        "status": "completed",
        "created_at": now,
    }


@router.get("/{reflection_id}", response_model=ReflectionResponse)
async def get_reflection(reflection_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": reflection_id,
            "user_id": "anon",
            "title": "",
            "content": "",
            "reflection_type": "weekly",
            "status": "completed",
            "created_at": datetime.now(UTC),
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(ReflectionModel).where(ReflectionModel.id == uuid.UUID(reflection_id))
        )
        reflection = result.scalar_one_or_none()

        if not reflection:
            return {
                "id": reflection_id,
                "user_id": "anon",
                "title": "",
                "content": "",
                "reflection_type": "weekly",
                "status": "completed",
                "created_at": datetime.now(UTC),
            }

        return {
            "id": str(reflection.id),
            "user_id": str(reflection.user_id),
            "title": reflection.title,
            "content": reflection.narrative,
            "reflection_type": "weekly",
            "period_start": reflection.period_start,
            "period_end": reflection.period_end,
            "status": reflection.status,
            "created_at": reflection.created_at,
        }


@router.delete("/{reflection_id}", status_code=204)
async def delete_reflection(reflection_id: str, user: Any = None) -> None:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(ReflectionModel).where(ReflectionModel.id == uuid.UUID(reflection_id))
            )
            reflection = result.scalar_one_or_none()
            if reflection:
                reflection.deleted_at = datetime.now(UTC)
                await session.commit()
