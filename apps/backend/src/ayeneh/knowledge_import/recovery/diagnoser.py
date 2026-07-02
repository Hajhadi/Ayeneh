"""Document Diagnoser — detects why chunk extraction failed."""

from __future__ import annotations

import structlog

from ayeneh.knowledge_import.recovery.types import (
    DiagnosticResult,
    FailureReason,
    PageDiagnosis,
    PageStatus,
)

logger = structlog.get_logger(__name__)


class DocumentDiagnoser:
    """Diagnoses why a document failed to produce chunks.

    Analyzes the PDF to determine the root cause before attempting recovery.
    Performs page-level diagnosis for selective OCR.
    """

    def diagnose(self, content: bytes, filename: str) -> DiagnosticResult:
        """Diagnose a failed document import with page-level analysis."""
        try:
            import fitz
        except ImportError:
            return DiagnosticResult(
                failure_reason=FailureReason.PARSING_FAILURE,
                recommendations=["Install PyMuPDF: pip install PyMuPDF"],
            )

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            return DiagnosticResult(
                failure_reason=FailureReason.CORRUPTED_PDF,
                is_corrupted=True,
                recommendations=[f"PDF appears corrupted: {str(e)[:100]}"],
            )

        page_count = len(doc)
        pages_with_text = 0
        pages_without_text = 0
        text_samples: list[str] = []
        page_diagnoses: list[PageDiagnosis] = []

        for page_num in range(page_count):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text").strip()

                # Page-level diagnosis
                page_diag = self._diagnose_page(page_num, text)
                page_diagnoses.append(page_diag)

                if text:
                    pages_with_text += 1
                    text_samples.append(text[:200])
                else:
                    pages_without_text += 1
            except Exception:
                pages_without_text += 1
                page_diagnoses.append(PageDiagnosis(
                    page_number=page_num,
                    status=PageStatus.CORRUPTED,
                    is_corrupted=True,
                ))

        doc.close()

        # Calculate text layer quality
        if page_count > 0:
            text_layer_quality = pages_with_text / page_count
        else:
            text_layer_quality = 0.0

        # Determine failure reason
        failure_reason = FailureReason.UNKNOWN
        recommendations: list[str] = []

        if pages_without_text == page_count:
            failure_reason = FailureReason.SCANNED_PDF
            recommendations.append("Document appears to be scanned or image-only")
            recommendations.append("OCR will be required to extract text")
        elif pages_without_text > 0 and pages_with_text > 0:
            failure_reason = FailureReason.EMPTY_TEXT_LAYER
            recommendations.append(f"{pages_without_text} of {page_count} pages have no text layer")
            recommendations.append("OCR may be needed for pages without text")
        elif pages_with_text > 0 and text_layer_quality < 0.1:
            failure_reason = FailureReason.EMPTY_TEXT_LAYER
            recommendations.append("Text layer exists but quality is very low")
            recommendations.append("Consider improving parser or using OCR")
        elif page_count == 0:
            failure_reason = FailureReason.CORRUPTED_PDF
            recommendations.append("Document has no pages")
        else:
            failure_reason = FailureReason.PARSING_FAILURE
            recommendations.append("Text exists but chunking failed")
            recommendations.append("Check parser configuration")

        # Check for encoding issues
        encoding_detected = "utf-8"
        if text_samples:
            try:
                text_samples[0].encode("utf-8")
            except UnicodeEncodeError:
                encoding_detected = "unknown"
                failure_reason = FailureReason.UNSUPPORTED_ENCODING
                recommendations.append("Document contains non-UTF-8 characters")

        result = DiagnosticResult(
            failure_reason=failure_reason,
            has_text_layer=pages_with_text > 0,
            text_layer_quality=text_layer_quality,
            page_count=page_count,
            pages_with_text=pages_with_text,
            pages_without_text=pages_without_text,
            is_scanned=pages_without_text == page_count,
            is_corrupted=page_count == 0,
            encoding_detected=encoding_detected,
            recommendations=recommendations,
            page_diagnoses=page_diagnoses,
        )

        logger.info(
            "document_diagnosed",
            filename=filename,
            failure_reason=failure_reason,
            page_count=page_count,
            pages_with_text=pages_with_text,
            text_layer_quality=round(text_layer_quality, 2),
        )

        return result

    def _diagnose_page(self, page_number: int, text: str) -> PageDiagnosis:
        """Diagnose a single page."""
        if not text:
            return PageDiagnosis(
                page_number=page_number,
                status=PageStatus.OCR_REQUIRED,
                has_native_text=False,
                needs_ocr=True,
            )

        # Check text quality
        text_length = len(text)
        if text_length < 10:
            return PageDiagnosis(
                page_number=page_number,
                status=PageStatus.MIXED,
                native_text=text,
                native_text_quality=0.2,
                has_native_text=True,
                needs_ocr=True,
            )

        if text_length < 50:
            return PageDiagnosis(
                page_number=page_number,
                status=PageStatus.MIXED,
                native_text=text,
                native_text_quality=0.5,
                has_native_text=True,
                needs_ocr=True,
            )

        return PageDiagnosis(
            page_number=page_number,
            status=PageStatus.NATIVE_TEXT,
            native_text=text,
            native_text_quality=min(1.0, text_length / 200),
            has_native_text=True,
            needs_ocr=False,
        )
