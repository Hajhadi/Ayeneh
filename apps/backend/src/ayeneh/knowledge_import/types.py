"""Knowledge Import types — core domain objects for document import pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ImportStatus(StrEnum):
    """Status of an import job."""

    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChunkingStrategy(StrEnum):
    """Available chunking strategies."""

    FIXED_LENGTH = "fixed_length"
    SEMANTIC = "semantic"
    CHAPTER_AWARE = "chapter_aware"
    PARAGRAPH_AWARE = "paragraph_aware"


@dataclass
class ImportMetadata:
    """Optional metadata for an import job."""

    title: str = ""
    author: str = ""
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    category: str = ""
    framework: str = ""
    domain: str = ""
    source: str = ""


@dataclass
class ImportJob:
    """Represents an import job with full lifecycle tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    filename: str = ""
    file_size: int = 0
    content_type: str = ""

    # Metadata
    metadata: ImportMetadata = field(default_factory=ImportMetadata)

    # Status
    status: str = ImportStatus.QUEUED
    progress_percent: float = 0.0
    current_step: str = ""
    error: str | None = None

    # Results
    document_id: str | None = None
    total_pages: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_remaining_ms: float | None = None

    # Retry
    attempt: int = 0
    max_attempts: int = 3
    last_checkpoint: str | None = None


@dataclass
class ImportProgress:
    """Progress update during import pipeline."""

    job_id: str
    status: str
    progress_percent: float = 0.0
    current_step: str = ""
    pages_parsed: int = 0
    chunks_generated: int = 0
    embeddings_generated: int = 0
    total_pages: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    error: str | None = None
    estimated_remaining_ms: float | None = None


@dataclass
class ImportResult:
    """Result of a completed import pipeline."""

    job_id: str
    document_id: str
    status: str
    total_pages: int = 0
    total_chapters: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class DocumentInfo:
    """Information about an imported document."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    author: str = ""
    source_format: str = ""
    status: str = "processing"
    chunk_count: int = 0
    page_count: int = 0
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    category: str = ""
    framework: str = ""
    domain: str = ""
    source: str = ""
    imported_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    indexed_at: datetime | None = None


@dataclass
class ChunkInfo:
    """Information about a document chunk."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    chapter_id: str = ""
    content: str = ""
    sequence_number: int = 0
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0
    section_heading: str | None = None
    char_offset_start: int = 0
    char_offset_end: int = 0
    embedding_id: str | None = None


@dataclass
class ChapterInfo:
    """Information about a document chapter."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    title: str = ""
    sequence_number: int = 0
    page_start: int | None = None
    page_end: int | None = None
    chunk_count: int = 0


@dataclass
class ImportMetrics:
    """Metrics about import operations."""

    documents_imported: int = 0
    pages_parsed: int = 0
    chunks_generated: int = 0
    embeddings_generated: int = 0
    average_chunk_size: float = 0.0
    import_latency_ms: float = 0.0
    failed_imports: int = 0
    retry_count: int = 0
    resume_count: int = 0
