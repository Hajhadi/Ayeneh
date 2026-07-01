"""Tests for vector store abstraction."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.application.ports.vector_store import (
    SearchResult,
    SimilarityMetric,
    VectorRecord,
    VectorStore,
)


class MockVectorStore(VectorStore):
    """Test double for VectorStore."""

    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}

    async def upsert(self, record: VectorRecord) -> None:
        to_remove = [
            k for k, v in self.records.items()
            if v.entity_id == record.entity_id and v.entity_type == record.entity_type
        ]
        for k in to_remove:
            del self.records[k]
        self.records[record.id] = record

    async def upsert_batch(self, records: list[VectorRecord]) -> None:
        for r in records:
            await self.upsert(r)

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
            score = 1.0 - sum(
                (a - b) ** 2 for a, b in zip(query_embedding[: len(r.embedding)], r.embedding, strict=False)
            ) / len(r.embedding)
            if score >= score_threshold:
                results.append(SearchResult(record=r, score=score))
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def count(self, entity_type: str | None = None) -> int:
        if entity_type:
            return sum(1 for r in self.records.values() if r.entity_type == entity_type)
        return len(self.records)


class TestVectorStoreContract:
    """Test the VectorStore abstract contract via mock."""

    @pytest.mark.asyncio
    async def test_upsert_and_get(self) -> None:
        store = MockVectorStore()
        record = VectorRecord(
            id=str(uuid.uuid4()),
            entity_id=str(uuid.uuid4()),
            entity_type="memory",
            embedding=[0.1, 0.2, 0.3],
            model_version=1,
        )
        await store.upsert(record)
        found = await store.get_by_entity(record.entity_id, "memory")
        assert found is not None
        assert found.entity_id == record.entity_id

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self) -> None:
        store = MockVectorStore()
        entity_id = str(uuid.uuid4())
        r1 = VectorRecord(id="1", entity_id=entity_id, entity_type="memory", embedding=[0.1], model_version=1)
        r2 = VectorRecord(id="2", entity_id=entity_id, entity_type="memory", embedding=[0.5], model_version=2)
        await store.upsert(r1)
        await store.upsert(r2)
        found = await store.get_by_entity(entity_id, "memory")
        assert found is not None
        assert found.model_version == 2

    @pytest.mark.asyncio
    async def test_upsert_batch(self) -> None:
        store = MockVectorStore()
        records = [
            VectorRecord(id=str(i), entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[0.1], model_version=1)
            for i in range(5)
        ]
        await store.upsert_batch(records)
        assert await store.count() == 5

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        store = MockVectorStore()
        record = VectorRecord(id="del-1", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[0.1], model_version=1)
        await store.upsert(record)
        await store.delete("del-1")
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_delete_by_entity(self) -> None:
        store = MockVectorStore()
        entity_id = str(uuid.uuid4())
        r1 = VectorRecord(id="1", entity_id=entity_id, entity_type="memory", embedding=[0.1], model_version=1)
        r2 = VectorRecord(id="2", entity_id=str(uuid.uuid4()), entity_type="book_chunk", embedding=[0.2], model_version=1)
        await store.upsert(r1)
        await store.upsert(r2)
        await store.delete_by_entity(entity_id, "memory")
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        store = MockVectorStore()
        await store.upsert(VectorRecord(id="1", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[1.0, 0.0], model_version=1))
        await store.upsert(VectorRecord(id="2", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[0.0, 1.0], model_version=1))
        results = await store.search([1.0, 0.0], limit=2)
        assert len(results) == 2
        assert results[0].score >= results[1].score

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self) -> None:
        store = MockVectorStore()
        await store.upsert(VectorRecord(id="1", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[1.0], model_version=1))
        await store.upsert(VectorRecord(id="2", entity_id=str(uuid.uuid4()), entity_type="book_chunk", embedding=[1.0], model_version=1))
        results = await store.search([1.0], entity_type="memory")
        assert len(results) == 1
        assert results[0].record.entity_type == "memory"

    @pytest.mark.asyncio
    async def test_search_with_score_threshold(self) -> None:
        store = MockVectorStore()
        await store.upsert(VectorRecord(id="1", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[1.0, 0.0], model_version=1))
        await store.upsert(VectorRecord(id="2", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[0.0, 1.0], model_version=1))
        results = await store.search([1.0, 0.0], score_threshold=0.9)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        store = MockVectorStore()
        assert await store.count() == 0
        await store.upsert(VectorRecord(id="1", entity_id=str(uuid.uuid4()), entity_type="memory", embedding=[0.1], model_version=1))
        assert await store.count() == 1
        assert await store.count("memory") == 1
        assert await store.count("book_chunk") == 0
