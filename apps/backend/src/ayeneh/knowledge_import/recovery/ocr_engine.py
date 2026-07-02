"""OCR Engine — extracts text from scanned documents using Tesseract."""

from __future__ import annotations

import structlog

from ayeneh.knowledge_import.recovery.types import OCRConfig, OCRPageResult

logger = structlog.get_logger(__name__)


class OCREngine:
    """OCR engine using Tesseract for text extraction from scanned documents.

    Supports multiple languages including Persian, Arabic, English, and Spanish.
    """

    def __init__(self, config: OCRConfig | None = None) -> None:
        self._config = config or OCRConfig()

    def extract_text(self, content: bytes, filename: str) -> list[OCRPageResult]:
        """Extract text from a PDF using OCR."""
        try:
            import fitz
        except ImportError:
            logger.error("ocr_dependencies_missing", library="PyMuPDF")
            return []

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            logger.error("ocr_pdf_open_failed", error=str(e))
            return []

        results: list[OCRPageResult] = []
        page_count = len(doc)

        for page_num in range(page_count):
            try:
                page = doc.load_page(page_num)

                # First check if native text exists
                native_text = page.get_text("text").strip()
                if native_text and len(native_text) > 10:
                    results.append(OCRPageResult(
                        page_number=page_num,
                        text=native_text,
                        confidence=1.0,
                        language_detected="native",
                        is_native=True,
                    ))
                    continue

                # Convert page to image for OCR
                pix = page.get_pixmap(dpi=self._config.dpi)
                img_data = pix.tobytes("png")

                # Run OCR
                text, confidence, language = self._run_tesseract(img_data)

                results.append(OCRPageResult(
                    page_number=page_num,
                    text=text,
                    confidence=confidence,
                    language_detected=language,
                    is_native=False,
                ))

            except Exception as e:
                logger.warning("ocr_page_failed", page=page_num, error=str(e))
                results.append(OCRPageResult(
                    page_number=page_num,
                    text="",
                    confidence=0.0,
                    language_detected="",
                    is_native=False,
                ))

        doc.close()

        logger.info(
            "ocr_extraction_complete",
            filename=filename,
            total_pages=page_count,
            pages_with_text=sum(1 for r in results if r.text.strip()),
            average_confidence=self._calculate_average_confidence(results),
        )

        return results

    def _run_tesseract(self, img_data: bytes) -> tuple[str, float, str]:
        """Run Tesseract OCR on image data."""
        try:
            import pytesseract
            from PIL import Image
            import io

            # Convert image bytes to PIL Image
            image = Image.open(io.BytesIO(img_data))

            # Get text with confidence data
            data = pytesseract.image_to_data(
                image,
                lang="+".join(self._config.languages),
                output_type=pytesseract.Output.DICT,
            )

            # Extract text and calculate confidence
            words = []
            confidences = []
            for i, word in enumerate(data["text"]):
                if word.strip():
                    words.append(word)
                    conf = data["conf"][i]
                    if conf > 0:  # Tesseract uses -1 for non-text
                        confidences.append(conf / 100.0)

            text = " ".join(words)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Detect language (simplified)
            language = self._detect_language(text)

            return text, avg_confidence, language

        except ImportError:
            logger.warning("ocr_dependencies_missing", library="pytesseract/Pillow")
            return "", 0.0, ""
        except Exception as e:
            logger.warning("tesseract_failed", error=str(e))
            return "", 0.0, ""

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns."""
        if not text:
            return "unknown"

        # Check for Arabic/Persian characters (Unicode range)
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
        total_chars = len(text.strip())

        if total_chars > 0 and arabic_chars / total_chars > 0.3:
            return "fas"  # Default to Persian, could be Arabic

        # Check for common English words
        english_indicators = ["the", "is", "are", "was", "were", "have", "has"]
        if any(word in text.lower().split() for word in english_indicators):
            return "eng"

        return "eng"  # Default

    def _calculate_average_confidence(self, results: list[OCRPageResult]) -> float:
        """Calculate average OCR confidence across all pages."""
        if not results:
            return 0.0

        confidences = [r.confidence for r in results if r.confidence > 0]
        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)
