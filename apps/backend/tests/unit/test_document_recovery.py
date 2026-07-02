"""Comprehensive tests for the Document Recovery Pipeline."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_import.recovery.diagnoser import DocumentDiagnoser
from ayeneh.knowledge_import.recovery.service import RecoveryMetrics, RecoveryService
from ayeneh.knowledge_import.recovery.types import (
    DiagnosticResult,
    FailureReason,
    OCRConfig,
    OCRPageResult,
    RecoveryResult,
    RecoveryStatus,
    TextSource,
)
from ayeneh.ingestion.parsers.base import Chapter, ParsedDocument


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
    return OCRConfig(languages=["eng"], confidence_threshold=0.6)


# ---------------------------------------------------------------------------
# Diagnostic tests
# ---------------------------------------------------------------------------


class TestDiagnostic:
    def test_diagnose_empty_pdf(self, diagnoser: DocumentDiagnoser) -> None:
        # Create a minimal valid PDF
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
        result = diagnoser.diagnose(pdf_content, "empty.pdf")
        assert result.failure_reason in (
            FailureReason.SCANNED_PDF,
            FailureReason.EMPTY_TEXT_LAYER,
            FailureReason.PARSING_FAILURE,
        )
        assert result.page_count >= 1

    def test_diagnose_returns_recommendations(self, diagnoser: DocumentDiagnoser) -> None:
        result = diagnoser.diagnose(b"not a pdf", "test.pdf")
        assert len(result.recommendations) > 0

    def test_diagnostic_result_has_required_fields(self) -> None:
        result = DiagnosticResult()
        assert hasattr(result, "failure_reason")
        assert hasattr(result, "has_text_layer")
        assert hasattr(result, "text_layer_quality")
        assert hasattr(result, "page_count")
        assert hasattr(result, "recommendations")


# ---------------------------------------------------------------------------
# OCR Engine tests
# ---------------------------------------------------------------------------


class TestOCRConfig:
    def test_default_config(self) -> None:
        config = OCRConfig()
        assert "eng" in config.languages
        assert config.confidence_threshold == 0.6
        assert config.dpi == 300

    def test_custom_config(self) -> None:
        config = OCRConfig(
            languages=["eng", "fas", "ara"],
            confidence_threshold=0.7,
            dpi=150,
        )
        assert config.languages == ["eng", "fas", "ara"]
        assert config.confidence_threshold == 0.7


class TestOCRPageResult:
    def test_page_result_fields(self) -> None:
        result = OCRPageResult(
            page_number=0,
            text="test text",
            confidence=0.85,
            language_detected="eng",
            is_native=False,
        )
        assert result.page_number == 0
        assert result.text == "test text"
        assert result.confidence == 0.85


# ---------------------------------------------------------------------------
# Recovery Service tests
# ---------------------------------------------------------------------------


class TestRecoveryService:
    def test_recover_empty_pdf(self, recovery_service: RecoveryService) -> None:
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
        assert isinstance(result, RecoveryResult)
        assert result.total_pages >= 1
        assert result.diagnostic is not None

    def test_recovery_metrics(self, recovery_service: RecoveryService) -> None:
        metrics = recovery_service.get_metrics()
        assert "total_recoveries" in metrics
        assert "successful_recoveries" in metrics


class TestRecoveryMetrics:
    def test_record_recovery(self) -> None:
        metrics = RecoveryMetrics()
        metrics.record_recovery(RecoveryStatus.COMPLETED)
        assert metrics._total_recoveries == 1
        assert metrics._successful_recoveries == 1

    def test_record_failed_recovery(self) -> None:
        metrics = RecoveryMetrics()
        metrics.record_recovery(RecoveryStatus.FAILED)
        assert metrics._total_recoveries == 1
        assert metrics._successful_recoveries == 0

    def test_get_metrics(self) -> None:
        metrics = RecoveryMetrics()
        metrics.record_recovery(RecoveryStatus.COMPLETED)
        metrics.record_recovery(RecoveryStatus.LOW_CONFIDENCE)
        m = metrics.get_metrics()
        assert m["total_recoveries"] == 2


# ---------------------------------------------------------------------------
# Text Source tests
# ---------------------------------------------------------------------------


class TestTextSource:
    def test_text_source_values(self) -> None:
        assert TextSource.NATIVE == "native"
        assert TextSource.OCR == "ocr"
        assert TextSource.MIXED == "mixed"


# ---------------------------------------------------------------------------
# Failure Reason tests
# ---------------------------------------------------------------------------


class TestFailureReason:
    def test_all_reasons_exist(self) -> None:
        assert FailureReason.SCANNED_PDF == "scanned_pdf"
        assert FailureReason.IMAGE_ONLY_PAGES == "image_only_pages"
        assert FailureReason.CORRUPTED_PDF == "corrupted_pdf"
        assert FailureReason.UNSUPPORTED_ENCODING == "unsupported_encoding"
        assert FailureReason.EMPTY_TEXT_LAYER == "empty_text_layer"
        assert FailureReason.OCR_REQUIRED == "ocr_required"
        assert FailureReason.PARSING_FAILURE == "parsing_failure"


# ---------------------------------------------------------------------------
# Chapter text source tests
# ---------------------------------------------------------------------------


class TestChapterTextSource:
    def test_chapter_has_text_source(self) -> None:
        chapter = Chapter(
            title="Test",
            sequence_number=0,
            content="content",
            text_source="native",
        )
        assert chapter.text_source == "native"

    def test_chapter_default_text_source(self) -> None:
        chapter = Chapter(title="Test", sequence_number=0, content="content")
        assert chapter.text_source == "native"


# ---------------------------------------------------------------------------
# ParsedDocument text source tests
# ---------------------------------------------------------------------------


class TestParsedDocumentTextSource:
    def test_document_has_text_source(self) -> None:
        doc = ParsedDocument(title="Test", text_source="ocr")
        assert doc.text_source == "ocr"

    def test_document_default_text_source(self) -> None:
        doc = ParsedDocument(title="Test")
        assert doc.text_source == "native"


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_parser_still_works(self) -> None:
        from ayeneh.ingestion.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        assert "pdf" in parser.supported_formats

    def test_recovery_service_without_ocr(self) -> None:
        service = RecoveryService()
        assert service._ocr_engine is None  # Lazy init


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
        assert elapsed < 1000  # 10 diagnoses in under 1 second
