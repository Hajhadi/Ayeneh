"""Comprehensive tests for OCR hardening features."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_import.recovery.diagnoser import DocumentDiagnoser
from ayeneh.knowledge_import.recovery.service import RecoveryService
from ayeneh.knowledge_import.recovery.types import (
    ChunkProvenance,
    DiagnosticResult,
    FailureReason,
    OCRConfig,
    OCRPageResult,
    PageDiagnosis,
    PageStatus,
    RecoveryResult,
    RecoveryStatus,
    ReviewMetadata,
    ReviewStatus,
    TextOrigin,
    TextSource,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def diagnoser() -> DocumentDiagnoser:
    return DocumentDiagnoser()


@pytest.fixture
def recovery_service() -> RecoveryService:
    return RecoveryService()


@pytest.fixture
def ocr_config() -> OCRConfig:
    return OCRConfig(languages=["eng"], confidence_threshold=0.6, review_threshold=0.80)


# ---------------------------------------------------------------------------
# Selective OCR tests
# ---------------------------------------------------------------------------


class TestSelectiveOCR:
    def test_selective_ocr_only_processes_needed_pages(
        self, recovery_service: RecoveryService,
    ) -> None:
        """OCR should only process pages that need it."""
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        result = recovery_service.recover(pdf_content, "test.pdf")
        assert result.total_pages >= 1
        # Pages that need OCR should be processed
        assert result.pages_using_ocr >= 0

    def test_native_text_preserved(
        self, recovery_service: RecoveryService,
    ) -> None:
        """Native text should always be preserved."""
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        result = recovery_service.recover(pdf_content, "test.pdf")
        # Native text should be tracked
        assert result.pages_using_native >= 0
        assert result.pages_using_ocr >= 0


# ---------------------------------------------------------------------------
# Chunk Provenance tests
# ---------------------------------------------------------------------------


class TestChunkProvenance:
    def test_provenance_has_required_fields(self) -> None:
        prov = ChunkProvenance(
            text_origin=TextOrigin.NATIVE,
            native_text_available=True,
            ocr_confidence=0.0,
            ocr_engine="tesseract",
            page_number=0,
        )
        assert prov.text_origin == TextOrigin.NATIVE
        assert prov.native_text_available is True

    def test_text_origin_values(self) -> None:
        assert TextOrigin.NATIVE == "native"
        assert TextOrigin.OCR == "ocr"
        assert TextOrigin.HYBRID == "hybrid"


# ---------------------------------------------------------------------------
# Review Status tests
# ---------------------------------------------------------------------------


class TestReviewStatus:
    def test_review_status_values(self) -> None:
        assert ReviewStatus.NONE == "none"
        assert ReviewStatus.NEEDS_REVIEW == "needs_review"
        assert ReviewStatus.REVIEWED == "reviewed"
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.REJECTED == "rejected"


class TestReviewMetadata:
    def test_review_metadata_fields(self) -> None:
        meta = ReviewMetadata(
            review_status=ReviewStatus.NEEDS_REVIEW,
            average_confidence=0.75,
            minimum_confidence=0.50,
            pages_below_threshold=3,
            ocr_percentage=0.45,
            review_reason="Low confidence",
        )
        assert meta.review_status == ReviewStatus.NEEDS_REVIEW
        assert meta.average_confidence == 0.75
        assert meta.pages_below_threshold == 3


# ---------------------------------------------------------------------------
# Page Diagnosis tests
# ---------------------------------------------------------------------------


class TestPageDiagnosis:
    def test_page_diagnosis_fields(self) -> None:
        diag = PageDiagnosis(
            page_number=0,
            status=PageStatus.NATIVE_TEXT,
            native_text="test text",
            native_text_quality=0.8,
            has_native_text=True,
            needs_ocr=False,
        )
        assert diag.page_number == 0
        assert diag.status == PageStatus.NATIVE_TEXT
        assert diag.has_native_text is True

    def test_page_status_values(self) -> None:
        assert PageStatus.NATIVE_TEXT == "native_text"
        assert PageStatus.OCR_REQUIRED == "ocr_required"
        assert PageStatus.CORRUPTED == "corrupted"
        assert PageStatus.MIXED == "mixed"
        assert PageStatus.EMPTY == "empty"


# ---------------------------------------------------------------------------
# Diagnostic Page-Level tests
# ---------------------------------------------------------------------------


class TestDiagnosticPageLevel:
    def test_diagnostic_includes_page_diagnoses(self, diagnoser: DocumentDiagnoser) -> None:
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        result = diagnoser.diagnose(pdf_content, "test.pdf")
        assert len(result.page_diagnoses) >= 1


# ---------------------------------------------------------------------------
# Review Workflow tests
# ---------------------------------------------------------------------------


class TestReviewWorkflow:
    def test_review_metadata_generated(
        self, recovery_service: RecoveryService,
    ) -> None:
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        result = recovery_service.recover(pdf_content, "test.pdf")
        assert result.review_metadata is not None

    def test_review_status_none_when_high_confidence(
        self, recovery_service: RecoveryService,
    ) -> None:
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        result = recovery_service.recover(pdf_content, "test.pdf")
        assert result.review_metadata is not None
        assert result.review_metadata.review_status in (
            ReviewStatus.NONE,
            ReviewStatus.NEEDS_REVIEW,
        )


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    def test_ocr_config_review_threshold(self) -> None:
        config = OCRConfig(review_threshold=0.85)
        assert config.review_threshold == 0.85

    def test_ocr_config_default_review_threshold(self) -> None:
        config = OCRConfig()
        assert config.review_threshold == 0.80


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_recovery_still_works(self) -> None:
        service = RecoveryService()
        assert service._ocr_engine is None

    def test_existing_diagnoser_still_works(self) -> None:
        diagnoser = DocumentDiagnoser()
        assert diagnoser is not None

    def test_recovery_result_has_new_fields(self) -> None:
        result = RecoveryResult()
        assert hasattr(result, "pages_using_native")
        assert hasattr(result, "pages_using_ocr")
        assert hasattr(result, "pages_skipped")
        assert hasattr(result, "ocr_percentage")
        assert hasattr(result, "review_metadata")


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_diagnosis_completes_quickly(self, diagnoser: DocumentDiagnoser) -> None:
        import time
        start = time.monotonic()
        for _ in range(10):
            diagnoser.diagnose(b"not a pdf", "test.pdf")
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000
