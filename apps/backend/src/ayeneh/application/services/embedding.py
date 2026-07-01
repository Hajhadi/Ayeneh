"""Application-level EmbeddingService — bridges application needs to infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EmbeddingMetrics:
    total_calls: int = 0
    total_texts: int = 0
    total_dimensions: int = 0
    total_duration_ms: float = 0.0


class EmbeddingService:
    """Application-level embedding facade that wraps the infrastructure EmbeddingService.

    Provides a simplified interface for the ingestion pipeline and retrieval layer.
    """

    def __init__(self, infra_embedding_service: Any) -> None:
        self._infra = infra_embedding_service
        self.metrics = EmbeddingMetrics()

    async def embed(self, text: str) -> list[float]:
        return await self._infra.provider.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._infra.provider.embed_batch(texts)

    async def store(
        self, entity_id: str, entity_type: str, text: str
    ) -> None:
        import uuid
        await self._infra.embed_and_store(
            uuid.UUID(entity_id), entity_type, text
        )
        self.metrics.total_calls += 1
        self.metrics.total_texts += 1

    async def store_batch(
        self, items: list[dict[str, Any]]
    ) -> int:
        records = await self._infra.embed_and_store_batch(items)
        self.metrics.total_texts += len(items)
        return len(records)

    async def search(
        self,
        query: str,
        *,
        entity_type: str | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        return await self._infra.search(
            query,
            entity_type=entity_type,
            limit=limit,
            score_threshold=score_threshold,
            filters=filters,
        )

    async def delete(self, entity_id: str, entity_type: str) -> None:
        import uuid
        await self._infra.delete_embedding(uuid.UUID(entity_id), entity_type)

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_calls": self.metrics.total_calls,
            "total_texts": self.metrics.total_texts,
        }
