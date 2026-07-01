"""Pattern service — persists patterns detected by PatternAgent."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.infrastructure.persistence.models.pattern import PatternModel

logger = structlog.get_logger(__name__)


class PatternService:
    """Handles pattern persistence from PatternAgent outputs."""

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def create_pattern(
        self,
        user_id: str,
        description: str,
        strength: float = 0.5,
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            existing = await uow.patterns.find_active_by_description(
                uuid.UUID(user_id), description
            )
            if existing:
                existing.strength = max(existing.strength, strength)
                existing.evidence_count += len(evidence_ids or [])
                existing.updated_at = now
                await uow.patterns.update(existing)
                await uow.commit()
                return {"id": str(existing.id), "updated": True}

            pattern = PatternModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                description=description,
                strength=strength,
                evidence_count=len(evidence_ids or []),
                status="active",
                first_detected_at=now,
                created_at=now,
                updated_at=now,
            )
            await uow.patterns.create(pattern)
            await uow.commit()
            return {
                "id": str(pattern.id),
                "updated": False,
            }

    async def list_patterns(
        self, user_id: str, *, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            patterns = await uow.patterns.list_by_user(
                uuid.UUID(user_id), status=status, limit=limit
            )
            return [
                {
                    "id": str(p.id),
                    "description": p.description,
                    "strength": p.strength,
                    "evidence_count": p.evidence_count,
                    "status": p.status,
                    "first_detected_at": p.first_detected_at.isoformat(),
                }
                for p in patterns
            ]

    async def get_pattern(self, pattern_id: str) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            p = await uow.patterns.get_by_id(uuid.UUID(pattern_id))
            if p is None:
                return None
            return {
                "id": str(p.id),
                "description": p.description,
                "strength": p.strength,
                "evidence_count": p.evidence_count,
                "status": p.status,
                "first_detected_at": p.first_detected_at.isoformat(),
            }

    async def count_patterns(self, user_id: str) -> int:
        async with self._uow_factory() as uow:
            return await uow.patterns.count(filters={"user_id": uuid.UUID(user_id)})
