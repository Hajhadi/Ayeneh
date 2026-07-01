"""Comprehensive tests for the Knowledge Retrieval Engine."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.application.ports.vector_store import SearchResult, VectorRecord
from ayeneh.application.services.knowledge import (
    Book,
    BookChunk,
    BookRepository,
    ChunkSearchGateway,
    EmbeddingGateway,
    KnowledgeService,
    RetrievalConfig,
    RetrievalStrategy,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeBookRepo(BookRepository):
    def __init__(self) -> None:
        self._books: dict[uuid.UUID, Book] = {}
        self._chunks: dict[uuid.UUID, BookChunk] = {}

    def add_book(self, book: Book) -> None:
        self._books[book.id] = book

    def add_chunk(self, chunk: BookChunk) -> None:
        self._chunks[chunk.id] = chunk

    async def get_by_user(self, user_id: uuid.UUID) -> list[Book]:
        return [b for b in self._books.values() if b.user_id == user_id]

    async def get_by_id(self, book_id: uuid.UUID) -> Book | None:
        return self._books.get(book_id)

    async def get_chunks_by_book(self, book_id: uuid.UUID) -> list[BookChunk]:
        return [c for c in self._chunks.values() if c.book_id == book_id]

    async def get_chunks_by_ids(self, chunk_ids: list[uuid.UUID]) -> list[BookChunk]:
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]


class FakeChunkSearch(ChunkSearchGateway):
    def __init__(self) -> None:
        self._vectors: dict[str, VectorRecord] = {}
        self._keyword_index: dict[str, list[str]] = {}

    def index(self, record: VectorRecord, keywords: list[str] | None = None) -> None:
        self._vectors[record.entity_id] = record
        if keywords:
            for kw in keywords:
                self._keyword_index.setdefault(kw.lower(), []).append(record.entity_id)

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        *,
        user_id: uuid.UUID,
        entity_type: str = "book_chunk",
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for _eid, rec in self._vectors.items():
            if rec.entity_type != entity_type:
                continue
            score = 1.0 - sum(
                (a - b) ** 2
                for a, b in zip(query_embedding[: len(rec.embedding)], rec.embedding, strict=True)
            ) / max(len(rec.embedding), 1)
            if score >= score_threshold:
                results.append(SearchResult(record=rec, score=max(0.0, score)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def keyword_search(
        self,
        query: str,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        query_lower = query.lower()
        matches: dict[str, float] = {}
        for kw, eids in self._keyword_index.items():
            if kw in query_lower or query_lower in kw:
                for eid in eids:
                    matches[eid] = matches.get(eid, 0.0) + 0.5
        results: list[SearchResult] = []
        for eid, score in sorted(matches.items(), key=lambda x: x[1], reverse=True):
            if eid in self._vectors:
                results.append(SearchResult(record=self._vectors[eid], score=score))
        return results[:limit]


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self, dims: int = 4) -> None:
        self._dims = dims
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(hash(text) % 100) / 100 for _ in range(self._dims)]


@pytest.fixture
def uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def book_repo() -> FakeBookRepo:
    return FakeBookRepo()


@pytest.fixture
def chunk_search() -> FakeChunkSearch:
    return FakeChunkSearch()


@pytest.fixture
def emb() -> FakeEmbeddingGateway:
    return FakeEmbeddingGateway()


@pytest.fixture
def svc(book_repo: FakeBookRepo, chunk_search: FakeChunkSearch, emb: FakeEmbeddingGateway) -> KnowledgeService:
    return KnowledgeService(book_repo=book_repo, chunk_search=chunk_search, embeddings=emb)


def _make_book(uid: uuid.UUID, title: str = "Test Book") -> Book:
    bid = uuid.uuid4()
    return Book(id=bid, user_id=uid, title=title, author="Author", source_format="pdf", status="ready")


def _make_chunk(book_id: uuid.UUID, content: str, seq: int = 0, tokens: int = 50, section: str | None = None) -> BookChunk:
    return BookChunk(
        id=uuid.uuid4(),
        book_id=book_id,
        chapter_id=uuid.uuid4(),
        content=content,
        sequence_number=seq,
        token_count=tokens,
        section_heading=section,
    )


# ---------------------------------------------------------------------------
# Semantic retrieval
# ---------------------------------------------------------------------------

class TestSemanticRetrieval:
    @pytest.mark.asyncio
    async def test_semantic_only_strategy(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        chunk = _make_chunk(book.id, "quantum computing basics")
        book_repo.add_chunk(chunk)
        chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY)
        ctx = await svc.retrieve(uid, "quantum physics", config=cfg)
        assert len(ctx.chunks) == 1

    @pytest.mark.asyncio
    async def test_semantic_no_results(self, svc: KnowledgeService, uid: uuid.UUID) -> None:
        ctx = await svc.retrieve(uid, "nothing matches", config=RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY))
        assert len(ctx.chunks) == 0


# ---------------------------------------------------------------------------
# Hybrid retrieval
# ---------------------------------------------------------------------------

class TestHybridRetrieval:
    @pytest.mark.asyncio
    async def test_hybrid_combines_semantic_and_keyword(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        c1 = _make_chunk(book.id, "machine learning algorithms", seq=0)
        c2 = _make_chunk(book.id, "deep learning neural networks", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1), keywords=["machine", "learning"])
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.1, 0.9, 0.1, 0.1], model_version=1), keywords=["deep", "learning"])

        cfg = RetrievalConfig(strategy=RetrievalStrategy.HYBRID)
        ctx = await svc.retrieve(uid, "machine learning", config=cfg)
        assert len(ctx.chunks) >= 1

    @pytest.mark.asyncio
    async def test_hybrid_respects_weights(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        c1 = _make_chunk(book.id, "alpha content", seq=0)
        c2 = _make_chunk(book.id, "beta content", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1), keywords=["alpha"])
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.1, 0.9, 0.1, 0.1], model_version=1), keywords=["beta"])

        cfg = RetrievalConfig(strategy=RetrievalStrategy.HYBRID, semantic_weight=1.0, keyword_weight=0.0)
        ctx = await svc.retrieve(uid, "alpha", config=cfg)
        assert len(ctx.chunks) >= 1
        assert ctx.chunks[0].chunk.id == c1.id


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

class TestKeywordRetrieval:
    @pytest.mark.asyncio
    async def test_keyword_only_strategy(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        c1 = _make_chunk(book.id, "kubernetes deployment guide", seq=0)
        c2 = _make_chunk(book.id, "docker container basics", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.5] * 4, model_version=1), keywords=["kubernetes", "deployment"])
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.5] * 4, model_version=1), keywords=["docker", "container"])

        cfg = RetrievalConfig(strategy=RetrievalStrategy.KEYWORD_ONLY)
        ctx = await svc.retrieve(uid, "kubernetes deployment", config=cfg)
        assert len(ctx.chunks) >= 1
        assert any("kubernetes" in c.chunk.content for c in ctx.chunks)


# ---------------------------------------------------------------------------
# Metadata filtering
# ---------------------------------------------------------------------------

class TestMetadataFiltering:
    @pytest.mark.asyncio
    async def test_chunks_loaded_from_correct_book(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        b1 = _make_book(uid, "Book A")
        b2 = _make_book(uid, "Book B")
        book_repo.add_book(b1)
        book_repo.add_book(b2)
        c1 = _make_chunk(b1.id, "content from A", seq=0)
        c2 = _make_chunk(b2.id, "content from B", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.8, 0.2, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "content")
        titles = [rc.book.title for rc in ctx.chunks]
        assert "Book A" in titles or "Book B" in titles


# ---------------------------------------------------------------------------
# Citation generation
# ---------------------------------------------------------------------------

class TestCitationGeneration:
    @pytest.mark.asyncio
    async def test_citations_generated(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid, "Citation Book")
        book_repo.add_book(book)
        chunk = _make_chunk(book.id, "important passage about AI", seq=0, section="Chapter 1: AI Basics")
        book_repo.add_chunk(chunk)
        chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "artificial intelligence")
        assert len(ctx.citations) >= 1
        assert ctx.citations[0].book_title == "Citation Book"
        assert ctx.citations[0].section_heading == "Chapter 1: AI Basics"

    @pytest.mark.asyncio
    async def test_citation_includes_excerpt(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        content = "a" * 300
        chunk = _make_chunk(book.id, content, seq=0)
        book_repo.add_chunk(chunk)
        chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "test query")
        assert len(ctx.citations) >= 1
        assert len(ctx.citations[0].excerpt) <= 200


# ---------------------------------------------------------------------------
# Context compression
# ---------------------------------------------------------------------------

class TestContextCompression:
    @pytest.mark.asyncio
    async def test_respects_token_budget(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        for i in range(10):
            chunk = _make_chunk(book.id, f"chunk {i}", seq=i, tokens=100)
            book_repo.add_chunk(chunk)
            chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9 - i * 0.05, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, token_budget=350, tokens_per_chunk_estimate=100)
        ctx = await svc.retrieve(uid, "chunk", config=cfg)
        assert ctx.total_tokens_estimate <= 350

    @pytest.mark.asyncio
    async def test_compression_stops_at_budget(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        for i in range(5):
            chunk = _make_chunk(book.id, f"chunk {i}", seq=i, tokens=500)
            book_repo.add_chunk(chunk)
            chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, token_budget=600, tokens_per_chunk_estimate=500)
        ctx = await svc.retrieve(uid, "chunk", config=cfg)
        assert len(ctx.chunks) <= 2


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

class TestRanking:
    @pytest.mark.asyncio
    async def test_chunks_sorted_by_score(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        c1 = _make_chunk(book.id, "low relevance", seq=0)
        c2 = _make_chunk(book.id, "high relevance", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.2, 0.8, 0.1, 0.1], model_version=1))
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "query matching c2", config=RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY))
        if len(ctx.chunks) >= 2:
            assert ctx.chunks[0].final_score >= ctx.chunks[1].final_score


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

class TestBudgetEnforcement:
    @pytest.mark.asyncio
    async def test_total_tokens_within_budget(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        for i in range(20):
            chunk = _make_chunk(book.id, f"chunk {i}", seq=i, tokens=100)
            book_repo.add_chunk(chunk)
            chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, token_budget=500, tokens_per_chunk_estimate=100)
        ctx = await svc.retrieve(uid, "chunk", config=cfg)
        assert ctx.total_tokens_estimate <= 500
        assert ctx.token_budget == 500

    @pytest.mark.asyncio
    async def test_zero_budget_returns_empty(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        chunk = _make_chunk(book.id, "content", seq=0, tokens=50)
        book_repo.add_chunk(chunk)
        chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, token_budget=0)
        ctx = await svc.retrieve(uid, "content", config=cfg)
        assert len(ctx.chunks) == 0


# ---------------------------------------------------------------------------
# Multi-source retrieval
# ---------------------------------------------------------------------------

class TestMultiSourceRetrieval:
    @pytest.mark.asyncio
    async def test_retrieves_from_multiple_books(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        b1 = _make_book(uid, "Physics")
        b2 = _make_book(uid, "Chemistry")
        b3 = _make_book(uid, "Biology")
        for b in [b1, b2, b3]:
            book_repo.add_book(b)
            c = _make_chunk(b.id, f"content from {b.title}", seq=0)
            book_repo.add_chunk(c)
            chunk_search.index(VectorRecord(id=str(c.id), entity_id=str(c.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "content", config=RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, max_total_chunks=10))
        assert len(ctx.chunks) == 3

    @pytest.mark.asyncio
    async def test_sources_used_populated(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        b1 = _make_book(uid, "Source A")
        b2 = _make_book(uid, "Source B")
        book_repo.add_book(b1)
        book_repo.add_book(b2)
        c1 = _make_chunk(b1.id, "alpha", seq=0)
        c2 = _make_chunk(b2.id, "beta", seq=1)
        book_repo.add_chunk(c1)
        book_repo.add_chunk(c2)
        chunk_search.index(VectorRecord(id=str(c1.id), entity_id=str(c1.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))
        chunk_search.index(VectorRecord(id=str(c2.id), entity_id=str(c2.id), entity_type="book_chunk", embedding=[0.8, 0.2, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "content")
        assert len(ctx.sources_used) >= 1


# ---------------------------------------------------------------------------
# Merged retrieval context
# ---------------------------------------------------------------------------

class TestMergedContext:
    @pytest.mark.asyncio
    async def test_context_has_all_fields(self, svc: KnowledgeService, uid: uuid.UUID) -> None:
        ctx = await svc.retrieve(uid, "empty query")
        assert ctx.query == "empty query"
        assert isinstance(ctx.chunks, list)
        assert isinstance(ctx.citations, list)
        assert isinstance(ctx.total_tokens_estimate, int)
        assert isinstance(ctx.sources_used, list)

    @pytest.mark.asyncio
    async def test_citations_match_chunks(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid, "Matched Book")
        book_repo.add_book(book)
        chunk = _make_chunk(book.id, "relevant passage", seq=0, section="Intro")
        book_repo.add_chunk(chunk)
        chunk_search.index(VectorRecord(id=str(chunk.id), entity_id=str(chunk.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        ctx = await svc.retrieve(uid, "relevant")
        assert len(ctx.chunks) == len(ctx.citations)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_book_repo(self, svc: KnowledgeService, uid: uuid.UUID) -> None:
        ctx = await svc.retrieve(uid, "anything")
        assert len(ctx.chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_not_in_repo(self, svc: KnowledgeService, uid: uuid.UUID, chunk_search: FakeChunkSearch) -> None:
        fake_id = uuid.uuid4()
        chunk_search.index(VectorRecord(id=str(fake_id), entity_id=str(fake_id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))
        ctx = await svc.retrieve(uid, "query", config=RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY))
        assert len(ctx.chunks) == 0

    @pytest.mark.asyncio
    async def test_max_chunks_per_source(self, svc: KnowledgeService, uid: uuid.UUID, book_repo: FakeBookRepo, chunk_search: FakeChunkSearch) -> None:
        book = _make_book(uid)
        book_repo.add_book(book)
        for i in range(10):
            c = _make_chunk(book.id, f"chunk {i}", seq=i, tokens=10)
            book_repo.add_chunk(c)
            chunk_search.index(VectorRecord(id=str(c.id), entity_id=str(c.id), entity_type="book_chunk", embedding=[0.9, 0.1, 0.1, 0.1], model_version=1))

        cfg = RetrievalConfig(strategy=RetrievalStrategy.SEMANTIC_ONLY, max_chunks_per_source=3, max_total_chunks=3)
        ctx = await svc.retrieve(uid, "chunk", config=cfg)
        assert len(ctx.chunks) <= 3
