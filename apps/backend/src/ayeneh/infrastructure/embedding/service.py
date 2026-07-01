"""Embedding service — coordinates embedding generation, storage, and retrieval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.application.ports.vector_store import (
    SearchResult,
    SimilarityMetric,
    VectorRecord,
    VectorStore,
)

if TYPE_CHECKING:
    from ayeneh.application.ports.embedding import EmbeddingProvider

logger = structlog.get_logger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding service."""

    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    current_model_version: int = 1
    batch_size: int = 100


@dataclass
class EmbeddingService:
    """Coordinates embedding generation, storage, and similarity search.

    This service owns no business logic — it is a pure infrastructure capability
    that other services (MemoryService, LibraryService) consume.
    """

    provider: EmbeddingProvider
    vector_store: VectorStore
    config: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    async def embed_and_store(
        self,
        entity_id: uuid.UUID,
        entity_type: str,
        text: str,
    ) -> VectorRecord:
        """Embed a single text and store the resulting vector."""
        embedding = await self.provider.embed(text)
        record = VectorRecord(
            id=str(uuid.uuid4()),
            entity_id=str(entity_id),
            entity_type=entity_type,
            embedding=embedding,
            model_version=self.config.current_model_version,
        )
        await self.vector_store.upsert(record)
        logger.info("embedding_stored", entity_id=str(entity_id), entity_type=entity_type)
        return record

    async def embed_and_store_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[VectorRecord]:
        """Embed and store multiple items in batch.

        Each item dict must contain: entity_id, entity_type, text.
        """
        if not items:
            return []

        texts = [item["text"] for item in items]
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i : i + self.config.batch_size]
            batch_embeddings = await self.provider.embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        records: list[VectorRecord] = []
        for item, embedding in zip(items, all_embeddings, strict=False):
            record = VectorRecord(
                id=str(uuid.uuid4()),
                entity_id=str(item["entity_id"]),
                entity_type=item["entity_type"],
                embedding=embedding,
                model_version=self.config.current_model_version,
            )
            records.append(record)

        await self.vector_store.upsert_batch(records)
        logger.info("embedding_batch_stored", count=len(records))
        return records

    async def search(
        self,
        query: str,
        *,
        entity_type: str | None = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors by text query."""
        query_embedding = await self.provider.embed(query)
        return await self.vector_store.search(
            query_embedding,
            entity_type=entity_type,
            metric=metric,
            limit=limit,
            score_threshold=score_threshold,
            filters=filters,
        )

    async def search_by_vector(
        self,
        query_embedding: list[float],
        *,
        entity_type: str | None = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors by pre-computed embedding."""
        return await self.vector_store.search(
            query_embedding,
            entity_type=entity_type,
            metric=metric,
            limit=limit,
            score_threshold=score_threshold,
            filters=filters,
        )

    async def get_embedding(self, entity_id: uuid.UUID, entity_type: str) -> VectorRecord | None:
        """Retrieve a stored embedding by entity reference."""
        return await self.vector_store.get_by_entity(str(entity_id), entity_type)

    async def delete_embedding(self, entity_id: uuid.UUID, entity_type: str) -> None:
        """Delete a stored embedding by entity reference."""
        await self.vector_store.delete_by_entity(str(entity_id), entity_type)
        logger.info("embedding_deleted", entity_id=str(entity_id), entity_type=entity_type)

    async def needs_reembedding(self, entity_id: uuid.UUID, entity_type: str) -> bool:
        """Check if an entity's embedding is stale and needs regeneration."""
        record = await self.vector_store.get_by_entity(str(entity_id), entity_type)
        if record is None:
            return True
        return record.model_version < self.config.current_model_version

    async def reembed(
        self,
        entity_id: uuid.UUID,
        entity_type: str,
        text: str,
    ) -> VectorRecord:
        """Re-embed an entity with the current model version."""
        await self.vector_store.delete_by_entity(str(entity_id), entity_type)
        return await self.embed_and_store(entity_id, entity_type, text)

    async def reembed_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[VectorRecord]:
        """Re-embed multiple entities with the current model version."""
        for item in items:
            await self.vector_store.delete_by_entity(
                str(item["entity_id"]), item["entity_type"]
            )
        return await self.embed_and_store_batch(items)

    async def count(self, entity_type: str | None = None) -> int:
        """Count stored embeddings."""
        return await self.vector_store.count(entity_type)
