"""Comprehensive tests for the Memory Engine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.application.ports.vector_store import SearchResult, VectorRecord
from ayeneh.application.services.memory import (
    ConsolidationResult,
    EmbeddingGateway,
    ExpirationPolicy,
    Memory,
    MemoryCreate,
    MemoryRepository,
    MemoryService,
    MemoryStatus,
    MemoryType,
    RankingWeights,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class InMemoryMemoryRepo(MemoryRepository):
    """In-memory repository for testing."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Memory] = {}

    async def create(self, memory: Memory) -> Memory:
        self._store[memory.id] = memory
        return memory

    async def get_by_id(self, memory_id: uuid.UUID) -> Memory | None:
        return self._store.get(memory_id)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        results = [
            m
            for m in self._store.values()
            if m.user_id == user_id and m.status == status
            and (memory_type is None or m.type == memory_type)
        ]
        return results[offset : offset + limit]

    async def update(self, memory: Memory) -> Memory:
        self._store[memory.id] = memory
        return memory

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        return sum(1 for m in self._store.values() if m.user_id == user_id)

    async def list_expiring(
        self, user_id: uuid.UUID, before: datetime, limit: int = 100
    ) -> list[Memory]:
        return [
            m
            for m in self._store.values()
            if m.user_id == user_id
            and m.created_at < before
            and m.status == MemoryStatus.ACTIVE
        ][:limit]

    async def find_similar_content(
        self, user_id: uuid.UUID, content: str, threshold: float = 0.95
    ) -> list[Memory]:
        normalized = content.strip().lower()
        return [
            m
            for m in self._store.values()
            if m.user_id == user_id
            and m.status == MemoryStatus.ACTIVE
            and m.content.strip().lower() == normalized
        ]


class FakeEmbeddingGateway(EmbeddingGateway):
    """Deterministic embedding gateway for tests."""

    def __init__(self, dimensions: int = 4) -> None:
        self._dims = dimensions
        self._vectors: dict[str, list[float]] = {}
        self.embed_calls: list[str] = []
        self.upsert_calls: list[tuple[uuid.UUID, str]] = []
        self.delete_calls: list[tuple[uuid.UUID, str]] = []

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [float(hash(text) % 100) / 100 for _ in range(self._dims)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    async def search_similar(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        query_emb = await self.embed(query)
        for eid, emb in self._vectors.items():
            score = 1.0 - sum(
                (a - b) ** 2 for a, b in zip(query_emb, emb, strict=True)
            ) / len(emb)
            if score >= score_threshold:
                results.append(
                    SearchResult(
                        record=VectorRecord(
                            id=eid,
                            entity_id=eid,
                            entity_type="memory",
                            embedding=emb,
                            model_version=1,
                        ),
                        score=max(0.0, score),
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def upsert(self, entity_id: uuid.UUID, entity_type: str, text: str) -> None:
        self.upsert_calls.append((entity_id, entity_type))
        self._vectors[str(entity_id)] = await self.embed(text)

    async def delete(self, entity_id: uuid.UUID, entity_type: str) -> None:
        self.delete_calls.append((entity_id, entity_type))
        self._vectors.pop(str(entity_id), None)

    async def needs_reembedding(self, entity_id: uuid.UUID, entity_type: str) -> bool:
        return str(entity_id) not in self._vectors


@pytest.fixture
def uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def repo() -> InMemoryMemoryRepo:
    return InMemoryMemoryRepo()


@pytest.fixture
def emb() -> FakeEmbeddingGateway:
    return FakeEmbeddingGateway()


@pytest.fixture
def svc(repo: InMemoryMemoryRepo, emb: FakeEmbeddingGateway) -> MemoryService:
    return MemoryService(repo=repo, embeddings=emb)


# ---------------------------------------------------------------------------
# Storing memories
# ---------------------------------------------------------------------------

class TestStore:
    @pytest.mark.asyncio
    async def test_store_creates_memory(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="I went to the park"))
        assert m.id is not None
        assert m.type == MemoryType.EPISODIC
        assert m.status == MemoryStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_store_generates_embedding(self, svc: MemoryService, emb: FakeEmbeddingGateway, uid: uuid.UUID) -> None:
        m = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="I love dogs"))
        assert len(emb.upsert_calls) == 1
        assert emb.upsert_calls[0][0] == m.id

    @pytest.mark.asyncio
    async def test_store_deduplicates(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m1 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="exact duplicate"))
        m2 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="exact duplicate"))
        assert m1.id == m2.id

    @pytest.mark.asyncio
    async def test_store_dedup_keeps_higher_confidence(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m1 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="dup", confidence=0.3))
        m2 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="dup", confidence=0.9))
        assert m1.id == m2.id
        assert m2.confidence == 0.9

    @pytest.mark.asyncio
    async def test_store_different_types_not_deduped(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m1 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="shared"))
        m2 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="shared"))
        assert m1.id != m2.id

    @pytest.mark.asyncio
    async def test_store_batch(self, svc: MemoryService, uid: uuid.UUID) -> None:
        items = [
            MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content=f"item {i}")
            for i in range(5)
        ]
        results = await svc.store_batch(items)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_store_preserves_source_message_ids(self, svc: MemoryService, uid: uuid.UUID) -> None:
        msg_ids = [uuid.uuid4(), uuid.uuid4()]
        m = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="with sources", source_message_ids=msg_ids))
        assert m.source_message_ids == msg_ids


# ---------------------------------------------------------------------------
# Retrieving memories
# ---------------------------------------------------------------------------

class TestRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_empty(self, svc: MemoryService, uid: uuid.UUID) -> None:
        ctx = await svc.retrieve(uid, "query")
        assert ctx.episodic == []
        assert ctx.semantic == []
        assert ctx.total_tokens_estimate == 0

    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="park visit"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="loves nature"))
        ctx = await svc.retrieve(uid, "park")
        total = len(ctx.episodic) + len(ctx.semantic) + len(ctx.pattern) + len(ctx.reflection)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_retrieve_respects_type_filter(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="park"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="nature"))
        ctx = await svc.retrieve(uid, "park", memory_types=[MemoryType.EPISODIC])
        assert len(ctx.episodic) >= 1
        assert len(ctx.semantic) == 0

    @pytest.mark.asyncio
    async def test_retrieve_respects_limit(self, svc: MemoryService, uid: uuid.UUID) -> None:
        for i in range(20):
            await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content=f"memory {i}"))
        ctx = await svc.retrieve(uid, "memory", limit=5)
        total = len(ctx.episodic) + len(ctx.semantic) + len(ctx.pattern) + len(ctx.reflection)
        assert total <= 5

    @pytest.mark.asyncio
    async def test_retrieve_by_type(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.PATTERN, content="tends to procrastinate"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="went to store"))
        results = await svc.retrieve_by_type(uid, MemoryType.PATTERN, limit=10)
        assert len(results) == 1
        assert results[0].type == MemoryType.PATTERN


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

class TestRanking:
    @pytest.mark.asyncio
    async def test_ranking_scores_populated(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="important goal"))
        ctx = await svc.retrieve(uid, "important goal")
        assert len(ctx.scores) >= 1
        assert ctx.scores[0].final_score > 0

    @pytest.mark.asyncio
    async def test_ranking_respects_weights(self, svc: MemoryService, uid: uuid.UUID) -> None:
        svc.ranking_weights = RankingWeights(relevance=1.0, recency=0.0, importance=0.0, confidence=0.0)
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="test"))
        ctx = await svc.retrieve(uid, "test")
        assert len(ctx.scores) >= 1
        assert ctx.scores[0].relevance >= 0

    @pytest.mark.asyncio
    async def test_recency_scores_older_lower(self) -> None:
        now = datetime.now(UTC)
        mem_old = Memory(id=uuid.uuid4(), user_id=uuid.uuid4(), type=MemoryType.EPISODIC, content="old", created_at=now - timedelta(days=300))
        mem_new = Memory(id=uuid.uuid4(), user_id=uuid.uuid4(), type=MemoryType.EPISODIC, content="new", created_at=now - timedelta(days=1))
        svc = MemoryService(repo=InMemoryMemoryRepo(), embeddings=FakeEmbeddingGateway())
        scores = svc._rank([mem_old, mem_new], "query", {})
        assert scores[0].memory.id == mem_new.id

    @pytest.mark.asyncio
    async def test_importance_boosts_keywords(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="this is an important goal"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="went to store"))
        ctx = await svc.retrieve(uid, "important goal")
        if len(ctx.scores) >= 2:
            important_score = next(s for s in ctx.scores if "important" in s.memory.content)
            assert important_score.importance > 0.5


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

class TestConsolidation:
    @pytest.mark.asyncio
    async def test_consolidation_runs(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="memory a"))
        result = await svc.consolidate(uid)
        assert isinstance(result, ConsolidationResult)

    @pytest.mark.asyncio
    async def test_consolidation_expires_old(self, svc: MemoryService, uid: uuid.UUID) -> None:
        old = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="very old",
            confidence=0.1,
            created_at=datetime.now(UTC) - timedelta(days=400),
        )
        await svc.repo.create(old)
        await svc.embeddings.upsert(old.id, "memory", old.content)
        result = await svc.consolidate(uid)
        assert result.archived >= 1

    @pytest.mark.asyncio
    async def test_consolidation_deduplicates(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="duplicate me"))
        m2 = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="duplicate me", confidence=0.3,
            created_at=datetime.now(UTC),
        )
        await svc.repo.create(m2)
        await svc.embeddings.upsert(m2.id, "memory", m2.content)
        result = await svc.consolidate(uid)
        assert result.deduplicated >= 1

    @pytest.mark.asyncio
    async def test_consolidation_merges_similar(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="I enjoy reading books and writing stories"))
        m2 = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="I enjoy reading books and writing stories also",
            confidence=0.5,
            created_at=datetime.now(UTC),
        )
        await svc.repo.create(m2)
        await svc.embeddings.upsert(m2.id, "memory", m2.content)
        result = await svc.consolidate(uid)
        assert result.merged >= 1


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_removes_exact_duplicates(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m1 = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="exact"))
        m2 = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.SEMANTIC,
            content="exact", confidence=0.4,
            created_at=datetime.now(UTC),
        )
        await svc.repo.create(m2)
        await svc.embeddings.upsert(m2.id, "memory", m2.content)
        deduped = await svc._deduplicate(uid)
        assert deduped >= 1
        m1_reload = await svc.repo.get_by_id(m1.id)
        assert m1_reload is not None
        assert m1_reload.status == MemoryStatus.ACTIVE


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------

class TestExpiration:
    @pytest.mark.asyncio
    async def test_expiration_archives_old_low_confidence(self, svc: MemoryService, uid: uuid.UUID) -> None:
        old = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="fading memory", confidence=0.1,
            created_at=datetime.now(UTC) - timedelta(days=200),
        )
        await svc.repo.create(old)
        await svc.embeddings.upsert(old.id, "memory", old.content)
        count = await svc._expire_memories(uid)
        assert count >= 1
        reloaded = await svc.repo.get_by_id(old.id)
        assert reloaded is not None
        assert reloaded.status == MemoryStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_expiration_keeps_high_confidence(self, svc: MemoryService, uid: uuid.UUID) -> None:
        old = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="important old", confidence=0.9,
            created_at=datetime.now(UTC) - timedelta(days=200),
        )
        await svc.repo.create(old)
        count = await svc._expire_memories(uid)
        assert count == 0
        reloaded = await svc.repo.get_by_id(old.id)
        assert reloaded is not None
        assert reloaded.status == MemoryStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_expiration_respects_ttl_per_type(self, svc: MemoryService, uid: uuid.UUID) -> None:
        svc.expiration = ExpirationPolicy(episodic_ttl_days=10, semantic_ttl_days=1000)
        epi = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.EPISODIC,
            content="epi", confidence=0.1,
            created_at=datetime.now(UTC) - timedelta(days=20),
        )
        sem = Memory(
            id=uuid.uuid4(), user_id=uid, type=MemoryType.SEMANTIC,
            content="sem", confidence=0.1,
            created_at=datetime.now(UTC) - timedelta(days=20),
        )
        await svc.repo.create(epi)
        await svc.repo.create(sem)
        count = await svc._expire_memories(uid)
        assert count == 1


# ---------------------------------------------------------------------------
# Supersede and archive
# ---------------------------------------------------------------------------

class TestLifecycle:
    @pytest.mark.asyncio
    async def test_supersede(self, svc: MemoryService, uid: uuid.UUID) -> None:
        old = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="old belief"))
        new = await svc.supersede(old.id, "new belief", new_confidence=0.9)
        assert new.id != old.id
        assert new.content == "new belief"
        old_reload = await svc.repo.get_by_id(old.id)
        assert old_reload is not None
        assert old_reload.status == MemoryStatus.SUPERSEDED

    @pytest.mark.asyncio
    async def test_supersede_not_found(self, svc: MemoryService) -> None:
        with pytest.raises(ValueError):
            await svc.supersede(uuid.uuid4(), "new")

    @pytest.mark.asyncio
    async def test_archive(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="archivable"))
        await svc.archive(m.id)
        reloaded = await svc.repo.get_by_id(m.id)
        assert reloaded is not None
        assert reloaded.status == MemoryStatus.ARCHIVED


# ---------------------------------------------------------------------------
# RetrievalContext
# ---------------------------------------------------------------------------

class TestRetrievalContext:
    @pytest.mark.asyncio
    async def test_context_buckets_by_type(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="epi"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.SEMANTIC, content="sem"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.PATTERN, content="pat"))
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.REFLECTION, content="ref"))
        ctx = await svc.retrieve(uid, "epi sem pat ref", limit=10)
        types_found = set()
        if ctx.episodic:
            types_found.add("episodic")
        if ctx.semantic:
            types_found.add("semantic")
        if ctx.pattern:
            types_found.add("pattern")
        if ctx.reflection:
            types_found.add("reflection")
        assert len(types_found) >= 2

    @pytest.mark.asyncio
    async def test_context_token_estimate(self, svc: MemoryService, uid: uuid.UUID) -> None:
        await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content="word " * 50))
        ctx = await svc.retrieve(uid, "word", limit=5)
        assert ctx.total_tokens_estimate > 0


# ---------------------------------------------------------------------------
# Content similarity
# ---------------------------------------------------------------------------

class TestContentSimilarity:
    def test_identical(self) -> None:
        assert MemoryService._content_similarity("hello world", "hello world") == 1.0

    def test_disjoint(self) -> None:
        assert MemoryService._content_similarity("cat", "dog") == 0.0

    def test_partial(self) -> None:
        sim = MemoryService._content_similarity("hello world", "hello there")
        assert 0.0 < sim < 1.0

    def test_empty(self) -> None:
        assert MemoryService._content_similarity("", "") == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_store_empty_content(self, svc: MemoryService, uid: uuid.UUID) -> None:
        m = await svc.store(MemoryCreate(user_id=uid, type=MemoryType.EPISODIC, content=""))
        assert m.content == ""

    @pytest.mark.asyncio
    async def test_retrieve_no_memories(self, svc: MemoryService, uid: uuid.UUID) -> None:
        ctx = await svc.retrieve(uuid.uuid4(), "anything")
        assert len(ctx.scores) == 0

    @pytest.mark.asyncio
    async def test_consolidation_empty_user(self, svc: MemoryService, uid: uuid.UUID) -> None:
        result = await svc.consolidate(uid)
        assert result.merged == 0
        assert result.archived == 0
        assert result.deduplicated == 0
