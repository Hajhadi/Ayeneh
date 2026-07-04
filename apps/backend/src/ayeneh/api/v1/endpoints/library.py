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
    author: str | None = None
    source_url: str | None = None
    source_format: str = "txt"


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
    import sqlite3
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    book_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    cursor.execute(
        "INSERT INTO books (id, user_id, title, author, source_format, status, chunk_count, metadata, imported_at, created_at, deleted_at) "
        "VALUES (?, ?, ?, ?, ?, 'processing', 0, '{}', ?, ?, NULL)",
        (book_id, str(uuid.uuid4()), body.title, body.author, body.source_format, now, now),
    )
    conn.commit()
    conn.close()

    return {
        "id": book_id,
        "status": "processing",
        "message": "Book created successfully",
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


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    q: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_id: str
    book_title: str
    chapter_title: str
    content: str
    score: float


@router.get("/search")
async def search_books(q: str = Query(..., min_length=1, max_length=500), limit: int = Query(default=10, ge=1, le=50)) -> dict:
    import sqlite3
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = [w.strip() for w in q.split() if len(w.strip()) >= 2]
    if not keywords:
        conn.close()
        return {"results": [], "total": 0}

    conditions = " OR ".join(["bc.content LIKE ?" for _ in keywords])
    search_terms = [f"%{kw}%" for kw in keywords]

    cursor.execute(
        f"SELECT bc.id, b.title, COALESCE(ch.title, ''), bc.content, "
        f"bc.token_count "
        f"FROM book_chunks bc "
        f"JOIN books b ON bc.book_id = b.id "
        f"LEFT JOIN book_chapters ch ON bc.chapter_id = ch.id "
        f"WHERE bc.deleted_at IS NULL AND b.deleted_at IS NULL AND ({conditions}) "
        f"ORDER BY bc.token_count DESC "
        f"LIMIT ?",
        (*search_terms, limit),
    )

    results = []
    for row in cursor.fetchall():
        match_count = sum(1 for kw in keywords if kw.lower() in (row[3] or '').lower())
        score = min(1.0, match_count / max(len(keywords), 1) + 0.2)

        content = row[3] or ""
        content_lower = content.lower()
        best_pos = -1
        for kw in keywords:
            pos = content_lower.find(kw.lower())
            if pos >= 0:
                best_pos = pos
                break

        if best_pos >= 0:
            start = max(0, best_pos - 100)
            end = min(len(content), best_pos + 300)
            snippet = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
        else:
            snippet = content[:400]

        results.append({
            "chunk_id": row[0],
            "book_title": row[1],
            "chapter_title": row[2],
            "content": snippet,
            "score": round(score, 2),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return {"results": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Manual text endpoint (for books with failed PDF extraction)
# ---------------------------------------------------------------------------

class ManualTextRequest(BaseModel):
    content: str = Field(min_length=10, max_length=500000)
    generate_profile: bool = True


@router.post("/books/{book_id}/text", status_code=200)
async def add_book_text(book_id: str, body: ManualTextRequest) -> dict:
    import sqlite3
    import json
    from datetime import UTC, datetime

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Verify book exists
    cursor.execute("SELECT title, author FROM books WHERE id = ? AND deleted_at IS NULL", (book_id,))
    book_row = cursor.fetchone()
    if not book_row:
        conn.close()
        return {"error": "Book not found", "book_id": book_id}

    now = datetime.now(UTC).isoformat()

    # Soft-delete old chapters and chunks
    cursor.execute("UPDATE book_chapters SET deleted_at = ? WHERE book_id = ? AND deleted_at IS NULL", (now, book_id))
    cursor.execute("UPDATE book_chunks SET deleted_at = ? WHERE book_id = ? AND deleted_at IS NULL", (now, book_id))

    # Chunk the text
    words = body.content.split()
    chunk_size = 800
    overlap = 100
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())

    # Create chapters and chunks
    for idx, ct in enumerate(chunks):
        chapter_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        tc = len(ct.split())

        cursor.execute(
            "INSERT INTO book_chapters (id, book_id, title, sequence_number, page_start, page_end, created_at, deleted_at) "
            "VALUES (?, ?, ?, ?, 0, 0, ?, NULL)",
            (chapter_id, book_id, f"Chapter {idx + 1}", idx + 1, now),
        )
        cursor.execute(
            "INSERT INTO book_chunks (id, book_id, chapter_id, content, sequence_number, page_start, page_end, section_heading, token_count, created_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, 0, 0, '', ?, ?, NULL)",
            (chunk_id, book_id, chapter_id, ct, idx + 1, tc, now),
        )

    # Update book chunk count
    cursor.execute("UPDATE books SET chunk_count = ? WHERE id = ?", (len(chunks), book_id))

    profile_result = None
    if body.generate_profile and chunks:
        from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
        from ayeneh.domain.knowledge_epistemics.generator.types import DocumentContext

        generator = RuleBasedProfileGenerator()
        doc_context = DocumentContext(
            document_id=book_id,
            title=book_row[0] or "Unknown",
            author=book_row[1] or "Unknown",
            language="en",
            chapters=[{"content": ct[:2000], "token_count": len(ct.split())} for ct in chunks],
            total_chunks=len(chunks),
        )

        profile, metadata = generator.generate(doc_context, book_id, "00000000-0000-0000-0000-000000000001")
        validation = generator.validate(profile)

        def to_str(val) -> str:
            if val is None: return ""
            if hasattr(val, "value"): return val.value
            return str(val)

        # Upsert profile
        cursor.execute("SELECT id FROM epistemic_profiles WHERE book_id = ? AND deleted_at IS NULL", (book_id,))
        existing = cursor.fetchone()
        pid = str(profile.id) if isinstance(profile.id, uuid.UUID) else str(profile.id)

        vals = (
            to_str(profile.tradition), to_str(profile.framework), to_str(profile.discipline),
            json.dumps(profile.primary_topics or []), json.dumps(profile.secondary_topics or []),
            to_str(profile.evidence_level), to_str(profile.reasoning_style), to_str(profile.authority),
            json.dumps([v.value if hasattr(v, "value") else str(v) for v in (profile.claim_types or [])]),
            json.dumps({"contexts": (profile.applicability.contexts if profile.applicability else []),
                        "conditions": (profile.applicability.conditions if profile.applicability else []),
                        "contraindications": (profile.applicability.contraindications if profile.applicability else [])}),
            json.dumps([{"description": l.description, "severity": l.severity} for l in (profile.limitations or [])]),
            json.dumps({"included": (profile.scope_boundary.included_topics if profile.scope_boundary else []),
                        "excluded": (profile.scope_boundary.excluded_topics if profile.scope_boundary else [])}),
            json.dumps({"required": (profile.citation_policy.required if profile.citation_policy else True),
                        "format": (profile.citation_policy.format if profile.citation_policy else "inline")}),
            json.dumps({"score": (profile.source_reliability.score if profile.source_reliability else 0.5),
                        "basis": (profile.source_reliability.basis if profile.source_reliability else "mixed")}),
            now,
        )

        if existing:
            cursor.execute(
                "UPDATE epistemic_profiles SET tradition=?, framework=?, discipline=?, "
                "primary_topics=?, secondary_topics=?, evidence_level=?, reasoning_style=?, authority=?, "
                "claim_types=?, applicability=?, limitations=?, scope_boundary=?, citation_policy=?, "
                "source_reliability=?, updated_at=?, deleted_at=NULL WHERE book_id=? AND deleted_at IS NULL",
                (*vals, book_id),
            )
            pid = existing[0]
        else:
            cursor.execute(
                "INSERT INTO epistemic_profiles "
                "(id, book_id, user_id, source, tradition, framework, discipline, "
                "primary_topics, secondary_topics, supported_questions, unsupported_questions, "
                "evidence_level, reasoning_style, authority, claim_types, applicability, "
                "limitations, scope_boundary, citation_policy, confidence_policy, "
                "conflict_policy, priority_hints, source_reliability, historical_period, "
                "language, translation_metadata, created_at, updated_at, deleted_at) "
                "VALUES (?, ?, ?, 'book', ?, ?, ?, ?, ?, '', '', ?, ?, ?, ?, ?, "
                "?, ?, ?, 'standard', 'negotiate', '[]', ?, 'modern', 'en', '', ?, ?, NULL)",
                (pid, book_id, "00000000-0000-0000-0000-000000000001", *vals, now),
            )

        profile_result = {
            "profile_id": pid,
            "framework": to_str(profile.framework),
            "discipline": to_str(profile.discipline),
            "evidence_level": to_str(profile.evidence_level),
            "reasoning_style": to_str(profile.reasoning_style),
            "is_valid": validation.is_valid,
        }

    conn.commit()
    conn.close()

    return {
        "book_id": book_id,
        "chunks_created": len(chunks),
        "total_words": len(words),
        "profile": profile_result,
    }


# ---------------------------------------------------------------------------
# Epistemic Profile endpoints
# ---------------------------------------------------------------------------

class EpistemicProfileResponse(BaseModel):
    id: str
    book_id: str
    tradition: str
    framework: str
    discipline: str
    evidence_level: str
    reasoning_style: str
    authority: str
    primary_topics: list[str] = []
    secondary_topics: list[str] = []
    supported_questions: list[str] = []
    unsupported_questions: list[str] = []
    claim_types: list[str] = []
    limitations: list[dict] = []
    scope_boundary: dict = {}
    citation_policy: dict = {}
    source_reliability: dict = {}
    language: str = "en"


class RegenerateProfileResponse(BaseModel):
    profile_id: str
    book_id: str
    framework: str
    discipline: str
    evidence_level: str
    reasoning_style: str
    is_valid: bool
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    duration_ms: float


def _get_db_path() -> str:
    return "/home/hadi/ayeneh/Ayeneh/ayeneh.db"


@router.get("/books/{book_id}/profile")
async def get_book_profile(book_id: str) -> dict:
    import sqlite3, json
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, book_id, tradition, framework, discipline, evidence_level, "
        "reasoning_style, authority, primary_topics, secondary_topics, "
        "supported_questions, unsupported_questions, claim_types, "
        "limitations, scope_boundary, citation_policy, source_reliability, language "
        "FROM epistemic_profiles WHERE book_id = ? AND deleted_at IS NULL",
        (book_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "Profile not found", "book_id": book_id}

    def parse_json(val, default=None):
        if val is None:
            return default if default is not None else []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default if default is not None else []
        return val

    return {
        "id": row[0],
        "book_id": row[1],
        "tradition": row[2],
        "framework": row[3],
        "discipline": row[4],
        "evidence_level": row[5],
        "reasoning_style": row[6],
        "authority": row[7],
        "primary_topics": parse_json(row[8]),
        "secondary_topics": parse_json(row[9]),
        "supported_questions": parse_json(row[10]),
        "unsupported_questions": parse_json(row[11]),
        "claim_types": parse_json(row[12]),
        "limitations": parse_json(row[13]),
        "scope_boundary": parse_json(row[14]),
        "citation_policy": parse_json(row[15]),
        "source_reliability": parse_json(row[16]),
        "language": row[17] or "en",
    }


@router.post("/books/{book_id}/regenerate-profile", status_code=200)
async def regenerate_book_profile(book_id: str) -> dict:
    import sqlite3
    import json
    import time
    from datetime import UTC, datetime

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get book info
    cursor.execute("SELECT title, author FROM books WHERE id = ? AND deleted_at IS NULL", (book_id,))
    book_row = cursor.fetchone()
    if not book_row:
        conn.close()
        return {"error": "Book not found", "book_id": book_id}

    # Get chunks for this book as chapters
    cursor.execute(
        "SELECT content, token_count FROM book_chunks "
        "WHERE book_id = ? AND deleted_at IS NULL ORDER BY sequence_number",
        (book_id,),
    )
    book_chunks = cursor.fetchall()
    if not book_chunks:
        conn.close()
        return {"error": "No chunks found for book", "book_id": book_id}

    chapters = [{"content": ct[0][:2000], "token_count": ct[1]} for ct in book_chunks]

    from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
    from ayeneh.domain.knowledge_epistemics.generator.types import DocumentContext

    generator = RuleBasedProfileGenerator()
    doc_context = DocumentContext(
        document_id=book_id,
        title=book_row[0] or "Unknown",
        author=book_row[1] or "Unknown",
        language="en",
        chapters=chapters,
        total_chunks=len(chapters),
    )

    start = time.monotonic()
    profile, metadata = generator.generate(doc_context, book_id, "00000000-0000-0000-0000-000000000001")
    validation = generator.validate(profile)
    duration_ms = (time.monotonic() - start) * 1000

    def to_str(val) -> str:
        if val is None:
            return ""
        if hasattr(val, "value"):
            return val.value
        return str(val)

    now = datetime.now(UTC).isoformat()

    # Check if profile already exists
    cursor.execute(
        "SELECT id FROM epistemic_profiles WHERE book_id = ? AND deleted_at IS NULL",
        (book_id,),
    )
    existing = cursor.fetchone()

    profile_id = str(profile.id) if isinstance(profile.id, uuid.UUID) else str(profile.id)

    common_values = (
        to_str(profile.tradition),
        to_str(profile.framework),
        to_str(profile.discipline),
        json.dumps(profile.primary_topics or []),
        json.dumps(profile.secondary_topics or []),
        to_str(profile.evidence_level),
        to_str(profile.reasoning_style),
        to_str(profile.authority),
        json.dumps([v.value if hasattr(v, "value") else str(v) for v in (profile.claim_types or [])]),
        json.dumps({
            "contexts": (profile.applicability.contexts if profile.applicability else []),
            "conditions": (profile.applicability.conditions if profile.applicability else []),
            "contraindications": (profile.applicability.contraindications if profile.applicability else []),
        }),
        json.dumps([{"description": l.description, "severity": l.severity} for l in (profile.limitations or [])]),
        json.dumps({
            "included": (profile.scope_boundary.included_topics if profile.scope_boundary else []),
            "excluded": (profile.scope_boundary.excluded_topics if profile.scope_boundary else []),
        }),
        json.dumps({
            "required": (profile.citation_policy.required if profile.citation_policy else True),
            "format": (profile.citation_policy.format if profile.citation_policy else "inline"),
        }),
        json.dumps({
            "score": (profile.source_reliability.score if profile.source_reliability else 0.5),
            "basis": (profile.source_reliability.basis if profile.source_reliability else "mixed"),
        }),
        now,
    )

    if existing:
        cursor.execute(
            "UPDATE epistemic_profiles SET "
            "tradition=?, framework=?, discipline=?, primary_topics=?, secondary_topics=?, "
            "evidence_level=?, reasoning_style=?, authority=?, claim_types=?, applicability=?, "
            "limitations=?, scope_boundary=?, citation_policy=?, source_reliability=?, "
            "updated_at=?, deleted_at=NULL "
            "WHERE book_id=? AND deleted_at IS NULL",
            (*common_values, book_id),
        )
        profile_id = existing[0]
    else:
        cursor.execute(
            "INSERT INTO epistemic_profiles "
            "(id, book_id, user_id, source, tradition, framework, discipline, "
            "primary_topics, secondary_topics, supported_questions, unsupported_questions, "
            "evidence_level, reasoning_style, authority, claim_types, applicability, "
            "limitations, scope_boundary, citation_policy, confidence_policy, "
            "conflict_policy, priority_hints, source_reliability, historical_period, "
            "language, translation_metadata, created_at, updated_at, deleted_at) "
            "VALUES (?, ?, ?, 'book', ?, ?, ?, ?, ?, '', '', ?, ?, ?, ?, ?, "
            "?, ?, ?, 'standard', 'negotiate', '[]', ?, 'modern', 'en', '', ?, ?, NULL)",
            (profile_id, book_id, "00000000-0000-0000-0000-000000000001", *common_values, now),
        )

    conn.commit()
    conn.close()

    return {
        "profile_id": profile_id,
        "book_id": book_id,
        "framework": to_str(profile.framework),
        "discipline": to_str(profile.discipline),
        "evidence_level": to_str(profile.evidence_level),
        "reasoning_style": to_str(profile.reasoning_style),
        "is_valid": validation.is_valid,
        "validation_errors": validation.errors,
        "validation_warnings": validation.warnings,
        "duration_ms": round(duration_ms, 2),
    }
