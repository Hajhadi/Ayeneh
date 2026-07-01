"""Reflection service — persists longitudinal reflections."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.infrastructure.persistence.models.reflection import ReflectionModel

logger = structlog.get_logger(__name__)


class ReflectionService:
    """Handles reflection persistence from ReflectionAgent outputs."""

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def create_reflection(
        self,
        user_id: str,
        title: str,
        narrative: str,
        period_start: datetime,
        period_end: datetime,
        evidence_snapshot: list[dict] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            reflection = ReflectionModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                title=title,
                narrative=narrative,
                period_start=period_start,
                period_end=period_end,
                status="published",
                evidence_snapshot=evidence_snapshot or [],
                created_at=now,
            )
            await uow.reflections.create(reflection)
            await uow.commit()
            return {
                "id": str(reflection.id),
                "title": reflection.title,
                "status": reflection.status,
            }

    async def list_reflections(
        self, user_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            refs = await uow.reflections.list_by_user(uuid.UUID(user_id), limit=limit)
            return [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "narrative": r.narrative,
                    "period_start": r.period_start.isoformat(),
                    "period_end": r.period_end.isoformat(),
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in refs
            ]

    async def get_reflection(self, reflection_id: str) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            r = await uow.reflections.get_by_id(uuid.UUID(reflection_id))
            if r is None:
                return None
            return {
                "id": str(r.id),
                "title": r.title,
                "narrative": r.narrative,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }

    async def count_reflections(self, user_id: str) -> int:
        async with self._uow_factory() as uow:
            return await uow.reflections.count(filters={"user_id": uuid.UUID(user_id)})
