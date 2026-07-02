"""Document Recovery Pipeline — handles failed imports with OCR support."""

from ayeneh.knowledge_import.recovery.service import RecoveryService
from ayeneh.knowledge_import.recovery.types import (
    ChunkProvenance,
    DiagnosticResult,
    FailureReason,
    OCRConfig,
    OCRPageResult,
    OCRVersionMetadata,
    PageDiagnosis,
    PageStatus,
    RecoveryResult,
    RecoveryStatus,
    ReviewMetadata,
    ReviewStatus,
    TextOrigin,
    TextSource,
)

__all__ = [
    "ChunkProvenance",
    "DiagnosticResult",
    "FailureReason",
    "OCRConfig",
    "OCRPageResult",
    "OCRVersionMetadata",
    "PageDiagnosis",
    "PageStatus",
    "RecoveryResult",
    "RecoveryService",
    "RecoveryStatus",
    "ReviewMetadata",
    "ReviewStatus",
    "TextOrigin",
    "TextSource",
]
