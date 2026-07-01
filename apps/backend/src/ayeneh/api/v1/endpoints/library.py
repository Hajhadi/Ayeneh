"""Library API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

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
    book_id = str(uuid.uuid4())
    return {
        "id": book_id,
        "status": "processing",
        "message": "Book uploaded and queued for indexing",
    }


@router.get("/books", response_model=BookListResponse)
async def list_books(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    user: Any = None,
) -> dict:
    return {"data": [], "total": 0, "has_more": False}


@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: str, user: Any = None) -> dict:
    return {
        "id": book_id,
        "user_id": getattr(user, "id", "anon"),
        "title": "",
        "source_format": "pdf",
        "status": "ready",
        "chunk_count": 0,
        "created_at": datetime.utcnow(),
    }


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: str, user: Any = None) -> None:
    pass


@router.post("/books/{book_id}/reindex", status_code=202)
async def reindex_book(book_id: str, user: Any = None) -> dict:
    return {"id": book_id, "status": "reindexing"}


@router.get("/books/{book_id}/progress", response_model=IndexingProgressResponse)
async def get_indexing_progress(book_id: str, user: Any = None) -> dict:
    return {
        "book_id": book_id,
        "status": "ready",
        "chunks_total": 0,
        "chunks_indexed": 0,
        "progress_percent": 100.0,
    }
