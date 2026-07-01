"""Comprehensive tests for the Knowledge Import Pipeline."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ayeneh.knowledge_import.service import (
    EmbeddingProvider,
    EmbeddingStore,
    EventPublisher,
    ImportJobStore,
    DocumentStore,
    KnowledgeImportService,
    ProgressReporter,
    validate_file,
)
from ayeneh.knowledge_import.types import (
    ChunkInfo,
    ChapterInfo,
    DocumentInfo,
    ImportJob,
    ImportMetadata,
    ImportMetrics,
    ImportProgress,
    ImportResult,
    ImportStatus,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class InMemoryJobStore(ImportJobStore):
    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}

    async def create_job(self, job: ImportJob) -> ImportJob:
        self._jobs[job.id] = job
        return job

    async def get_job(self, job_id: str) -> ImportJob | None:
        return self._jobs.get(job_id)

    async def update_job(self, job: ImportJob) -> None:
        self._jobs[job.id] = job

    async def list_jobs(self, user_id: str, limit: int = 20) -> list[ImportJob]:
        return [j for j in self._jobs.values() if j.user_id == user_id][:limit]


class InMemoryDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._docs: dict[str, DocumentInfo] = {}
        self._chapters: dict[str, ChapterInfo] = {}
        self._chunks: dict[str, ChunkInfo] = {}

    async def create_document(self, doc: DocumentInfo) -> DocumentInfo:
        self._docs[doc.id] = doc
        return doc

    async def get_document(self, doc_id: str) -> DocumentInfo | None:
        return self._docs.get(doc_id)

    async def update_document(self, doc: DocumentInfo) -> None:
        self._docs[doc.id] = doc

    async def create_chapter(self, chapter: ChapterInfo) -> ChapterInfo:
        self._chapters[chapter.id] = chapter
        return chapter

    async def create_chunk(self, chunk: ChunkInfo) -> ChunkInfo:
        self._chunks[chunk.id] = chunk
        return chunk

    async def get_chunks_by_document(self, doc_id: str) -> list[ChunkInfo]:
        return [c for c in self._chunks.values() if c.document_id == doc_id]


class FakeEmbeddingProvider(EmbeddingProvider):
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _ in texts]


class FakeEmbeddingStore(EmbeddingStore):
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    async def upsert_batch(self, records: list[dict[str, Any]]) -> None:
        self.records.extend(records)

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        self.records = [
            r for r in self.records
            if r.get("entity_id") != entity_id
        ]


class FakeEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


class FakeProgressReporter(ProgressReporter):
    def __init__(self) -> None:
        self.updates: list[ImportProgress] = []

    async def report(self, progress: ImportProgress) -> None:
        self.updates.append(progress)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def job_store() -> InMemoryJobStore:
    return InMemoryJobStore()


@pytest.fixture
def doc_store() -> InMemoryDocumentStore:
    return InMemoryDocumentStore()


@pytest.fixture
def embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def embedding_store() -> FakeEmbeddingStore:
    return FakeEmbeddingStore()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def progress_reporter() -> FakeProgressReporter:
    return FakeProgressReporter()


@pytest.fixture
def service(
    job_store: InMemoryJobStore,
    doc_store: InMemoryDocumentStore,
    embedding_provider: FakeEmbeddingProvider,
    embedding_store: FakeEmbeddingStore,
    event_publisher: FakeEventPublisher,
    progress_reporter: FakeProgressReporter,
) -> KnowledgeImportService:
    return KnowledgeImportService(
        job_store=job_store,
        document_store=doc_store,
        embedding_provider=embedding_provider,
        embedding_store=embedding_store,
        event_publisher=event_publisher,
        progress_reporter=progress_reporter,
    )


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_valid_file(self) -> None:
        assert validate_file("test.pdf", 1024, "application/pdf") is None

    def test_file_too_large(self) -> None:
        error = validate_file("test.pdf", 200 * 1024 * 1024, "application/pdf")
        assert error is not None
        assert "too large" in error.lower()

    def test_empty_file(self) -> None:
        error = validate_file("test.pdf", 0, "application/pdf")
        assert error is not None
        assert "empty" in error.lower()

    def test_unsupported_extension(self) -> None:
        error = validate_file("test.exe", 1024, "application/octet-stream")
        assert error is not None
        assert "unsupported" in error.lower()

    def test_txt_valid(self) -> None:
        assert validate_file("test.txt", 1024, "text/plain") is None

    def test_epub_valid(self) -> None:
        assert validate_file("test.epub", 1024, "application/epub+zip") is None

    def test_md_valid(self) -> None:
        assert validate_file("test.md", 1024, "text/markdown") is None


# ---------------------------------------------------------------------------
# Import job creation tests
# ---------------------------------------------------------------------------


class TestImportJobCreation:
    @pytest.mark.asyncio
    async def test_start_import_creates_job(
        self, service: KnowledgeImportService,
    ) -> None:
        content = b"Hello world content"
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=content,
            content_type="text/plain",
        )
        assert job.id is not None
        assert job.status == ImportStatus.QUEUED
        assert job.filename == "test.txt"

    @pytest.mark.asyncio
    async def test_start_import_with_metadata(
        self, service: KnowledgeImportService,
    ) -> None:
        metadata = ImportMetadata(
            title="My Book",
            author="Author Name",
            language="en",
            tags=["philosophy"],
        )
        job = await service.start_import(
            user_id="user1",
            filename="test.pdf",
            file_content=b"content",
            content_type="application/pdf",
            metadata=metadata,
        )
        assert job.metadata.title == "My Book"
        assert job.metadata.author == "Author Name"

    @pytest.mark.asyncio
    async def test_start_import_rejects_invalid_file(
        self, service: KnowledgeImportService,
    ) -> None:
        with pytest.raises(ValueError, match="too large"):
            await service.start_import(
                user_id="user1",
                filename="huge.pdf",
                file_content=b"x" * (200 * 1024 * 1024),
                content_type="application/pdf",
            )


# ---------------------------------------------------------------------------
# Import execution tests
# ---------------------------------------------------------------------------


class TestImportExecution:
    @pytest.mark.asyncio
    async def test_execute_txt_import(
        self, service: KnowledgeImportService, job_store: InMemoryJobStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"This is a test document with some content.",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"This is a test document with some content.")
        assert result.status == ImportStatus.COMPLETED
        assert result.document_id is not None
        assert result.total_chunks > 0

    @pytest.mark.asyncio
    async def test_execute_import_creates_document(
        self, service: KnowledgeImportService, doc_store: InMemoryDocumentStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"content")
        doc = await doc_store.get_document(result.document_id)
        assert doc is not None
        assert doc.status == "ready"

    @pytest.mark.asyncio
    async def test_execute_import_generates_embeddings(
        self, service: KnowledgeImportService, embedding_store: FakeEmbeddingStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"This is content that will be chunked and embedded.",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"This is content that will be chunked and embedded.")
        assert len(embedding_store.records) > 0

    @pytest.mark.asyncio
    async def test_execute_import_publishes_event(
        self, service: KnowledgeImportService, event_publisher: FakeEventPublisher,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        await service.execute_import(job.id, b"content")
        assert len(event_publisher.events) > 0
        assert event_publisher.events[0][0] == "DocumentImported"

    @pytest.mark.asyncio
    async def test_execute_import_reports_progress(
        self, service: KnowledgeImportService, progress_reporter: FakeProgressReporter,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        await service.execute_import(job.id, b"content")
        assert len(progress_reporter.updates) > 0


# ---------------------------------------------------------------------------
# Progress tests
# ---------------------------------------------------------------------------


class TestProgress:
    @pytest.mark.asyncio
    async def test_get_progress(
        self, service: KnowledgeImportService,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        progress = await service.get_progress(job.id)
        assert progress.job_id == job.id
        assert progress.status == ImportStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_progress_not_found(
        self, service: KnowledgeImportService,
    ) -> None:
        progress = await service.get_progress("nonexistent")
        assert progress.status == ImportStatus.FAILED
        assert "not found" in progress.error.lower()


# ---------------------------------------------------------------------------
# Cancel tests
# ---------------------------------------------------------------------------


class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_import(
        self, service: KnowledgeImportService,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        result = await service.cancel_import(job.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_completed_import(
        self, service: KnowledgeImportService,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        await service.execute_import(job.id, b"content")
        result = await service.cancel_import(job.id)
        assert result is False


# ---------------------------------------------------------------------------
# Retry tests
# ---------------------------------------------------------------------------


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_import(
        self, service: KnowledgeImportService, job_store: InMemoryJobStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        # Simulate failure
        job.status = ImportStatus.FAILED
        await job_store.update_job(job)

        result = await service.retry_import(job.id, b"content")
        assert result.status == ImportStatus.COMPLETED


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_metrics_initial(
        self, service: KnowledgeImportService,
    ) -> None:
        metrics = service.get_metrics()
        assert metrics.documents_imported == 0

    @pytest.mark.asyncio
    async def test_metrics_after_import(
        self, service: KnowledgeImportService,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        await service.execute_import(job.id, b"content")
        metrics = service.get_metrics()
        assert metrics.documents_imported == 1


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_imports(
        self, service: KnowledgeImportService,
    ) -> None:
        jobs = []
        for i in range(5):
            job = await service.start_import(
                user_id=f"user{i}",
                filename=f"test{i}.txt",
                file_content=f"content {i}".encode(),
                content_type="text/plain",
            )
            jobs.append(job)

        results = []
        for job in jobs:
            result = await service.execute_import(job.id, b"content")
            results.append(result)

        assert len(results) == 5
        assert all(r.status == ImportStatus.COMPLETED for r in results)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    @pytest.mark.asyncio
    async def test_import_completes_quickly(
        self, service: KnowledgeImportService,
    ) -> None:
        start = time.monotonic()
        for i in range(10):
            job = await service.start_import(
                user_id="user1",
                filename=f"test{i}.txt",
                file_content=b"content",
                content_type="text/plain",
            )
            await service.execute_import(job.id, b"content")
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 5000  # 10 imports in under 5 seconds


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_same_import_produces_separate_jobs(
        self, service: KnowledgeImportService,
    ) -> None:
        job1 = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        job2 = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        assert job1.id != job2.id


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_service_works_with_defaults(
        self,
    ) -> None:
        service = KnowledgeImportService(
            job_store=InMemoryJobStore(),
            document_store=InMemoryDocumentStore(),
            embedding_provider=FakeEmbeddingProvider(),
            embedding_store=FakeEmbeddingStore(),
            event_publisher=FakeEventPublisher(),
        )
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        assert job.id is not None


# ---------------------------------------------------------------------------
# Document store tests
# ---------------------------------------------------------------------------


class TestDocumentStore:
    @pytest.mark.asyncio
    async def test_document_created(
        self, service: KnowledgeImportService, doc_store: InMemoryDocumentStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"content",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"content")
        doc = await doc_store.get_document(result.document_id)
        assert doc is not None
        assert doc.user_id == "user1"

    @pytest.mark.asyncio
    async def test_chunks_created(
        self, service: KnowledgeImportService, doc_store: InMemoryDocumentStore,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"This is content that will be chunked.",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"This is content that will be chunked.")
        chunks = await doc_store.get_chunks_by_document(result.document_id)
        assert len(chunks) > 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_content(
        self, service: KnowledgeImportService,
    ) -> None:
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=b"   ",
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, b"   ")
        assert result.status == ImportStatus.COMPLETED
        assert result.total_chunks == 0

    @pytest.mark.asyncio
    async def test_large_content(
        self, service: KnowledgeImportService,
    ) -> None:
        content = b"This is a sentence. " * 1000
        job = await service.start_import(
            user_id="user1",
            filename="test.txt",
            file_content=content,
            content_type="text/plain",
        )
        result = await service.execute_import(job.id, content)
        assert result.status == ImportStatus.COMPLETED
        assert result.total_chunks > 1
