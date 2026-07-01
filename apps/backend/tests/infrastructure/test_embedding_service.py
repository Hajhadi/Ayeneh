"""Tests for EmbeddingService — coordination of generation, storage, and search."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.application.ports.embedding import EmbeddingProvider
from ayeneh.application.ports.vector_store import (
    SearchResult,
    SimilarityMetric,
    VectorRecord,
    VectorStore,
)
from ayeneh.infrastructure.embedding.service import EmbeddingConfig, EmbeddingService


class FakeProvider(EmbeddingProvider):
    """Deterministic embedding provider for tests."""

    def __init__(self, dimensions: int = 3) -> None:
        self._dimensions = dimensions
        self.embed_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [float(i) for i in range(self._dimensions)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.extend(texts)
        return [[float(i) for i in range(self._dimensions)] for _ in texts]


class FakeVectorStore(VectorStore):
    """In-memory vector store for tests."""

    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}
        self.upsert_count = 0
        self.delete_count = 0

    async def upsert(self, record: VectorRecord) -> None:
        self.records[record.id] = record
        self.upsert_count += 1

    async def upsert_batch(self, records: list[VectorRecord]) -> None:
        for r in records:
            self.records[r.id] = r
        self.upsert_count += len(records)

    async def get_by_entity(self, entity_id: str, entity_type: str) -> VectorRecord | None:
        for r in self.records.values():
            if r.entity_id == entity_id and r.entity_type == entity_type:
                return r
        return None

    async def delete(self, record_id: str) -> None:
        self.records.pop(record_id, None)

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        to_remove = [
            k for k, v in self.records.items()
            if v.entity_id == entity_id and v.entity_type == entity_type
        ]
        for k in to_remove:
            del self.records[k]
            self.delete_count += 1

    async def search(
        self,
        query_embedding: list[float],
        *,
        entity_type: str | None = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        limit: int = 10,
        score_threshold: float = 0.0,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for r in self.records.values():
            if entity_type and r.entity_type != entity_type:
                continue
            score = max(0.0, 1.0 - sum(
                (a - b) ** 2 for a, b in zip(query_embedding, r.embedding, strict=False)
            ) / max(len(r.embedding), 1))
            if score >= score_threshold:
                results.append(SearchResult(record=r, score=score))
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def count(self, entity_type: str | None = None) -> int:
        if entity_type:
            return sum(1 for r in self.records.values() if r.entity_type == entity_type)
        return len(self.records)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider(dimensions=3)


@pytest.fixture
def store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def service(provider: FakeProvider, store: FakeVectorStore) -> EmbeddingService:
    return EmbeddingService(
        provider=provider,
        vector_store=store,
        config=EmbeddingConfig(model="fake-model", dimensions=3, current_model_version=1),
    )


class TestEmbedAndStore:
    @pytest.mark.asyncio
    async def test_embed_and_store_creates_record(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        entity_id = uuid.uuid4()
        record = await service.embed_and_store(entity_id, "memory", "hello world")
        assert record.entity_id == str(entity_id)
        assert record.entity_type == "memory"
        assert record.model_version == 1
        assert len(record.embedding) == 3
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_embed_and_store_calls_provider(self, service: EmbeddingService, provider: FakeProvider) -> None:
        await service.embed_and_store(uuid.uuid4(), "memory", "test text")
        assert "test text" in provider.embed_calls


class TestEmbedAndStoreBatch:
    @pytest.mark.asyncio
    async def test_batch_creates_records(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        items = [
            {"entity_id": uuid.uuid4(), "entity_type": "memory", "text": f"text {i}"}
            for i in range(3)
        ]
        records = await service.embed_and_store_batch(items)
        assert len(records) == 3
        assert await store.count() == 3

    @pytest.mark.asyncio
    async def test_batch_empty(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        records = await service.embed_and_store_batch([])
        assert records == []
        assert await store.count() == 0


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "hello")
        results = await service.search("hello", entity_type="memory")
        assert len(results) == 1
        assert results[0].record.entity_id == str(entity_id)

    @pytest.mark.asyncio
    async def test_search_with_threshold(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        await service.embed_and_store(uuid.uuid4(), "memory", "hello")
        results = await service.search("hello", score_threshold=0.99)
        assert len(results) <= 1


class TestGetAndDelete:
    @pytest.mark.asyncio
    async def test_get_embedding(self, service: EmbeddingService) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "text")
        record = await service.get_embedding(entity_id, "memory")
        assert record is not None
        assert record.entity_id == str(entity_id)

    @pytest.mark.asyncio
    async def test_get_missing(self, service: EmbeddingService) -> None:
        record = await service.get_embedding(uuid.uuid4(), "memory")
        assert record is None

    @pytest.mark.asyncio
    async def test_delete_embedding(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "text")
        await service.delete_embedding(entity_id, "memory")
        assert await service.get_embedding(entity_id, "memory") is None


class TestReembedding:
    @pytest.mark.asyncio
    async def test_needs_reembedding_stale(self, service: EmbeddingService) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "text")
        service.config.current_model_version = 2
        assert await service.needs_reembedding(entity_id, "memory") is True

    @pytest.mark.asyncio
    async def test_needs_reembedding_current(self, service: EmbeddingService) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "text")
        assert await service.needs_reembedding(entity_id, "memory") is False

    @pytest.mark.asyncio
    async def test_needs_reembedding_missing(self, service: EmbeddingService) -> None:
        assert await service.needs_reembedding(uuid.uuid4(), "memory") is True

    @pytest.mark.asyncio
    async def test_reembed_replaces(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        entity_id = uuid.uuid4()
        await service.embed_and_store(entity_id, "memory", "old text")
        service.config.current_model_version = 2
        record = await service.reembed(entity_id, "memory", "new text")
        assert record.model_version == 2
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_reembed_batch(self, service: EmbeddingService, store: FakeVectorStore) -> None:
        eid1, eid2 = uuid.uuid4(), uuid.uuid4()
        await service.embed_and_store(eid1, "memory", "old1")
        await service.embed_and_store(eid2, "memory", "old2")
        service.config.current_model_version = 2
        items = [
            {"entity_id": eid1, "entity_type": "memory", "text": "new1"},
            {"entity_id": eid2, "entity_type": "memory", "text": "new2"},
        ]
        records = await service.reembed_batch(items)
        assert len(records) == 2
        assert all(r.model_version == 2 for r in records)
        assert await store.count() == 2


class TestCount:
    @pytest.mark.asyncio
    async def test_count(self, service: EmbeddingService) -> None:
        assert await service.count() == 0
        await service.embed_and_store(uuid.uuid4(), "memory", "t")
        await service.embed_and_store(uuid.uuid4(), "book_chunk", "t")
        assert await service.count() == 2
        assert await service.count("memory") == 1
