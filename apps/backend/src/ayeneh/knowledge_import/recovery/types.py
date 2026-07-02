"""Recovery types — core domain objects for document recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FailureReason(StrEnum):
    """Reasons why chunk extraction failed."""

    SCANNED_PDF = "scanned_pdf"
    IMAGE_ONLY_PAGES = "image_only_pages"
    CORRUPTED_PDF = "corrupted_pdf"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    EMPTY_TEXT_LAYER = "empty_text_layer"
    OCR_REQUIRED = "ocr_required"
    PARSING_FAILURE = "parsing_failure"
    UNKNOWN = "unknown"


class RecoveryStatus(StrEnum):
    """Status of recovery attempt."""

    PENDING = "pending"
    DIAGNOSING = "diagnosing"
    OCR_RUNNING = "ocr_running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"


class TextSource(StrEnum):
    """Source of extracted text."""

    NATIVE = "native"
    OCR = "ocr"
    MIXED = "mixed"


class TextOrigin(StrEnum):
    """Origin of text in a chunk for provenance tracking."""

    NATIVE = "native"
    OCR = "ocr"
    HYBRID = "hybrid"


class PageStatus(StrEnum):
    """Status of a page after diagnosis."""

    NATIVE_TEXT = "native_text"
    OCR_REQUIRED = "ocr_required"
    CORRUPTED = "corrupted"
    MIXED = "mixed"
    EMPTY = "empty"


class ReviewStatus(StrEnum):
    """Human review status for documents."""

    NONE = "none"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class OCRConfig:
    """Configuration for OCR engine."""

    languages: list[str] = field(default_factory=lambda: ["eng", "fas", "ara"])
    confidence_threshold: float = 0.6
    review_threshold: float = 0.80
    dpi: int = 300
    use_tesseract: bool = True
    tesseract_path: str = "tesseract"
    max_retries: int = 2


# ---------------------------------------------------------------------------
# Page Diagnosis
# ---------------------------------------------------------------------------


@dataclass
class PageDiagnosis:
    """Diagnosis result for a single page."""

    page_number: int = 0
    status: str = PageStatus.EMPTY
    native_text: str = ""
    native_text_quality: float = 0.0
    has_native_text: bool = False
    needs_ocr: bool = False
    is_corrupted: bool = False


# ---------------------------------------------------------------------------
# Chunk Provenance
# ---------------------------------------------------------------------------


@dataclass
class ChunkProvenance:
    """Provenance metadata for a chunk.

    Every chunk permanently retains its provenance.
    No consumer should need to inspect RecoveryResult.
    """

    text_origin: str = TextOrigin.NATIVE
    native_text_available: bool = True
    ocr_confidence: float = 0.0
    ocr_engine: str = ""
    ocr_model: str = ""
    ocr_version: str = ""
    ocr_timestamp: str = ""
    page_number: int = 0


# ---------------------------------------------------------------------------
# OCR Version Metadata
# ---------------------------------------------------------------------------


@dataclass
class OCRVersionMetadata:
    """Version metadata for OCR reproducibility.

    If OCR engine or preprocessing changes,
    the system knows which pages require regeneration.
    """

    engine_name: str = "tesseract"
    engine_version: str = ""
    language_models: list[str] = field(default_factory=list)
    configuration_hash: str = ""
    dpi: int = 300
    preprocessing_pipeline: str = "default"
    execution_date: str = ""


# ---------------------------------------------------------------------------
# Review Metadata
# ---------------------------------------------------------------------------


@dataclass
class ReviewMetadata:
    """Metadata for human review workflow."""

    review_status: str = ReviewStatus.NONE
    average_confidence: float = 0.0
    minimum_confidence: float = 1.0
    pages_below_threshold: int = 0
    ocr_percentage: float = 0.0
    review_reason: str = ""
    reviewer_notes: str = ""


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticResult:
    """Result of diagnosing a failed import."""

    failure_reason: str = FailureReason.UNKNOWN
    has_text_layer: bool = False
    text_layer_quality: float = 0.0
    page_count: int = 0
    pages_with_text: int = 0
    pages_without_text: int = 0
    is_scanned: bool = False
    is_corrupted: bool = False
    encoding_detected: str = "utf-8"
    recommendations: list[str] = field(default_factory=list)
    page_diagnoses: list[PageDiagnosis] = field(default_factory=list)


@dataclass
class OCRPageResult:
    """Result of OCR on a single page."""

    page_number: int = 0
    text: str = ""
    confidence: float = 0.0
    language_detected: str = ""
    is_native: bool = False
    native_text: str = ""


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    status: str = RecoveryStatus.PENDING
    original_failure_reason: str = FailureReason.UNKNOWN
    diagnostic: DiagnosticResult | None = None
    ocr_pages: list[OCRPageResult] = field(default_factory=list)
    recovered_text: str = ""
    text_source: str = TextSource.NATIVE
    average_confidence: float = 0.0
    low_confidence_pages: int = 0
    total_pages: int = 0
    recovered_pages: int = 0
    retry_needed: bool = False
    error: str | None = None

    # OCR hardening fields
    pages_using_native: int = 0
    pages_using_ocr: int = 0
    pages_skipped: int = 0
    ocr_percentage: float = 0.0
    review_metadata: ReviewMetadata | None = None
