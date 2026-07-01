"""Insight service — persists blind spot observations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.infrastructure.persistence.models.observation import ObservationModel

logger = structlog.get_logger(__name__)


class InsightService:
    """Handles observation persistence from BlindSpotAgent outputs."""

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def create_observation(
        self,
        user_id: str,
        content: str,
        source_agent: str,
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            obs = ObservationModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                content=content,
                source_agent=source_agent,
                evidence_ids=evidence_ids or [],
                status="pending",
                created_at=now,
            )
            await uow.observations.create(obs)
            await uow.commit()
            return {
                "id": str(obs.id),
                "content": obs.content,
                "source_agent": obs.source_agent,
                "status": obs.status,
            }

    async def list_observations(
        self, user_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            obs_list = await uow.observations.list_by_user(uuid.UUID(user_id), limit=limit)
            return [
                {
                    "id": str(o.id),
                    "content": o.content,
                    "source_agent": o.source_agent,
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
                for o in obs_list
            ]

    async def count_observations(self, user_id: str) -> int:
        async with self._uow_factory() as uow:
            return await uow.observations.count(filters={"user_id": uuid.UUID(user_id)})
