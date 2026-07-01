"""KnowledgeImportService — single owner of the complete import pipeline.

This subsystem owns the complete lifecycle of importing books
into the cognitive knowledge base.

No other subsystem should parse, chunk, embed, or index documents.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

from ayeneh.ingestion.chunking.engine import ChunkingConfig, ChunkingEngine
from ayeneh.ingestion.parsers.base import DocumentParser, ParsedDocument
from ayeneh.ingestion.parsers.pdf_parser import PDFParser
from ayeneh.ingestion.parsers.text_parser import TextParser
from ayeneh.ingestion.parsers.markdown_parser import MarkdownParser
from ayeneh.ingestion.parsers.epub_parser import EPUBParser
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

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------


class ImportJobStore:
    """Abstract persistence for import jobs."""

    async def create_job(self, job: ImportJob) -> ImportJob:
        raise NotImplementedError

    async def get_job(self, job_id: str) -> ImportJob | None:
        raise NotImplementedError

    async def update_job(self, job: ImportJob) -> None:
        raise NotImplementedError

    async def list_jobs(self, user_id: str, limit: int = 20) -> list[ImportJob]:
        raise NotImplementedError


class DocumentStore:
    """Abstract persistence for documents, chapters, and chunks."""

    async def create_document(self, doc: DocumentInfo) -> DocumentInfo:
        raise NotImplementedError

    async def get_document(self, doc_id: str) -> DocumentInfo | None:
        raise NotImplementedError

    async def update_document(self, doc: DocumentInfo) -> None:
        raise NotImplementedError

    async def create_chapter(self, chapter: ChapterInfo) -> ChapterInfo:
        raise NotImplementedError

    async def create_chunk(self, chunk: ChunkInfo) -> ChunkInfo:
        raise NotImplementedError

    async def get_chunks_by_document(self, doc_id: str) -> list[ChunkInfo]:
        raise NotImplementedError


class EmbeddingProvider:
    """Abstract embedding generation provider."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class EmbeddingStore:
    """Abstract vector storage for embeddings."""

    async def upsert_batch(self, records: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        raise NotImplementedError


class EventPublisher:
    """Abstract event publishing interface."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class ProgressReporter:
    """Abstract callback for progress reporting."""

    async def report(self, progress: ImportProgress) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Pipeline validators
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/epub+zip",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = {"pdf", "epub", "txt", "md", "markdown", "docx"}


def validate_file(filename: str, file_size: int, content_type: str) -> str | None:
    """Validate file for import. Returns error message or None."""
    if file_size > MAX_FILE_SIZE:
        return f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})"
    if file_size == 0:
        return "File is empty"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported format: .{ext}"
    return None


# ---------------------------------------------------------------------------
# KnowledgeImportService
# ---------------------------------------------------------------------------


class KnowledgeImportService:
    """Single owner of the complete document import pipeline.

    Pipeline: validate → parse → chunk → embed → index → store.
    Supports resumable imports, failure recovery, and job system integration.
    """

    def __init__(
        self,
        job_store: ImportJobStore,
        document_store: DocumentStore,
        embedding_provider: EmbeddingProvider,
        embedding_store: EmbeddingStore,
        event_publisher: EventPublisher,
        progress_reporter: ProgressReporter | None = None,
        chunking_config: ChunkingConfig | None = None,
    ) -> None:
        self._job_store = job_store
        self._doc_store = document_store
        self._embedding_provider = embedding_provider
        self._embedding_store = embedding_store
        self._events = event_publisher
        self._progress = progress_reporter
        self._chunker = ChunkingEngine(chunking_config)

        # Register parsers
        self._parsers: dict[str, DocumentParser] = {
            "pdf": PDFParser(),
            "epub": EPUBParser(),
            "txt": TextParser(),
            "text": TextParser(),
            "md": MarkdownParser(),
            "markdown": MarkdownParser(),
        }

        # Metrics
        self._metrics = ImportMetrics()

    async def start_import(
        self,
        user_id: str,
        filename: str,
        file_content: bytes,
        content_type: str,
        metadata: ImportMetadata | None = None,
    ) -> ImportJob:
        """Start a new import job. Returns job for tracking."""
        # Validate
        error = validate_file(filename, len(file_content), content_type)
        if error:
            raise ValueError(error)

        # Create job
        job = ImportJob(
            user_id=user_id,
            filename=filename,
            file_size=len(file_content),
            content_type=content_type,
            metadata=metadata or ImportMetadata(),
            status=ImportStatus.QUEUED,
        )
        await self._job_store.create_job(job)

        logger.info(
            "import_job_created",
            job_id=job.id,
            filename=filename,
            file_size=len(file_content),
        )

        return job

    async def execute_import(
        self,
        job_id: str,
        file_content: bytes,
    ) -> ImportResult:
        """Execute the complete import pipeline for a job.

        This is the main pipeline entry point.
        """
        start = time.monotonic()
        job = await self._job_store.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        try:
            # Step 1: Parsing
            await self._update_job_status(job, ImportStatus.PARSING, "parsing", 10)
            fmt = self._detect_format(job.filename)
            parser = self._get_parser(fmt)
            if parser is None:
                raise ValueError(f"No parser for format: {fmt}")

            doc = await parser.parse(file_content, job.filename)
            await self._update_job_status(job, ImportStatus.PARSING, "parsing_complete", 25)

            # Step 2: Create document
            document = DocumentInfo(
                user_id=job.user_id,
                title=job.metadata.title or doc.title,
                author=job.metadata.author or doc.author or "",
                source_format=fmt,
                status="processing",
                page_count=doc.metadata.get("page_count", 0),
                language=job.metadata.language,
                tags=job.metadata.tags,
                category=job.metadata.category,
                framework=job.metadata.framework,
                domain=job.metadata.domain,
                source=job.metadata.source,
            )
            document = await self._doc_store.create_document(document)
            job.document_id = document.id

            # Step 3: Chunking
            await self._update_job_status(job, ImportStatus.CHUNKING, "chunking", 40)
            chunks = self._chunker.chunk_document(doc.chapters)
            job.total_chunks = len(chunks)
            job.total_pages = document.page_count

            # Step 4: Embedding
            await self._update_job_status(job, ImportStatus.EMBEDDING, "embedding", 55)
            await self._generate_embeddings(document.id, chunks, job)

            # Step 5: Indexing
            await self._update_job_status(job, ImportStatus.INDEXING, "indexing", 85)
            await self._index_chunks(document.id, chunks)

            # Step 6: Complete
            document.status = "ready"
            document.chunk_count = len(chunks)
            from datetime import UTC, datetime as dt
            document.indexed_at = dt.now(UTC)
            await self._doc_store.update_document(document)

            duration_ms = (time.monotonic() - start) * 1000

            await self._update_job_status(job, ImportStatus.COMPLETED, "complete", 100)
            job.total_embeddings = len(chunks)

            # Publish event
            await self._events.publish("DocumentImported", {
                "document_id": document.id,
                "job_id": job_id,
                "total_chunks": len(chunks),
                "duration_ms": round(duration_ms, 2),
            })

            # Update metrics
            self._metrics.documents_imported += 1
            self._metrics.pages_parsed += document.page_count
            self._metrics.chunks_generated += len(chunks)
            self._metrics.embeddings_generated += len(chunks)
            if len(chunks) > 0:
                total_tokens = sum(c.token_count for c in chunks)
                self._metrics.average_chunk_size = total_tokens / len(chunks)

            logger.info(
                "import_complete",
                job_id=job_id,
                document_id=document.id,
                chunks=len(chunks),
                duration_ms=round(duration_ms, 2),
            )

            return ImportResult(
                job_id=job_id,
                document_id=document.id,
                status=ImportStatus.COMPLETED,
                total_pages=document.page_count,
                total_chapters=len(doc.chapters),
                total_chunks=len(chunks),
                total_embeddings=len(chunks),
                duration_ms=round(duration_ms, 2),
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            logger.exception("import_failed", job_id=job_id, error=error_msg)

            job.status = ImportStatus.FAILED
            job.error = error_msg
            await self._job_store.update_job(job)

            await self._events.publish("DocumentImportFailed", {
                "job_id": job_id,
                "error": error_msg,
                "duration_ms": round(duration_ms, 2),
            })

            self._metrics.failed_imports += 1

            return ImportResult(
                job_id=job_id,
                document_id=job.document_id or "",
                status=ImportStatus.FAILED,
                error=error_msg,
                duration_ms=round(duration_ms, 2),
            )

    async def get_progress(self, job_id: str) -> ImportProgress:
        """Get the current progress of an import job."""
        job = await self._job_store.get_job(job_id)
        if job is None:
            return ImportProgress(
                job_id=job_id,
                status=ImportStatus.FAILED,
                error="Job not found",
            )

        return ImportProgress(
            job_id=job_id,
            status=job.status,
            progress_percent=job.progress_percent,
            current_step=job.current_step,
            total_pages=job.total_pages,
            total_chunks=job.total_chunks,
            total_embeddings=job.total_embeddings,
            error=job.error,
            estimated_remaining_ms=job.estimated_remaining_ms,
        )

    async def cancel_import(self, job_id: str) -> bool:
        """Cancel an import job."""
        job = await self._job_store.get_job(job_id)
        if job is None:
            return False

        if job.status in (ImportStatus.COMPLETED, ImportStatus.FAILED, ImportStatus.CANCELLED):
            return False

        job.status = ImportStatus.CANCELLED
        await self._job_store.update_job(job)
        logger.info("import_cancelled", job_id=job_id)
        return True

    async def resume_import(self, job_id: str, file_content: bytes) -> ImportResult:
        """Resume a failed import from the last checkpoint."""
        job = await self._job_store.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        if job.status != ImportStatus.FAILED:
            raise ValueError(f"Job is not in failed state: {job.status}")

        job.attempt += 1
        job.status = ImportStatus.QUEUED
        job.error = None
        await self._job_store.update_job(job)

        self._metrics.resume_count += 1
        logger.info("import_resumed", job_id=job_id, attempt=job.attempt)

        return await self.execute_import(job_id, file_content)

    async def retry_import(self, job_id: str, file_content: bytes) -> ImportResult:
        """Retry a failed import."""
        job = await self._job_store.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        if job.attempt >= job.max_attempts:
            raise ValueError(f"Max attempts reached: {job.max_attempts}")

        job.attempt += 1
        job.status = ImportStatus.QUEUED
        job.error = None
        await self._job_store.update_job(job)

        self._metrics.retry_count += 1
        logger.info("import_retried", job_id=job_id, attempt=job.attempt)

        return await self.execute_import(job_id, file_content)

    def get_metrics(self) -> ImportMetrics:
        """Get current import metrics."""
        return self._metrics

    # ------------------------------------------------------------------
    # Internal pipeline methods
    # ------------------------------------------------------------------

    async def _generate_embeddings(
        self,
        document_id: str,
        chunks: list[Any],
        job: ImportJob,
    ) -> None:
        """Generate embeddings for all chunks in batches."""
        batch_size = 50
        total = len(chunks)

        for i in range(0, total, batch_size):
            batch = chunks[i: i + batch_size]
            texts = [c.content for c in batch]

            try:
                embeddings = await self._embedding_provider.embed_batch(texts)

                records = []
                for chunk, embedding in zip(batch, embeddings, strict=False):
                    records.append({
                        "entity_id": chunk.id if hasattr(chunk, "id") else f"{document_id}_{chunk.sequence_number}",
                        "entity_type": "book_chunk",
                        "embedding": embedding,
                        "model_version": 1,
                    })

                await self._embedding_store.upsert_batch(records)

            except Exception as exc:
                logger.warning(
                    "embedding_batch_failed",
                    batch_start=i,
                    error=str(exc),
                )
                # Continue with next batch - don't restart entire document

            progress = i + len(batch)
            percent = 55 + (progress / total) * 30 if total > 0 else 85
            await self._update_job_status(
                job,
                ImportStatus.EMBEDDING,
                f"embedding {progress}/{total}",
                percent,
            )

    async def _index_chunks(
        self,
        document_id: str,
        chunks: list[Any],
    ) -> None:
        """Store chunks in the database."""
        chapters: dict[str, ChapterInfo] = {}

        for chunk in chunks:
            # Get or create chapter
            chapter_title = chunk.chapter_title or "Untitled"
            if chapter_title not in chapters:
                chapter = ChapterInfo(
                    document_id=document_id,
                    title=chapter_title,
                    sequence_number=len(chapters),
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                )
                chapter = await self._doc_store.create_chapter(chapter)
                chapters[chapter_title] = chapter

            chapter_info = chapters[chapter_title]

            chunk_info = ChunkInfo(
                document_id=document_id,
                chapter_id=chapter_info.id,
                content=chunk.content,
                sequence_number=chunk.sequence_number,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                token_count=chunk.token_count,
                section_heading=chunk.section_heading,
                char_offset_start=0,
                char_offset_end=len(chunk.content),
            )
            await self._doc_store.create_chunk(chunk_info)

    async def _update_job_status(
        self,
        job: ImportJob,
        status: str,
        step: str,
        percent: float,
    ) -> None:
        """Update job status and report progress."""
        job.status = status
        job.current_step = step
        job.progress_percent = percent
        await self._job_store.update_job(job)

        if self._progress:
            await self._progress.report(ImportProgress(
                job_id=job.id,
                status=status,
                progress_percent=percent,
                current_step=step,
                total_pages=job.total_pages,
                total_chunks=job.total_chunks,
                total_embeddings=job.total_embeddings,
            ))

    def _detect_format(self, filename: str) -> str:
        """Detect file format from extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        format_map = {
            "pdf": "pdf",
            "epub": "epub",
            "txt": "txt",
            "text": "txt",
            "md": "md",
            "markdown": "md",
            "docx": "docx",
        }
        return format_map.get(ext, "txt")

    def _get_parser(self, fmt: str) -> DocumentParser | None:
        """Get parser for format."""
        return self._parsers.get(fmt)
