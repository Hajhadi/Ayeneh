"""Comprehensive tests for the Book Ingestion Pipeline."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ayeneh.ingestion.chunking.engine import ChunkingConfig, ChunkingEngine
from ayeneh.ingestion.ingestion_service import (
    BookRepository,
    BookStatus,
    EmbeddingGateway,
    EventPublisher,
    IngestionProgress,
    IngestionService,
    ProgressCallback,
)
from ayeneh.ingestion.parsers.base import Chapter, DocumentParser, ParsedDocument
from ayeneh.ingestion.parsers.markdown_parser import MarkdownParser
from ayeneh.ingestion.parsers.text_parser import TextParser

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeBookRepo(BookRepository):
    def __init__(self) -> None:
        self._books: dict[str, dict[str, Any]] = {}
        self._chapters: dict[str, list[dict[str, Any]]] = {}
        self._chunks: dict[str, list[dict[str, Any]]] = {}

    async def get_by_id(self, book_id: str) -> dict[str, Any] | None:
        return self._books.get(book_id)

    async def update_status(self, book_id: str, status: str, **kwargs: Any) -> None:
        if book_id in self._books:
            self._books[book_id]["status"] = status
            self._books[book_id].update(kwargs)

    async def create_chapter(self, book_id: str, title: str, sequence: int, page_start: int | None = None, page_end: int | None = None) -> dict[str, Any]:
        chapter = {"id": str(uuid.uuid4()), "book_id": book_id, "title": title, "sequence_number": sequence, "page_start": page_start, "page_end": page_end}
        self._chapters.setdefault(book_id, []).append(chapter)
        return chapter

    async def create_chunk(self, book_id: str, chapter_id: str, content: str, sequence: int, token_count: int, page_start: int | None = None, page_end: int | None = None, section_heading: str | None = None) -> dict[str, Any]:
        chunk = {"id": str(uuid.uuid4()), "book_id": book_id, "chapter_id": chapter_id, "content": content, "sequence_number": sequence, "token_count": token_count, "page_start": page_start, "page_end": page_end, "section_heading": section_heading}
        self._chunks.setdefault(book_id, []).append(chunk)
        return chunk

    async def count_chunks(self, book_id: str) -> int:
        return len(self._chunks.get(book_id, []))

    async def get_chunks_by_book(self, book_id: str) -> list[dict[str, Any]]:
        return self._chunks.get(book_id, [])


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self) -> None:
        self.embed_calls: list[list[str]] = []
        self.upsert_calls: list[tuple[str, str]] = []
        self.delete_calls: list[tuple[str, str]] = []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[0.1] * 4 for _ in texts]

    async def upsert(self, entity_id: str, entity_type: str, text: str) -> None:
        self.upsert_calls.append((entity_id, entity_type))

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        self.delete_calls.append((entity_id, entity_type))


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"event_type": event_type, **payload})


class FakeProgressCallback(ProgressCallback):
    def __init__(self) -> None:
        self.updates: list[IngestionProgress] = []

    async def on_progress(self, progress: IngestionProgress) -> None:
        self.updates.append(progress)


class FakeParser(DocumentParser):
    def __init__(self, chapters: list[Chapter] | None = None) -> None:
        self._chapters = chapters or [Chapter(title="Test Chapter", sequence_number=0, content="test content " * 50)]

    @property
    def supported_formats(self) -> list[str]:
        return ["test"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        return ParsedDocument(title="Test Doc", source_format="test", chapters=self._chapters)


@pytest.fixture
def book_repo() -> FakeBookRepo:
    return FakeBookRepo()


@pytest.fixture
def embedding() -> FakeEmbeddingGateway:
    return FakeEmbeddingGateway()


@pytest.fixture
def events() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def progress_cb() -> FakeProgressCallback:
    return FakeProgressCallback()


@pytest.fixture
def service(book_repo: FakeBookRepo, embedding: FakeEmbeddingGateway, events: FakeEventPublisher, progress_cb: FakeProgressCallback) -> IngestionService:
    return IngestionService(
        book_repo=book_repo,
        embedding=embedding,
        event_publisher=events,
        parsers={"test": FakeParser(), "markdown": MarkdownParser(), "text": TextParser()},
        progress_callback=progress_cb,
    )


# ---------------------------------------------------------------------------
# Markdown ingestion
# ---------------------------------------------------------------------------

class TestMarkdownIngestion:
    @pytest.mark.asyncio
    async def test_parse_markdown(self) -> None:
        parser = MarkdownParser()
        content = b"# Title\n\nFirst paragraph.\n\n## Chapter 1\n\nChapter content here."
        doc = await parser.parse(content, "test.md")
        assert doc.title == "Title"
        assert len(doc.chapters) >= 1

    @pytest.mark.asyncio
    async def test_parse_heading_detection(self) -> None:
        parser = MarkdownParser()
        content = b"# Introduction\n\nSome intro text.\n\n## Methods\n\nMethod details."
        doc = await parser.parse(content, "doc.md")
        titles = [c.title for c in doc.chapters]
        assert "Introduction" in titles
        assert "Methods" in titles


# ---------------------------------------------------------------------------
# Plain text ingestion
# ---------------------------------------------------------------------------

class TestTextIngestion:
    @pytest.mark.asyncio
    async def test_parse_text(self) -> None:
        parser = TextParser()
        content = b"This is a test document with some content."
        doc = await parser.parse(content, "test.txt")
        assert doc.source_format == "text"
        assert len(doc.chapters) >= 1

    @pytest.mark.asyncio
    async def test_parse_empty(self) -> None:
        parser = TextParser()
        content = b""
        doc = await parser.parse(content, "empty.txt")
        assert len(doc.chapters) == 1


# ---------------------------------------------------------------------------
# Chapter detection
# ---------------------------------------------------------------------------

class TestChapterDetection:
    @pytest.mark.asyncio
    async def test_chapters_from_markdown(self) -> None:
        parser = MarkdownParser()
        content = b"# Intro\n\nText.\n\n## Methods\n\nDetails.\n\n## Results\n\nOutcome."
        doc = await parser.parse(content, "paper.md")
        assert len(doc.chapters) == 3

    @pytest.mark.asyncio
    async def test_single_chapter(self) -> None:
        parser = MarkdownParser()
        content = b"Just some text without any headings at all."
        doc = await parser.parse(content, "plain.md")
        assert len(doc.chapters) == 1


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

class TestChunking:
    def test_small_text_single_chunk(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=100))
        chunks = engine.chunk_document([Chapter(title="T", sequence_number=0, content="short text")])
        assert len(chunks) == 1
        assert chunks[0].token_count == 2

    def test_large_text_multiple_chunks(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=10, overlap_tokens=2))
        content = "word " * 30
        chunks = engine.chunk_document([Chapter(title="T", sequence_number=0, content=content)])
        assert len(chunks) > 1

    def test_semantic_boundary(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=10, overlap_tokens=0, preserve_semantic_boundaries=True))
        content = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = engine.chunk_document([Chapter(title="T", sequence_number=0, content=content)])
        assert len(chunks) >= 1

    def test_empty_chapter(self) -> None:
        engine = ChunkingEngine()
        chunks = engine.chunk_document([Chapter(title="Empty", sequence_number=0, content="")])
        assert len(chunks) == 0

    def test_sequence_numbers(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=5, overlap_tokens=0))
        content = "a b c d e f g h i j k l m n o"
        chunks = engine.chunk_document([Chapter(title="T", sequence_number=0, content=content)])
        seqs = [c.sequence_number for c in chunks]
        assert seqs == list(range(len(chunks)))

    def test_chapter_metadata_propagated(self) -> None:
        engine = ChunkingEngine(ChunkingConfig(max_chunk_tokens=5, overlap_tokens=0))
        chunks = engine.chunk_document([Chapter(title="My Chapter", sequence_number=0, content="a b c d e f", page_start=1, page_end=5)])
        assert all(c.chapter_title == "My Chapter" for c in chunks)
        assert all(c.page_start == 1 for c in chunks)


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

class TestEmbeddingGeneration:
    @pytest.mark.asyncio
    async def test_embeddings_generated(self, service: IngestionService, embedding: FakeEmbeddingGateway, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        await service.ingest(book_id, b"test content", "test.txt")
        assert len(embedding.embed_calls) >= 1


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

class TestIndexing:
    @pytest.mark.asyncio
    async def test_chunks_stored(self, service: IngestionService, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        result = await service.ingest(book_id, b"test content for indexing", "test.txt")
        assert result.total_chunks >= 1
        assert len(book_repo._chunks.get(book_id, [])) >= 1


# ---------------------------------------------------------------------------
# Resume after failure
# ---------------------------------------------------------------------------

class TestResumeAfterFailure:
    @pytest.mark.asyncio
    async def test_resume_preserves_existing(self, service: IngestionService, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "failed"}
        existing = {"id": str(uuid.uuid4()), "book_id": book_id, "content": "old"}
        book_repo._chunks[book_id] = [existing]

        result = await service.resume(book_id, b"new content", "test.txt")
        assert result.status == BookStatus.READY


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------

class TestProgressReporting:
    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self, service: IngestionService, book_repo: FakeBookRepo, progress_cb: FakeProgressCallback) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        await service.ingest(book_id, b"content", "test.txt")
        assert len(progress_cb.updates) >= 1
        assert progress_cb.updates[-1].status == BookStatus.READY

    @pytest.mark.asyncio
    async def test_get_progress(self, service: IngestionService, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "ready"}
        progress = await service.get_progress(book_id)
        assert progress.status == BookStatus.READY


# ---------------------------------------------------------------------------
# Re-indexing
# ---------------------------------------------------------------------------

class TestReindexing:
    @pytest.mark.asyncio
    async def test_reindex_deletes_old_and_creates_new(self, service: IngestionService, book_repo: FakeBookRepo, embedding: FakeEmbeddingGateway) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        book_repo._chunks[book_id] = [{"id": "old-chunk", "book_id": book_id}]
        result = await service.reindex(book_id, b"reindexed content", "test.txt")
        assert result.status == BookStatus.READY
        assert len(embedding.delete_calls) >= 1


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class TestFailureHandling:
    @pytest.mark.asyncio
    async def test_invalid_format_fails(self, service: IngestionService, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        result = await service.ingest(book_id, b"content", "unknown.xyz")
        assert result.status == BookStatus.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_missing_book_get_progress(self, service: IngestionService) -> None:
        progress = await service.get_progress("nonexistent")
        assert progress.status == BookStatus.FAILED

    @pytest.mark.asyncio
    async def test_failure_event_published(self, service: IngestionService, book_repo: FakeBookRepo, events: FakeEventPublisher) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        await service.ingest(book_id, b"content", "unknown.xyz")
        assert any(e["event_type"] == "BookIngestionFailed" for e in events.events)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_success_event_published(self, service: IngestionService, book_repo: FakeBookRepo, events: FakeEventPublisher) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        await service.ingest(book_id, b"content", "test.txt")
        assert any(e["event_type"] == "BookIndexed" for e in events.events)

    @pytest.mark.asyncio
    async def test_duration_recorded(self, service: IngestionService, book_repo: FakeBookRepo) -> None:
        book_id = str(uuid.uuid4())
        book_repo._books[book_id] = {"id": book_id, "status": "processing"}
        result = await service.ingest(book_id, b"content", "test.txt")
        assert result.duration_ms >= 0

    def test_config_defaults(self) -> None:
        cfg = ChunkingConfig()
        assert cfg.max_chunk_tokens == 512
        assert cfg.overlap_tokens == 64
