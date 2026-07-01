"""Library service — manages book lifecycle, ingestion, and deletion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.infrastructure.persistence.models.book import (
    BookChapterModel,
    BookChunkModel,
    BookModel,
)

logger = structlog.get_logger(__name__)


class LibraryService:
    """Manages books through the repository layer via UnitOfWork."""

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def import_book(
        self,
        user_id: str,
        title: str,
        author: str | None = None,
        source_format: str = "unknown",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            book = BookModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                title=title,
                author=author,
                source_format=source_format,
                status="processing",
                chunk_count=0,
                created_at=now,
            )
            await uow.books.create(book)
            await uow.commit()
            return {
                "id": str(book.id),
                "title": book.title,
                "author": book.author,
                "status": book.status,
                "source_format": book.source_format,
            }

    async def get_book(self, book_id: str) -> dict[str, Any] | None:
        async with self._uow_factory() as uow:
            book = await uow.books.get_by_id(uuid.UUID(book_id))
            if book is None:
                return None
            return {
                "id": str(book.id),
                "title": book.title,
                "author": book.author,
                "status": book.status,
                "source_format": book.source_format,
                "chunk_count": book.chunk_count,
                "created_at": book.created_at.isoformat(),
            }

    async def list_books(self, user_id: str) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            books = await uow.books.list(
                filters={"user_id": uuid.UUID(user_id), "status": "ready"},
                limit=100,
            )
            return [
                {
                    "id": str(b.id),
                    "title": b.title,
                    "author": b.author,
                    "status": b.status,
                    "source_format": b.source_format,
                    "chunk_count": b.chunk_count,
                }
                for b in books
            ]

    async def update_book_status(
        self,
        book_id: str,
        status: str,
        *,
        chunk_count: int | None = None,
        indexed_at: datetime | None = None,
        error: str | None = None,
    ) -> None:
        async with self._uow_factory() as uow:
            book = await uow.books.get_by_id(uuid.UUID(book_id))
            if book:
                book.status = status
                if chunk_count is not None:
                    book.chunk_count = chunk_count
                if indexed_at:
                    book.indexed_at = indexed_at
                await uow.books.update(book)
                await uow.commit()

    async def create_chapter(
        self,
        book_id: str,
        title: str,
        sequence: int,
        page_start: int | None = None,
        page_end: int | None = None,
    ) -> dict[str, Any]:
        async with self._uow_factory() as uow:
            chapter = BookChapterModel(
                id=uuid.uuid4(),
                book_id=uuid.UUID(book_id),
                title=title,
                sequence_number=sequence,
                page_start=page_start,
                page_end=page_end,
            )
            await uow.books.create(chapter)
            await uow.flush()
            return {"id": str(chapter.id)}

    async def create_chunk(
        self,
        book_id: str,
        chapter_id: str,
        content: str,
        sequence: int,
        token_count: int,
        page_start: int | None = None,
        page_end: int | None = None,
        section_heading: str | None = None,
    ) -> dict[str, Any]:
        async with self._uow_factory() as uow:
            chunk = BookChunkModel(
                id=uuid.uuid4(),
                book_id=uuid.UUID(book_id),
                chapter_id=uuid.UUID(chapter_id),
                content=content,
                sequence_number=sequence,
                token_count=token_count,
                page_start=page_start,
                page_end=page_end,
                section_heading=section_heading,
            )
            await uow.books.create(chunk)
            await uow.flush()
            return {"id": str(chunk.id)}

    async def count_chunks(self, book_id: str) -> int:
        async with self._uow_factory() as uow:
            chunks = await uow.books.list(
                filters={"book_id": uuid.UUID(book_id)}
            )
            return len(chunks)

    async def get_chunks_by_book(self, book_id: str) -> list[dict[str, Any]]:
        async with self._uow_factory() as uow:
            from sqlalchemy import select
            stmt = (
                select(BookChunkModel)
                .where(BookChunkModel.book_id == uuid.UUID(book_id))
                .order_by(BookChunkModel.sequence_number)
            )
            result = await uow._session.execute(stmt)
            chunks = list(result.scalars().all())
            return [
                {
                    "id": str(c.id),
                    "book_id": str(c.book_id),
                    "chapter_id": str(c.chapter_id),
                    "content": c.content,
                    "sequence_number": c.sequence_number,
                    "token_count": c.token_count,
                    "section_heading": c.section_heading,
                }
                for c in chunks
            ]

    async def delete_book(self, book_id: str) -> None:
        async with self._uow_factory() as uow:
            await uow.books.delete(uuid.UUID(book_id))
            await uow.commit()

    async def count_books(self, user_id: str) -> int:
        async with self._uow_factory() as uow:
            return await uow.books.count(
                filters={"user_id": uuid.UUID(user_id), "status": "ready"}
            )
