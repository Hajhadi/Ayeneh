"""pgvector vector store — concrete implementation using pgvector."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import delete, func, select, text

from ayeneh.application.ports.vector_store import (
    SearchResult,
    SimilarityMetric,
    VectorRecord,
    VectorStore,
)
from ayeneh.infrastructure.persistence.models.embedding import EmbeddingModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

_METRIC_OP = {
    SimilarityMetric.COSINE: "<=>",
    SimilarityMetric.L2: "<->",
    SimilarityMetric.INNER_PRODUCT: "<#>",
}


class PgVectorStore(VectorStore):
    """Vector store backed by PostgreSQL with pgvector."""

    def __init__(self, session_factory: callable) -> None:
        self._session_factory = session_factory

    def _to_record(self, model: EmbeddingModel) -> VectorRecord:
        return VectorRecord(
            id=str(model.id),
            entity_id=str(model.entity_id),
            entity_type=model.entity_type,
            embedding=model.embedding,
            model_version=model.model_version,
        )

    async def upsert(self, record: VectorRecord) -> None:
        async with self._session_factory() as session:
            existing = await self._get_existing(session, record.entity_id, record.entity_type)
            if existing:
                existing.embedding = record.embedding
                existing.model_version = record.model_version
                logger.debug("vector_upsert_update", entity_id=record.entity_id)
            else:
                model = EmbeddingModel(
                    id=uuid.uuid4(),
                    entity_id=uuid.UUID(record.entity_id),
                    entity_type=record.entity_type,
                    embedding=record.embedding,
                    model_version=record.model_version,
                    created_at=datetime.now(UTC),
                )
                session.add(model)
                logger.debug("vector_upsert_insert", entity_id=record.entity_id)
            await session.commit()

    async def upsert_batch(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        async with self._session_factory() as session:
            for record in records:
                existing = await self._get_existing(session, record.entity_id, record.entity_type)
                if existing:
                    existing.embedding = record.embedding
                    existing.model_version = record.model_version
                else:
                    model = EmbeddingModel(
                        id=uuid.uuid4(),
                        entity_id=uuid.UUID(record.entity_id),
                        entity_type=record.entity_type,
                        embedding=record.embedding,
                        model_version=record.model_version,
                        created_at=datetime.now(UTC),
                    )
                    session.add(model)
            await session.commit()
            logger.debug("vector_upsert_batch", count=len(records))

    async def _get_existing(
        self, session: AsyncSession, entity_id: str, entity_type: str
    ) -> EmbeddingModel | None:
        stmt = select(EmbeddingModel).where(
            EmbeddingModel.entity_id == uuid.UUID(entity_id),
            EmbeddingModel.entity_type == entity_type,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_entity(self, entity_id: str, entity_type: str) -> VectorRecord | None:
        async with self._session_factory() as session:
            stmt = select(EmbeddingModel).where(
                EmbeddingModel.entity_id == uuid.UUID(entity_id),
                EmbeddingModel.entity_type == entity_type,
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._to_record(model) if model else None

    async def delete(self, record_id: str) -> None:
        async with self._session_factory() as session:
            stmt = delete(EmbeddingModel).where(EmbeddingModel.id == uuid.UUID(record_id))
            await session.execute(stmt)
            await session.commit()
            logger.debug("vector_delete", record_id=record_id)

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        async with self._session_factory() as session:
            stmt = delete(EmbeddingModel).where(
                EmbeddingModel.entity_id == uuid.UUID(entity_id),
                EmbeddingModel.entity_type == entity_type,
            )
            await session.execute(stmt)
            await session.commit()
            logger.debug("vector_delete_by_entity", entity_id=entity_id, entity_type=entity_type)

    async def search(
        self,
        query_embedding: list[float],
        *,
        entity_type: str | None = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        async with self._session_factory() as session:
            op = _METRIC_OP[metric]
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            query = f"""
                SELECT id, entity_id, entity_type, model_version,
                       1.0 - (embedding {op} :query_vec::vector) as score
                FROM embeddings
            """
            params: dict[str, object] = {"query_vec": embedding_str, "limit": limit}

            conditions: list[str] = []
            if entity_type:
                conditions.append("entity_type = :entity_type")
                params["entity_type"] = entity_type

            if filters:
                for key, value in filters.items():
                    conditions.append(f"entity_{key} = :filter_{key}")
                    params[f"filter_{key}"] = value

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            if metric == SimilarityMetric.COSINE:
                query += " AND (1.0 - (embedding {op} :query_vec::vector)) >= :threshold"
            elif metric == SimilarityMetric.INNER_PRODUCT:
                query += " AND (embedding {op} :query_vec::vector) >= :threshold"
            else:
                query += " AND (embedding {op} :query_vec::vector) <= :threshold"

            params["threshold"] = score_threshold
            query += " ORDER BY score DESC LIMIT :limit"

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [
                SearchResult(
                    record=VectorRecord(
                        id=str(row.id),
                        entity_id=str(row.entity_id),
                        entity_type=row.entity_type,
                        embedding=[],
                        model_version=row.model_version,
                    ),
                    score=float(row.score),
                )
                for row in rows
            ]

    async def count(self, entity_type: str | None = None) -> int:
        async with self._session_factory() as session:
            stmt = select(func.count()).select_from(EmbeddingModel)
            if entity_type:
                stmt = stmt.where(EmbeddingModel.entity_type == entity_type)
            result = await session.execute(stmt)
            return result.scalar_one()
