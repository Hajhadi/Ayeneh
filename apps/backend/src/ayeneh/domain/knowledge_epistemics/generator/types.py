"""Generator types — domain objects for profile generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class GenerationStatus(StrEnum):
    """Status of profile generation."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GenerationMetadata:
    """Metadata about how the profile was generated."""

    generator_version: str = "1.0.0"
    engine_type: str = "rule_based"  # "rule_based" | "llm"
    generation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    analysis_duration_ms: float = 0.0
    chapters_analyzed: int = 0
    total_tokens_analyzed: int = 0
    confidence_factors: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    alternative_interpretations: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of profile validation."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    consistency_checks: dict[str, bool] = field(default_factory=dict)


@dataclass
class ProfileVersion:
    """Versioned profile with history tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str = ""
    version: int = 1
    book_id: str = ""
    user_id: str = ""
    profile_data: dict = field(default_factory=dict)
    validation_result: ValidationResult = field(default_factory=ValidationResult)
    generation_metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_current: bool = True


@dataclass
class GenerationResult:
    """Result of profile generation."""

    status: str = GenerationStatus.COMPLETED
    profile_id: str = ""
    version: int = 1
    validation: ValidationResult = field(default_factory=ValidationResult)
    metadata: GenerationMetadata = field(default_factory=GenerationMetadata)
    error: str | None = None


@dataclass
class DocumentContext:
    """Context about the document being analyzed."""

    document_id: str = ""
    title: str = ""
    author: str = ""
    language: str = "en"
    chapters: list[dict] = field(default_factory=list)
    total_pages: int = 0
    total_chunks: int = 0
    metadata: dict = field(default_factory=dict)
