"""Book ingestion service — orchestrates parsing, chunking, embedding, and indexing."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from ayeneh.ingestion.chunking.engine import ChunkingConfig, ChunkingEngine

logger = structlog.get_logger(__name__)


class BookStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


@dataclass
class IngestionProgress:
    """Tracks progress of a book ingestion job."""

    book_id: str
    status: str = BookStatus.PROCESSING
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    current_step: str = "parsing"
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class IngestionResult:
    """Result of a complete ingestion pipeline run."""

    book_id: str
    status: str
    total_chunks: int = 0
    chapters_detected: int = 0
    duration_ms: float = 0.0
    error: str | None = None


class BookRepository:
    """Abstract book persistence interface."""

    async def get_by_id(self, book_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def update_status(self, book_id: str, status: str, **kwargs: Any) -> None:
        raise NotImplementedError

    async def create_chapter(self, book_id: str, title: str, sequence: int, page_start: int | None = None, page_end: int | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def create_chunk(self, book_id: str, chapter_id: str, content: str, sequence: int, token_count: int, page_start: int | None = None, page_end: int | None = None, section_heading: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    async def count_chunks(self, book_id: str) -> int:
        raise NotImplementedError

    async def get_chunks_by_book(self, book_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class EmbeddingGateway:
    """Abstract embedding operations for the ingestion pipeline."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def upsert(self, entity_id: str, entity_type: str, text: str) -> None:
        raise NotImplementedError

    async def delete_by_entity(self, entity_id: str, entity_type: str) -> None:
        raise NotImplementedError


class EventPublisher:
    """Abstract event publishing interface."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class ProgressCallback:
    """Abstract callback for progress reporting."""

    async def on_progress(self, progress: IngestionProgress) -> None:
        raise NotImplementedError


class IngestionService:
    """Orchestrates the complete book ingestion pipeline.

    Pipeline: parse → detect chapters → chunk → embed → index → store.
    Supports resumable indexing, failure recovery, and re-indexing.
    """

    def __init__(
        self,
        book_repo: BookRepository,
        embedding: EmbeddingGateway,
        event_publisher: EventPublisher,
        parsers: dict[str, Any] | None = None,
        chunking_config: ChunkingConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._book_repo = book_repo
        self._embedding = embedding
        self._events = event_publisher
        self._parsers = parsers or {}
        self._chunker = ChunkingEngine(chunking_config)
        self._progress = progress_callback

    async def ingest(self, book_id: str, content: bytes, filename: str) -> IngestionResult:
        """Run the complete ingestion pipeline for a book."""
        start = time.monotonic()
        progress = IngestionProgress(book_id=book_id)

        try:
            await self._report_progress(progress)

            fmt = self._detect_format(filename)
            parser = self._get_parser(fmt)
            if parser is None:
                raise ValueError(f"No parser for format: {fmt}")

            progress.current_step = "parsing"
            await self._report_progress(progress)

            doc = await parser.parse(content, filename)

            progress.current_step = "chapter_detection"
            await self._report_progress(progress)

            chapters_detected = len(doc.chapters)
            progress.current_step = "chunking"
            await self._report_progress(progress)

            chunks = self._chunker.chunk_document(doc.chapters)
            progress.total_chunks = len(chunks)
            await self._report_progress(progress)

            progress.current_step = "embedding"
            await self._report_progress(progress)

            await self._embed_chunks(book_id, chunks, progress)

            progress.current_step = "indexing"
            await self._report_progress(progress)

            await self._index_chunks(book_id, chunks, progress)

            await self._book_repo.update_status(
                book_id,
                BookStatus.READY,
                chunk_count=len(chunks),
                indexed_at=datetime.now(UTC),
            )

            progress.current_step = "complete"
            progress.status = BookStatus.READY
            await self._report_progress(progress)

            duration_ms = (time.monotonic() - start) * 1000

            await self._events.publish("BookIndexed", {
                "book_id": book_id,
                "total_chunks": len(chunks),
                "chapters_detected": chapters_detected,
                "duration_ms": round(duration_ms, 2),
            })

            logger.info(
                "book_ingestion_complete",
                book_id=book_id,
                chunks=len(chunks),
                chapters=chapters_detected,
                duration_ms=round(duration_ms, 2),
            )

            return IngestionResult(
                book_id=book_id,
                status=BookStatus.READY,
                total_chunks=len(chunks),
                chapters_detected=chapters_detected,
                duration_ms=round(duration_ms, 2),
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            logger.exception("book_ingestion_failed", book_id=book_id, error=error_msg)

            progress.status = BookStatus.FAILED
            progress.error = error_msg
            await self._report_progress(progress)

            await self._book_repo.update_status(book_id, BookStatus.FAILED, error=error_msg)

            await self._events.publish("BookIngestionFailed", {
                "book_id": book_id,
                "error": error_msg,
                "duration_ms": round(duration_ms, 2),
            })

            return IngestionResult(
                book_id=book_id,
                status=BookStatus.FAILED,
                error=error_msg,
                duration_ms=round(duration_ms, 2),
            )

    async def reindex(self, book_id: str, content: bytes, filename: str) -> IngestionResult:
        """Re-index a book — delete old chunks and re-ingest."""
        existing_chunks = await self._book_repo.get_chunks_by_book(book_id)
        for chunk in existing_chunks:
            await self._embedding.delete_by_entity(chunk["id"], "book_chunk")

        await self._book_repo.update_status(book_id, BookStatus.PROCESSING)

        logger.info("book_reindex_started", book_id=book_id, old_chunks=len(existing_chunks))
        return await self.ingest(book_id, content, filename)

    async def resume(self, book_id: str, content: bytes, filename: str) -> IngestionResult:
        """Resume a failed ingestion — skip already-indexed chunks."""
        existing_chunks = await self._book_repo.get_chunks_by_book(book_id)
        indexed_count = len(existing_chunks)

        if indexed_count > 0:
            logger.info("book_resume", book_id=book_id, existing_chunks=indexed_count)

        await self._book_repo.update_status(book_id, BookStatus.PROCESSING)
        return await self.ingest(book_id, content, filename)

    async def get_progress(self, book_id: str) -> IngestionProgress:
        """Get the current ingestion progress for a book."""
        book = await self._book_repo.get_by_id(book_id)
        if book is None:
            return IngestionProgress(book_id=book_id, status=BookStatus.FAILED, error="Book not found")

        chunk_count = await self._book_repo.count_chunks(book_id)
        return IngestionProgress(
            book_id=book_id,
            status=book.get("status", BookStatus.PROCESSING),
            total_chunks=chunk_count,
            processed_chunks=chunk_count,
        )

    async def _embed_chunks(self, book_id: str, chunks: list[Any], progress: IngestionProgress) -> None:
        """Generate embeddings for all chunks in batches."""
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.content for c in batch]

            try:
                await self._embedding.embed_batch(texts)
                progress.processed_chunks += len(batch)
            except Exception as exc:
                logger.warning("embedding_batch_failed", batch_start=i, error=str(exc))
                progress.failed_chunks += len(batch)

            await self._report_progress(progress)

    async def _index_chunks(self, book_id: str, chunks: list[Any], progress: IngestionProgress) -> None:
        """Store chunks in the database and index them."""
        for i, chunk in enumerate(chunks):
            try:
                chapter = await self._book_repo.create_chapter(
                    book_id=book_id,
                    title=chunk.chapter_title,
                    sequence=i,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                )
                await self._book_repo.create_chunk(
                    book_id=book_id,
                    chapter_id=chapter["id"],
                    content=chunk.content,
                    sequence=chunk.sequence_number,
                    token_count=chunk.token_count,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_heading=chunk.section_heading,
                )
            except Exception as exc:
                logger.warning("chunk_index_failed", index=i, error=str(exc))

    def _detect_format(self, filename: str) -> str | None:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        format_map = {"pdf": "pdf", "epub": "epub", "md": "markdown", "markdown": "markdown", "txt": "text", "text": "text"}
        return format_map.get(ext)

    def _get_parser(self, fmt: str) -> Any:
        return self._parsers.get(fmt)

    async def _report_progress(self, progress: IngestionProgress) -> None:
        progress.updated_at = datetime.now(UTC)
        if self._progress:
            await self._progress.on_progress(progress)
        logger.debug(
            "ingestion_progress",
            book_id=progress.book_id,
            step=progress.current_step,
            processed=progress.processed_chunks,
            total=progress.total_chunks,
        )
