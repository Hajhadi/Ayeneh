"""Library API endpoints — wired to real services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ayeneh.api.deps import get_container
from ayeneh.infrastructure.persistence.models.book import BookModel

router = APIRouter()


class BookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    author: str | None = None
    source_format: str
    status: str = "processing"
    chunk_count: int = 0
    created_at: datetime
    indexed_at: datetime | None = None


class BookListResponse(BaseModel):
    data: list[BookResponse]
    total: int
    has_more: bool = False


class BookDetailResponse(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    user_id: str
    title: str
    author: str | None = None
    source_format: str
    status: str
    chunk_count: int
    created_at: datetime
    indexed_at: datetime | None = None


class UploadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_url: str | None = None
    source_format: str = "pdf"


class UploadResponse(BaseModel):
    id: str
    status: str
    message: str


class IndexingProgressResponse(BaseModel):
    book_id: str
    status: str
    chunks_total: int = 0
    chunks_indexed: int = 0
    progress_percent: float = 0.0


@router.post("/books", response_model=UploadResponse, status_code=201)
async def upload_book(body: UploadRequest, user: Any = None) -> dict:
    container = get_container()
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    if container.database:
        async with container.database.session_factory() as session:
            book = BookModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                title=body.title,
                author=None,
                source_format=body.source_format,
                source_url=body.source_url,
                status="processing",
                chunk_count=0,
                imported_at=now,
                created_at=now,
            )
            session.add(book)
            await session.commit()

            return {
                "id": str(book.id),
                "status": "processing",
                "message": "Book uploaded and queued for indexing",
            }

    return {
        "id": str(uuid.uuid4()),
        "status": "processing",
        "message": "Book uploaded (no database)",
    }


@router.get("/books", response_model=BookListResponse)
async def list_books(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    container = get_container()
    if not container.database:
        return {"data": [], "total": 0, "has_more": False}

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(BookModel)
            .where(BookModel.deleted_at.is_(None))
            .order_by(BookModel.created_at.desc())
            .limit(limit)
        )
        books = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(b.id),
                    "user_id": str(b.user_id),
                    "title": b.title,
                    "author": b.author,
                    "source_format": b.source_format,
                    "status": b.status,
                    "chunk_count": b.chunk_count,
                    "created_at": b.created_at,
                    "indexed_at": b.indexed_at,
                }
                for b in books
            ],
            "total": len(books),
            "has_more": False,
        }


@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "id": book_id,
            "user_id": "anon",
            "title": "",
            "source_format": "pdf",
            "status": "ready",
            "chunk_count": 0,
            "created_at": datetime.now(UTC),
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(BookModel).where(BookModel.id == uuid.UUID(book_id))
        )
        book = result.scalar_one_or_none()

        if not book:
            return {
                "id": book_id,
                "user_id": "anon",
                "title": "",
                "source_format": "pdf",
                "status": "ready",
                "chunk_count": 0,
                "created_at": datetime.now(UTC),
            }

        return {
            "id": str(book.id),
            "user_id": str(book.user_id),
            "title": book.title,
            "author": book.author,
            "source_format": book.source_format,
            "status": book.status,
            "chunk_count": book.chunk_count,
            "created_at": book.created_at,
            "indexed_at": book.indexed_at,
        }


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: str, user: Any = None) -> None:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(BookModel).where(BookModel.id == uuid.UUID(book_id))
            )
            book = result.scalar_one_or_none()
            if book:
                book.deleted_at = datetime.now(UTC)
                await session.commit()


@router.post("/books/{book_id}/reindex", status_code=202)
async def reindex_book(book_id: str, user: Any = None) -> dict:
    container = get_container()
    if container.database:
        async with container.database.session_factory() as session:
            result = await session.execute(
                select(BookModel).where(BookModel.id == uuid.UUID(book_id))
            )
            book = result.scalar_one_or_none()
            if book:
                book.status = "processing"
                await session.commit()

    return {"id": book_id, "status": "reindexing"}


@router.get("/books/{book_id}/progress", response_model=IndexingProgressResponse)
async def get_indexing_progress(book_id: str, user: Any = None) -> dict:
    container = get_container()
    if not container.database:
        return {
            "book_id": book_id,
            "status": "ready",
            "chunks_total": 0,
            "chunks_indexed": 0,
            "progress_percent": 100.0,
        }

    async with container.database.session_factory() as session:
        result = await session.execute(
            select(BookModel).where(BookModel.id == uuid.UUID(book_id))
        )
        book = result.scalar_one_or_none()

        if not book:
            return {
                "book_id": book_id,
                "status": "ready",
                "chunks_total": 0,
                "chunks_indexed": 0,
                "progress_percent": 100.0,
            }

        chunks_total = book.chunk_count
        chunks_indexed = chunks_total if book.status == "ready" else 0
        progress = 100.0 if book.status == "ready" else (chunks_indexed / chunks_total * 100 if chunks_total > 0 else 0)

        return {
            "book_id": book_id,
            "status": book.status,
            "chunks_total": chunks_total,
            "chunks_indexed": chunks_indexed,
            "progress_percent": progress,
        }
