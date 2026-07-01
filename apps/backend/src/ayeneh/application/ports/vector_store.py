"""Vector store port — abstract contract for vector storage and retrieval."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SimilarityMetric(StrEnum):
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "inner_product"


@dataclass
class VectorRecord:
    """A single vector record stored in the vector store."""

    id: str
    entity_id: str
    entity_type: str
    embedding: list[float]
    model_version: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single similarity search result."""

    record: VectorRecord
    score: float


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    async def upsert(self, record: VectorRecord) -> None:
        """Insert or update a vector record."""

    @abstractmethod
    async def upsert_batch(self, records: list[VectorRecord]) -> None:
        """Insert or update multiple vector records."""

    @abstractmethod
    async def get_by_entity(self, entity_id: str, entity_type: str) -> VectorRecord | None:
        """Retrieve a vector record by entity reference."""

    @abstractmethod
    async def delete(self, record_id: str) -> None:
        """Delete a vector record by ID."""

    @abstractmethod
    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        """Delete a vector record by entity reference."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        *,
        entity_type: str | None = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors."""

    @abstractmethod
    async def count(self, entity_type: str | None = None) -> int:
        """Count stored vectors, optionally filtered by entity type."""
