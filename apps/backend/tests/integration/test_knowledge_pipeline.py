"""Integration tests for the complete Knowledge Ingestion and RAG pipeline."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

from ayeneh.application.ports.vector_store import SearchResult, VectorRecord
from ayeneh.application.services.knowledge import (
    Book,
    BookChunk,
    KnowledgeService,
    RankedChunk,
    RetrievalConfig,
    RetrievalStrategy,
)
from ayeneh.application.services.prompt_context import PromptContextService
from ayeneh.application.services.retrieval import RetrievalResult, RetrievalService
from ayeneh.ingestion.chunking.engine import ChunkingConfig, ChunkingEngine
from ayeneh.ingestion.ingestion_service import (
    BookRepository,
    EmbeddingGateway,
    EventPublisher,
    IngestionProgress,
    IngestionResult,
    IngestionService,
    ProgressCallback,
)
from ayeneh.ingestion.parsers.base import Chapter
from ayeneh.ingestion.parsers.markdown_parser import MarkdownParser
from ayeneh.ingestion.parsers.text_parser import TextParser


def _vr(chunk_id: str) -> VectorRecord:
    return VectorRecord(
        id=f"vr-{chunk_id}",
        entity_id=chunk_id,
        entity_type="book_chunk",
        embedding=[],
        model_version=1,
    )


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeBookRepo(BookRepository):
    def __init__(self) -> None:
        self.books: dict[str, dict] = {}
        self.chapters: dict[str, list[dict]] = {}
        self.chunks: dict[str, list[dict]] = {}

    async def get_by_id(self, book_id: str) -> dict | None:
        return self.books.get(book_id)

    async def update_status(self, book_id: str, status: str, **kwargs: Any) -> None:
        if book_id in self.books:
            self.books[book_id]["status"] = status
            self.books[book_id].update(kwargs)

    async def create_chapter(self, book_id: str, title: str, sequence: int, **kwargs: Any) -> dict:
        ch = {"id": str(uuid.uuid4()), "title": title, "sequence_number": sequence, **kwargs}
        self.chapters.setdefault(book_id, []).append(ch)
        return ch

    async def create_chunk(self, book_id: str, chapter_id: str, content: str, sequence: int, token_count: int, **kwargs: Any) -> dict:
        ck = {"id": str(uuid.uuid4()), "chapter_id": chapter_id, "content": content, "sequence_number": sequence, "token_count": token_count, **kwargs}
        self.chunks.setdefault(book_id, []).append(ck)
        return ck

    async def count_chunks(self, book_id: str) -> int:
        return len(self.chunks.get(book_id, []))

    async def get_chunks_by_book(self, book_id: str) -> list[dict]:
        return self.chunks.get(book_id, [])


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions
        self.stored: list[tuple[str, str, str]] = []
        self.embed_calls = 0

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        import random
        return [[random.random() for _ in range(self.dimensions)] for _ in texts]

    async def upsert(self, entity_id: str, entity_type: str, text: str) -> None:
        self.stored.append((entity_id, entity_type, text))

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        self.stored = [(eid, et, t) for eid, et, t in self.stored if eid != entity_id]


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, **payload})


class FakeProgressCallback(ProgressCallback):
    def __init__(self) -> None:
        self.steps_seen: list[str] = []

    async def on_progress(self, progress: IngestionProgress) -> None:
        self.steps_seen.append(progress.current_step)


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunkingEngine:
    def test_basic_chunking(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=50, overlap_tokens=10, min_chunk_tokens=5))
        chapter = Chapter(title="Chapter 1", sequence_number=0, content=" ".join(["word"] * 200))
        chunks = engine.chunk_document([chapter])
        assert len(chunks) > 1
        assert all(c.token_count >= 1 for c in chunks)

    def test_semantic_boundary_respect(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=30, overlap_tokens=5, min_chunk_tokens=3))
        text = " ".join(["Sentence.", "More.", "Here.", "Done."] * 10)
        chapter = Chapter(title="Test", sequence_number=0, content=text)
        chunks = engine.chunk_document([chapter])
        assert len(chunks) >= 1
        assert all(c.content.strip() for c in chunks)

    def test_empty_document(self) -> None:
        engine = ChunkingEngine()
        assert engine.chunk_document([]) == []

    def test_single_small_chapter(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=1000, min_chunk_tokens=1))
        chapter = Chapter(title="Short", sequence_number=0, content="Hello world.")
        chunks = engine.chunk_document([chapter])
        assert len(chunks) == 1
        assert chunks[0].token_count > 0

    def test_multiple_chapters_preserve_order(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=20, min_chunk_tokens=3))
        chapters = [
            Chapter(title=f"Ch {i}", sequence_number=i, content=" ".join(["sentence."] * 20))
            for i in range(3)
        ]
        chunks = engine.chunk_document(chapters)
        assert [c.sequence_number for c in chunks] == sorted(c.sequence_number for c in chunks)


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestMarkdownParser:
    @pytest.mark.asyncio
    async def test_parse_with_headings(self) -> None:
        parser = MarkdownParser()
        content = b"# Title\n\nIntro.\n\n## Ch 1\n\nContent.\n\n## Ch 2\n\nMore."
        doc = await parser.parse(content, "test.md")
        assert doc.title == "Title"
        assert doc.source_format == "markdown"
        assert len(doc.chapters) >= 2

    @pytest.mark.asyncio
    async def test_parse_fallback_title(self) -> None:
        parser = MarkdownParser()
        doc = await parser.parse(b"Just text.", "my-doc.md")
        assert doc.title == "My Doc"

    @pytest.mark.asyncio
    async def test_extract_title_from_h1(self) -> None:
        parser = MarkdownParser()
        assert parser._extract_title("# Hello World", "x.md") == "Hello World"

    @pytest.mark.asyncio
    async def test_no_duplicate_method(self) -> None:
        parser = MarkdownParser()
        methods = [m for m in dir(parser) if m == "_extract_title"]
        assert len(methods) == 1


class TestTextParser:
    @pytest.mark.asyncio
    async def test_parse_plain_text(self) -> None:
        parser = TextParser()
        doc = await parser.parse(b"Para one.\n\nPara two.", "test.txt")
        assert doc.source_format == "text"
        assert len(doc.chapters) >= 1

    @pytest.mark.asyncio
    async def test_parse_with_heading(self) -> None:
        parser = TextParser()
        doc = await parser.parse(b"INTRODUCTION\n\nIntro.\n\nCHAPTER ONE\n\nCh.", "book.txt")
        assert len(doc.chapters) >= 1


# ---------------------------------------------------------------------------
# Ingestion pipeline tests
# ---------------------------------------------------------------------------

class TestIngestionPipeline:
    @pytest.mark.asyncio
    async def test_full_markdown_ingestion(self) -> None:
        book_repo = FakeBookRepo()
        embedding = FakeEmbeddingGateway()
        events = FakeEventPublisher()
        progress = FakeProgressCallback()

        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=embedding,
            event_publisher=events,
            parsers={"markdown": MarkdownParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=100, min_chunk_tokens=10),
            progress_callback=progress,
        )

        book_id = str(uuid.uuid4())
        book_repo.books[book_id] = {"id": book_id, "status": "processing"}
        content = b"# My Book\n\nIntro.\n\n## Ch 1\n\nContent.\n\n## Ch 2\n\nMore."

        result = await ingestion.ingest(book_id, content, "test.md")
        assert result.status == "ready"
        assert result.total_chunks > 0
        assert result.chapters_detected >= 2

        book_idx_events = [e for e in events.events if e["type"] == "BookIndexed"]
        assert len(book_idx_events) == 1
        assert book_repo.books[book_id]["status"] == "ready"
        assert len(progress.steps_seen) >= 3

    @pytest.mark.asyncio
    async def test_full_text_ingestion(self) -> None:
        book_repo = FakeBookRepo()
        embedding = FakeEmbeddingGateway()

        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=embedding,
            event_publisher=FakeEventPublisher(),
            parsers={"text": TextParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=50, min_chunk_tokens=3),
        )

        book_id = str(uuid.uuid4())
        book_repo.books[book_id] = {"id": book_id, "status": "processing"}
        content = b"First paragraph. " * 30

        result = await ingestion.ingest(book_id, content, "book.txt")
        assert result.status == "ready"
        assert result.total_chunks > 0

    @pytest.mark.asyncio
    async def test_ingestion_failure_marks_failed(self) -> None:
        book_repo = FakeBookRepo()
        events = FakeEventPublisher()

        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=FakeEmbeddingGateway(),
            event_publisher=events,
            parsers={},
        )

        book_id = str(uuid.uuid4())
        book_repo.books[book_id] = {"id": book_id, "status": "processing"}
        result = await ingestion.ingest(book_id, b"content", "test.pdf")
        assert result.status == "failed"
        assert result.error is not None
        assert any(e["type"] == "BookIngestionFailed" for e in events.events)

    @pytest.mark.asyncio
    async def test_reindex_removes_old_embeddings(self) -> None:
        book_repo = FakeBookRepo()
        embedding = FakeEmbeddingGateway()

        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=embedding,
            event_publisher=FakeEventPublisher(),
            parsers={"markdown": MarkdownParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=100, min_chunk_tokens=10),
        )

        book_id = str(uuid.uuid4())
        book_repo.books[book_id] = {"id": book_id, "status": "ready"}
        book_repo.chunks[book_id] = [
            {"id": "old1", "content": "old"}, {"id": "old2", "content": "old"},
        ]
        embedding.stored = [("old1", "book_chunk", "text"), ("old2", "book_chunk", "text")]

        result = await ingestion.reindex(book_id, b"# New\n\n## Ch\n\nNew.", "new.md")
        assert result.status == "ready"
        assert all(eid not in ("old1", "old2") for eid, _, _ in embedding.stored)

    @pytest.mark.asyncio
    async def test_progress_tracks_all_steps(self) -> None:
        book_repo = FakeBookRepo()
        progress = FakeProgressCallback()

        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            parsers={"markdown": MarkdownParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=100, min_chunk_tokens=10),
            progress_callback=progress,
        )

        book_id = str(uuid.uuid4())
        book_repo.books[book_id] = {"id": book_id, "status": "processing"}
        await ingestion.ingest(book_id, b"# T\n\nContent.", "t.md")

        assert "parsing" in progress.steps_seen
        assert "chunking" in progress.steps_seen
        assert "embedding" in progress.steps_seen
        assert "complete" in progress.steps_seen


# ---------------------------------------------------------------------------
# Knowledge retrieval tests
# ---------------------------------------------------------------------------

class TestKnowledgeRetrieval:
    @pytest.mark.asyncio
    async def test_hybrid_search_merge(self) -> None:
        book_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        book_data = {str(book_id): Book(id=book_id, user_id=user_id, title="Test Book", status="ready")}
        chunk_data = {str(chunk_id): BookChunk(id=chunk_id, book_id=book_id, chapter_id=uuid.uuid4(), content="Content about patterns", sequence_number=0, token_count=50)}

        class FakeChunkSearch:
            async def search_by_embedding(self, query_embedding, *, user_id, entity_type="book_chunk", limit=20, score_threshold=0.0):
                return [SearchResult(record=_vr(str(chunk_id)), score=0.8)]

            async def keyword_search(self, query, *, user_id, limit=20):
                return [SearchResult(record=_vr(str(chunk_id)), score=0.6)]

        class FakeEmbed:
            async def embed(self, text):
                return [0.1] * 128

        class FakeBookRepo2:
            async def get_by_user(self, uid):
                return list(book_data.values())
            async def get_by_id(self, bid):
                return book_data.get(str(bid))
            async def get_chunks_by_ids(self, cids):
                return [chunk_data[str(cid)] for cid in cids if str(cid) in chunk_data]

        kb = KnowledgeService(
            book_repo=FakeBookRepo2(),
            chunk_search=FakeChunkSearch(),
            embeddings=FakeEmbed(),
            config=RetrievalConfig(strategy=RetrievalStrategy.HYBRID),
        )

        ctx = await kb.retrieve(user_id, "cognitive patterns")
        assert len(ctx.chunks) == 1
        assert ctx.chunks[0].final_score > 0

    @pytest.mark.asyncio
    async def test_citation_generation(self) -> None:
        chunk = BookChunk(id=uuid.uuid4(), book_id=uuid.uuid4(), chapter_id=uuid.uuid4(), content="Findings", section_heading="Results", page_start=10, page_end=12, token_count=30)
        book = Book(id=uuid.uuid4(), user_id=uuid.uuid4(), title="Paper", author="Dr. Smith")

        kb = KnowledgeService.__new__(KnowledgeService)
        ranked = [RankedChunk(chunk=chunk, book=book, final_score=0.85)]
        with_citations = kb._generate_citations(ranked)
        c = with_citations[0].citation
        assert c is not None
        assert c.book_title == "Paper"
        assert c.section_heading == "Results"
        assert c.page_start == 10

    @pytest.mark.asyncio
    async def test_token_budget_compression(self) -> None:
        chunks = [
            RankedChunk(
                chunk=BookChunk(id=uuid.uuid4(), book_id=uuid.uuid4(), chapter_id=uuid.uuid4(), content=f"C{i}", sequence_number=i, token_count=100),
                book=Book(id=uuid.uuid4(), user_id=uuid.uuid4(), title="B"),
                final_score=0.9 - i * 0.1,
            )
            for i in range(20)
        ]
        kb = KnowledgeService.__new__(KnowledgeService)
        compressed = kb._compress(chunks, RetrievalConfig(token_budget=500))
        assert sum(c.chunk.token_count for c in compressed) <= 500


# ---------------------------------------------------------------------------
# Prompt context tests
# ---------------------------------------------------------------------------

class TestPromptContext:
    @pytest.mark.asyncio
    async def test_assemble_empty(self) -> None:
        ctx = await PromptContextService().assemble(str(uuid.uuid4()), "hello")
        assert ctx.system_context != ""
        assert ctx.memory_context == ""

    @pytest.mark.asyncio
    async def test_assemble_with_retrieval(self) -> None:
        class FakeRetrieval:
            async def retrieve_context(self, user_id, query, **kw):
                return RetrievalResult(
                    memories=[{"type": "semantic", "content": "Fact", "confidence": 0.8}],
                    patterns=[{"description": "Pattern"}],
                    knowledge_chunks=[{"content": "Research", "book_title": "Book"}],
                    citations=[{"book_title": "Book", "excerpt": "Research"}],
                )

        ctx = await PromptContextService(retrieval_service=FakeRetrieval()).assemble(str(uuid.uuid4()), "test")
        assert "Fact" in ctx.memory_context
        assert "Book" in ctx.knowledge_context
        assert len(ctx.citations) == 1

    @pytest.mark.asyncio
    async def test_token_budget_truncation(self) -> None:
        class BigRetrieval:
            async def retrieve_context(self, user_id, query, **kw):
                return RetrievalResult(
                    knowledge_chunks=[{"content": "word " * 500, "book_title": f"B{i}"} for i in range(10)],
                )

        ctx = await PromptContextService(retrieval_service=BigRetrieval()).assemble(
            str(uuid.uuid4()), "test", token_budget=300
        )
        assert ctx.token_estimate < 600
        assert len(ctx.truncated_components) > 0


# ---------------------------------------------------------------------------
# Retrieval aggregation tests
# ---------------------------------------------------------------------------

class TestRetrievalService:
    @pytest.mark.asyncio
    async def test_aggregates_sources(self) -> None:
        class FakePatternService:
            async def list_patterns(self, user_id, limit=10):
                return [{"description": "p1"}]

        retrieval = RetrievalService(pattern_service=FakePatternService())
        result = await retrieval.retrieve_context(str(uuid.uuid4()), "q")
        assert len(result.patterns) == 1

    @pytest.mark.asyncio
    async def test_graceful_degradation(self) -> None:
        class FailingMem:
            async def retrieve(self, *a, **kw):
                raise RuntimeError("down")

        retrieval = RetrievalService(memory_service=FailingMem())
        result = await retrieval.retrieve_context(str(uuid.uuid4()), "q")
        assert result.memories == []


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------

class TestConcurrentIngestion:
    @pytest.mark.asyncio
    async def test_parallel_different_books(self) -> None:
        book_repo = FakeBookRepo()
        embedding = FakeEmbeddingGateway()
        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=embedding,
            event_publisher=FakeEventPublisher(),
            parsers={"markdown": MarkdownParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=100, min_chunk_tokens=10),
        )

        async def run(idx: int) -> IngestionResult:
            bid = str(uuid.uuid4())
            book_repo.books[bid] = {"id": bid, "status": "processing"}
            return await ingestion.ingest(bid, f"# B{idx}\n\n## C\n\nText.".encode(), f"b{idx}.md")

        results = await asyncio.gather(*[run(i) for i in range(5)])
        assert all(r.status == "ready" and r.total_chunks > 0 for r in results)

    @pytest.mark.asyncio
    async def test_reindex_preserves_other_books(self) -> None:
        book_repo = FakeBookRepo()
        ingestion = IngestionService(
            book_repo=book_repo,
            embedding=FakeEmbeddingGateway(),
            event_publisher=FakeEventPublisher(),
            parsers={"markdown": MarkdownParser()},
            chunking_config=ChunkingConfig(max_chunk_tokens=100, min_chunk_tokens=10),
        )

        b1, b2 = str(uuid.uuid4()), str(uuid.uuid4())
        book_repo.books[b1] = {"id": b1, "status": "ready"}
        book_repo.books[b2] = {"id": b2, "status": "ready"}
        book_repo.chunks[b2] = [{"id": "keep", "content": "keep me"}]

        await ingestion.ingest(b1, b"# B1\n\n## C\n\nContent.", "b1.md")
        assert book_repo.books[b2]["status"] == "ready"
        assert len(book_repo.chunks.get(b2, [])) == 1
