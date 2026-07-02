"""Recovery Service — orchestrates document recovery with OCR support."""

from __future__ import annotations

import structlog

from ayeneh.knowledge_import.recovery.diagnoser import DocumentDiagnoser
from ayeneh.knowledge_import.recovery.ocr_engine import OCREngine
from ayeneh.knowledge_import.recovery.types import (
    DiagnosticResult,
    FailureReason,
    OCRConfig,
    RecoveryResult,
    RecoveryStatus,
    TextSource,
)

logger = structlog.get_logger(__name__)


class RecoveryService:
    """Orchestrates document recovery for failed imports.

    Pipeline:
    1. Diagnose why chunk extraction failed
    2. Check if native text layer exists
    3. If no text layer, run OCR
    4. If OCR confidence is low, mark as LowConfidence
    5. Return recovered text for retry
    """

    def __init__(self, ocr_config: OCRConfig | None = None) -> None:
        self._diagnoser = DocumentDiagnoser()
        self._ocr_config = ocr_config or OCRConfig()
        self._ocr_engine: OCREngine | None = None
        self._metrics = RecoveryMetrics()

    def _get_ocr_engine(self) -> OCREngine:
        """Lazy-init OCR engine."""
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine(self._ocr_config)
        return self._ocr_engine

    def recover(
        self,
        content: bytes,
        filename: str,
    ) -> RecoveryResult:
        """Attempt to recover a failed document import."""
        result = RecoveryResult()

        # Step 1: Diagnose
        result.status = RecoveryStatus.DIAGNOSING
        diagnostic = self._diagnoser.diagnose(content, filename)
        result.diagnostic = diagnostic
        result.original_failure_reason = diagnostic.failure_reason
        result.total_pages = diagnostic.page_count

        logger.info(
            "recovery_diagnosed",
            filename=filename,
            failure_reason=diagnostic.failure_reason,
            has_text_layer=diagnostic.has_text_layer,
            text_layer_quality=round(diagnostic.text_layer_quality, 2),
        )

        # Step 2: Check if native text can be improved
        if diagnostic.has_text_layer and diagnostic.text_layer_quality > 0.3:
            # Has decent text layer - try to re-parse with better settings
            result.text_source = TextSource.NATIVE
            result.status = RecoveryStatus.RETRYING
            result.recovered_text = f"[Native text available: {diagnostic.pages_with_text} pages]"
            result.recovered_pages = diagnostic.pages_with_text
            result.average_confidence = diagnostic.text_layer_quality
            result.retry_needed = True
            self._metrics.record_recovery(RecoveryStatus.RETRYING)
            return result

        # Step 3: Selective OCR - only process pages that need it
        result.status = RecoveryStatus.OCR_RUNNING
        ocr_engine = self._get_ocr_engine()

        # Get page diagnoses from diagnostic
        page_diagnoses = diagnostic.page_diagnoses

        # Selective OCR: only OCR pages that need it
        ocr_results = self._selective_ocr(content, filename, page_diagnoses)
        result.ocr_pages = ocr_results

        # Step 4: Evaluate OCR quality
        result.average_confidence = self._calculate_average_confidence(ocr_results)
        result.recovered_pages = sum(1 for r in ocr_results if r.text.strip())
        result.low_confidence_pages = sum(
            1 for r in ocr_results
            if r.text.strip() and r.confidence < self._ocr_config.confidence_threshold
        )

        # Step 5: Count page sources
        result.pages_using_native = sum(1 for r in ocr_results if r.is_native)
        result.pages_using_ocr = sum(1 for r in ocr_results if not r.is_native and r.text.strip())
        result.pages_skipped = sum(1 for r in ocr_results if not r.text.strip() and not r.is_native)

        # Calculate OCR percentage
        if result.total_pages > 0:
            result.ocr_percentage = result.pages_using_ocr / result.total_pages

        # Step 6: Determine text source
        if result.pages_using_native > 0 and result.pages_using_ocr > 0:
            result.text_source = TextSource.MIXED
        elif result.pages_using_native > 0:
            result.text_source = TextSource.NATIVE
        else:
            result.text_source = TextSource.OCR

        # Step 7: Build recovered text (preserve page order)
        result.recovered_text = "\n\n".join(
            r.text for r in ocr_results if r.text.strip()
        )

        # Step 8: Review workflow
        result.review_metadata = self._compute_review_metadata(result)

        # Step 9: Check confidence threshold
        if result.average_confidence < self._ocr_config.confidence_threshold:
            result.status = RecoveryStatus.LOW_CONFIDENCE
            logger.warning(
                "ocr_low_confidence",
                filename=filename,
                average_confidence=round(result.average_confidence, 2),
                threshold=self._ocr_config.confidence_threshold,
                low_confidence_pages=result.low_confidence_pages,
            )
        elif result.review_metadata.review_status == ReviewStatus.NEEDS_REVIEW:
            result.status = RecoveryStatus.COMPLETED
            result.retry_needed = True
            logger.info(
                "document_needs_review",
                filename=filename,
                average_confidence=round(result.average_confidence, 2),
                review_threshold=self._ocr_config.review_threshold,
            )
        else:
            result.status = RecoveryStatus.COMPLETED
            result.retry_needed = True

        # Record metrics
        self._metrics.record_recovery(result.status)

        logger.info(
            "recovery_complete",
            filename=filename,
            status=result.status,
            recovered_pages=result.recovered_pages,
            average_confidence=round(result.average_confidence, 2),
            text_source=result.text_source,
            pages_native=result.pages_using_native,
            pages_ocr=result.pages_using_ocr,
        )

        return result

    def _selective_ocr(
        self,
        content: bytes,
        filename: str,
        page_diagnoses: list,
    ) -> list:
        """Run OCR only on pages that need it."""
        try:
            import fitz
        except ImportError:
            return []

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception:
            return []

        from ayeneh.knowledge_import.recovery.types import OCRPageResult, PageStatus

        results = []
        ocr_engine = self._get_ocr_engine()

        for page_diag in page_diagnoses:
            page_num = page_diag.page_number

            if page_diag.status == PageStatus.NATIVE_TEXT and not page_diag.needs_ocr:
                # Use native text - no OCR needed
                results.append(OCRPageResult(
                    page_number=page_num,
                    text=page_diag.native_text,
                    confidence=1.0,
                    language_detected="native",
                    is_native=True,
                    native_text=page_diag.native_text,
                ))
            elif page_diag.status == PageStatus.CORRUPTED or page_diag.status == PageStatus.EMPTY:
                # Skip corrupted or empty pages
                results.append(OCRPageResult(
                    page_number=page_num,
                    text="",
                    confidence=0.0,
                    language_detected="",
                    is_native=False,
                ))
            else:
                # OCR required - run selective OCR on this page only
                try:
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=ocr_engine._config.dpi)
                    img_data = pix.tobytes("png")

                    text, confidence, language = ocr_engine._run_tesseract(img_data)

                    results.append(OCRPageResult(
                        page_number=page_num,
                        text=text,
                        confidence=confidence,
                        language_detected=language,
                        is_native=False,
                        native_text=page_diag.native_text,
                    ))
                except Exception as e:
                    logger.warning("selective_ocr_failed", page=page_num, error=str(e))
                    results.append(OCRPageResult(
                        page_number=page_num,
                        text="",
                        confidence=0.0,
                        language_detected="",
                        is_native=False,
                    ))

        doc.close()
        return results

    def _calculate_average_confidence(self, ocr_results: list) -> float:
        """Calculate average OCR confidence."""
        if not ocr_results:
            return 0.0

        confidences = [r.confidence for r in ocr_results if r.confidence > 0]
        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)

    def _compute_review_metadata(self, result) -> 'ReviewMetadata':
        """Compute review metadata for human review workflow."""
        from ayeneh.knowledge_import.recovery.types import ReviewMetadata, ReviewStatus

        # Calculate OCR statistics
        ocr_confidences = [
            r.confidence for r in result.ocr_pages
            if not r.is_native and r.confidence > 0
        ]

        average_confidence = result.average_confidence
        minimum_confidence = min(ocr_confidences) if ocr_confidences else 1.0
        pages_below_threshold = sum(
            1 for c in ocr_confidences
            if c < self._ocr_config.confidence_threshold
        )
        ocr_percentage = result.ocr_percentage

        # Determine if review is needed
        review_status = ReviewStatus.NONE
        review_reason = ""

        if average_confidence < self._ocr_config.review_threshold:
            review_status = ReviewStatus.NEEDS_REVIEW
            review_reason = f"Average OCR confidence {average_confidence:.2f} below threshold {self._ocr_config.review_threshold}"
        elif pages_below_threshold > 0:
            review_status = ReviewStatus.NEEDS_REVIEW
            review_reason = f"{pages_below_threshold} pages below confidence threshold"

        return ReviewMetadata(
            review_status=review_status,
            average_confidence=average_confidence,
            minimum_confidence=minimum_confidence,
            pages_below_threshold=pages_below_threshold,
            ocr_percentage=ocr_percentage,
            review_reason=review_reason,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get recovery metrics."""
        return self._metrics.get_metrics()


class RecoveryMetrics:
    """Metrics for recovery operations."""

    def __init__(self) -> None:
        self._recovery_count: dict[str, int] = {}
        self._total_recoveries: int = 0
        self._successful_recoveries: int = 0

    def record_recovery(self, status: str) -> None:
        """Record a recovery attempt."""
        self._recovery_count[status] = self._recovery_count.get(status, 0) + 1
        self._total_recoveries += 1
        if status in (RecoveryStatus.COMPLETED, RecoveryStatus.RETRYING):
            self._successful_recoveries += 1

    def get_metrics(self) -> dict[str, int]:
        """Get metrics."""
        return {
            "total_recoveries": self._total_recoveries,
            "successful_recoveries": self._successful_recoveries,
            "recovery_by_status": dict(self._recovery_count),
        }
