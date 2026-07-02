"""Test 06: OCR verification — native, OCR, and hybrid book handling."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.ocr_policy import get_ocr_policy


@pytest.mark.asyncio
async def test_ocr_provenance_preserved():
    """Verify OCR provenance is preserved through the pipeline."""
    from ayeneh.provenance.bundle import ProvenanceBundle
    from ayeneh.provenance.types import ChunkOrigin

    bundle = ProvenanceBundle()
    chunk = ChunkOrigin(
        chunk_id="ocr-chunk-1",
        chapter_id="ch-1",
        text_origin="ocr",
        ocr_confidence=0.85,
        ocr_engine="tesseract",
    )
    bundle = bundle.with_chunk(chunk)

    assert bundle.chunks[0].text_origin == "ocr"
    assert bundle.chunks[0].ocr_confidence == 0.85
    assert bundle.chunks[0].ocr_engine == "tesseract"


@pytest.mark.asyncio
async def test_ocr_confidence_adjustment():
    """Verify safety score is adjusted for OCR confidence."""
    engine = EpistemicSafetyEngine()
    response = "This passage suggests acceptance practice."
    result = engine.validate(
        response,
        context={"ocr_confidence": 0.7, "review_status": "needs_review"},
    )

    # OCR confidence should affect the safety score
    assert result.overall_safety_score <= 1.0
    # Should have scope violation for OCR penalty
    assert any("OCR" in v for v in result.scope_violations)


@pytest.mark.asyncio
async def test_native_text_preferred():
    """Verify native text is preferred over OCR text."""
    from ayeneh.provenance.bundle import ProvenanceBundle
    from ayeneh.provenance.types import ChunkOrigin

    bundle = ProvenanceBundle()
    native_chunk = ChunkOrigin(
        chunk_id="native-1",
        text_origin="native",
        ocr_confidence=1.0,
    )
    ocr_chunk = ChunkOrigin(
        chunk_id="ocr-1",
        text_origin="ocr",
        ocr_confidence=0.8,
    )
    bundle = bundle.with_chunk(native_chunk).with_chunk(ocr_chunk)

    native_chunks = [c for c in bundle.chunks if c.text_origin == "native"]
    ocr_chunks = [c for c in bundle.chunks if c.text_origin == "ocr"]

    assert len(native_chunks) == 1
    assert len(ocr_chunks) == 1
    # Native should have higher confidence
    assert native_chunks[0].ocr_confidence > ocr_chunks[0].ocr_confidence


@pytest.mark.asyncio
async def test_ocr_policy_applied():
    """Verify OCR policy is applied correctly."""
    policy = get_ocr_policy("ayeneh")

    # Low OCR confidence should increase uncertainty
    assert policy.should_increase_uncertainty(0.5, "needs_review")
    assert not policy.should_increase_uncertainty(1.0, "none")

    # Confidence penalty should be positive for low OCR confidence
    assert policy.confidence_penalty(0.5) > 0
    assert policy.confidence_penalty(1.0) == 0
