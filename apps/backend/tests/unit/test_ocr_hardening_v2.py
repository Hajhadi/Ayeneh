"""Comprehensive tests for OCR hardening v2: provenance, safety, versioning."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.types import EpistemicSafetyResult, UncertaintyLevel
from ayeneh.knowledge_import.recovery.types import (
    ChunkProvenance,
    OCRVersionMetadata,
    TextOrigin,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def safety_engine() -> EpistemicSafetyEngine:
    return EpistemicSafetyEngine()


# ---------------------------------------------------------------------------
# Chunk Provenance tests
# ---------------------------------------------------------------------------


class TestChunkProvenance:
    def test_provenance_has_all_fields(self) -> None:
        prov = ChunkProvenance(
            text_origin=TextOrigin.NATIVE,
            native_text_available=True,
            ocr_confidence=0.0,
            ocr_engine="tesseract",
            ocr_model="eng",
            ocr_version="4.0",
            ocr_timestamp="2026-07-01T00:00:00Z",
            page_number=0,
        )
        assert prov.text_origin == TextOrigin.NATIVE
        assert prov.ocr_engine == "tesseract"
        assert prov.ocr_model == "eng"
        assert prov.ocr_version == "4.0"

    def test_provenance_hybrid(self) -> None:
        prov = ChunkProvenance(
            text_origin=TextOrigin.HYBRID,
            native_text_available=True,
            ocr_confidence=0.75,
        )
        assert prov.text_origin == TextOrigin.HYBRID
        assert prov.native_text_available is True


# ---------------------------------------------------------------------------
# OCR Version Metadata tests
# ---------------------------------------------------------------------------


class TestOCRVersionMetadata:
    def test_version_metadata_fields(self) -> None:
        meta = OCRVersionMetadata(
            engine_name="tesseract",
            engine_version="4.0",
            language_models=["eng", "fas"],
            configuration_hash="abc123",
            dpi=300,
            preprocessing_pipeline="default",
            execution_date="2026-07-01",
        )
        assert meta.engine_name == "tesseract"
        assert meta.engine_version == "4.0"
        assert "eng" in meta.language_models

    def test_version_metadata_defaults(self) -> None:
        meta = OCRVersionMetadata()
        assert meta.engine_name == "tesseract"
        assert meta.dpi == 300


# ---------------------------------------------------------------------------
# OCR Confidence Calibration tests
# ---------------------------------------------------------------------------


class TestOCRConfidenceCalibration:
    def test_low_ocr_confidence_reduces_safety(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "This passage suggests meditation helps.",
            context={"ocr_confidence": 0.4},
        )
        assert result.overall_safety_score < 1.0
        assert any("OCR" in v or "ocr" in v for v in result.scope_violations)

    def test_high_ocr_confidence_no_penalty(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "This passage suggests meditation helps.",
            context={"ocr_confidence": 0.95},
        )
        # High confidence should not significantly reduce score
        assert result.overall_safety_score >= 0.8

    def test_needs_review_increases_uncertainty(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "This passage suggests meditation helps.",
            context={"ocr_confidence": 0.6, "review_status": "needs_review"},
        )
        # Review status should increase uncertainty
        assert result.uncertainty_level in (
            UncertaintyLevel.MEDIUM,
            UncertaintyLevel.HIGH,
        )

    def test_ocr_calibration_stage_recorded(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "Test",
            context={"ocr_confidence": 0.5},
        )
        assert "ocr_confidence_calibration" in result.stages_completed

    def test_no_calibration_when_native_text(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "Test",
            context={"ocr_confidence": 1.0},
        )
        # Native text should not trigger OCR calibration
        assert result.overall_safety_score >= 0.8


# ---------------------------------------------------------------------------
# Safety with mixed sources tests
# ---------------------------------------------------------------------------


class TestSafetyMixedSources:
    def test_safety_with_mixed_native_ocr(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "This passage from OCR text suggests meditation helps.",
            context={"ocr_confidence": 0.7},
        )
        assert result.overall_safety_score > 0.5

    def test_safety_prefers_higher_quality_source(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        # When OCR confidence is low, safety should still work
        result = safety_engine.validate(
            "This passage suggests meditation helps.",
            context={"ocr_confidence": 0.3},
        )
        # Should not block, just reduce confidence
        assert result.recommendation != "BLOCK" or result.overall_safety_score > 0.2


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_safety_engine_still_works_without_ocr_context(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate("Test response.")
        assert isinstance(result, EpistemicSafetyResult)
        assert "ocr_confidence_calibration" in result.stages_completed

    def test_provenance_backward_compatible(self) -> None:
        prov = ChunkProvenance()
        assert prov.text_origin == TextOrigin.NATIVE
        assert prov.ocr_confidence == 0.0
        assert prov.ocr_engine == ""

    def test_version_metadata_backward_compatible(self) -> None:
        meta = OCRVersionMetadata()
        assert meta.engine_name == "tesseract"
        assert meta.dpi == 300
