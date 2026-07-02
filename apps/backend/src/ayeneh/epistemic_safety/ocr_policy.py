"""OCR Confidence Policy — configurable OCR confidence handling.

The Safety Layer asks the policy how OCR confidence should influence:
- confidence calibration
- uncertainty wording
- evidence weighting
- citation preference
- source preference

The engine never knows numeric thresholds. It only consumes the policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class OCRConfidencePolicy(Protocol):
    """Protocol for OCR confidence policies."""

    def calibrate_confidence(
        self,
        base_confidence: float,
        ocr_confidence: float,
        review_status: str,
    ) -> float:
        """Calibrate safety confidence based on OCR confidence."""
        ...

    def should_increase_uncertainty(
        self,
        ocr_confidence: float,
        review_status: str,
    ) -> bool:
        """Determine if uncertainty wording should be increased."""
        ...

    def should_prefer_alternative_source(
        self,
        ocr_confidence: float,
        has_native_alternative: bool,
    ) -> bool:
        """Determine if an alternative native source should be preferred."""
        ...

    def should_require_multiple_sources(
        self,
        ocr_confidence: float,
    ) -> bool:
        """Determine if multiple sources should be required."""
        ...

    def confidence_penalty(
        self,
        ocr_confidence: float,
    ) -> float:
        """Return the confidence penalty for OCR-extracted text."""
        ...


# ---------------------------------------------------------------------------
# Ayeneh Policy (Default - Conservative)
# ---------------------------------------------------------------------------


@dataclass
class AyenehOCRPolicy:
    """Ayeneh's conservative OCR confidence policy.

    Very conservative approach with high uncertainty disclosure.
    """

    # Thresholds (using curves, not fixed thresholds)
    low_confidence_threshold: float = 0.5
    medium_confidence_threshold: float = 0.7
    high_confidence_threshold: float = 0.85

    # Penalties
    low_confidence_penalty: float = 0.3
    medium_confidence_penalty: float = 0.15
    high_confidence_penalty: float = 0.05

    # Behavior flags
    always_require_multiple_sources: bool = False
    always_increase_uncertainty: bool = False

    def calibrate_confidence(
        self,
        base_confidence: float,
        ocr_confidence: float,
        review_status: str,
    ) -> float:
        penalty = self.confidence_penalty(ocr_confidence)
        calibrated = base_confidence * (1.0 - penalty)

        if review_status == "needs_review":
            calibrated *= 0.9

        return max(0.0, min(1.0, calibrated))

    def should_increase_uncertainty(
        self,
        ocr_confidence: float,
        review_status: str,
    ) -> bool:
        if self.always_increase_uncertainty:
            return True
        if review_status == "needs_review":
            return True
        return ocr_confidence < self.medium_confidence_threshold

    def should_prefer_alternative_source(
        self,
        ocr_confidence: float,
        has_native_alternative: bool,
    ) -> bool:
        if not has_native_alternative:
            return False
        return ocr_confidence < self.high_confidence_threshold

    def should_require_multiple_sources(
        self,
        ocr_confidence: float,
    ) -> bool:
        if self.always_require_multiple_sources:
            return True
        return ocr_confidence < self.medium_confidence_threshold

    def confidence_penalty(
        self,
        ocr_confidence: float,
    ) -> float:
        if ocr_confidence < self.low_confidence_threshold:
            return self.low_confidence_penalty
        elif ocr_confidence < self.medium_confidence_threshold:
            return self.medium_confidence_penalty
        elif ocr_confidence < self.high_confidence_threshold:
            return self.high_confidence_penalty
        return 0.0


# ---------------------------------------------------------------------------
# Career Policy (Action-Oriented)
# ---------------------------------------------------------------------------


@dataclass
class CareerOCRPolicy:
    """Career Mentor's OCR confidence policy.

    More permissive, action-oriented approach.
    """

    low_confidence_threshold: float = 0.4
    medium_confidence_threshold: float = 0.6
    high_confidence_threshold: float = 0.8

    low_confidence_penalty: float = 0.2
    medium_confidence_penalty: float = 0.1
    high_confidence_penalty: float = 0.03

    always_require_multiple_sources: bool = False
    always_increase_uncertainty: bool = False

    def calibrate_confidence(
        self,
        base_confidence: float,
        ocr_confidence: float,
        review_status: str,
    ) -> float:
        penalty = self.confidence_penalty(ocr_confidence)
        calibrated = base_confidence * (1.0 - penalty)
        return max(0.0, min(1.0, calibrated))

    def should_increase_uncertainty(
        self,
        ocr_confidence: float,
        review_status: str,
    ) -> bool:
        return ocr_confidence < self.low_confidence_threshold

    def should_prefer_alternative_source(
        self,
        ocr_confidence: float,
        has_native_alternative: bool,
    ) -> bool:
        if not has_native_alternative:
            return False
        return ocr_confidence < self.low_confidence_threshold

    def should_require_multiple_sources(
        self,
        ocr_confidence: float,
    ) -> bool:
        return ocr_confidence < self.low_confidence_threshold

    def confidence_penalty(
        self,
        ocr_confidence: float,
    ) -> float:
        if ocr_confidence < self.low_confidence_threshold:
            return self.low_confidence_penalty
        elif ocr_confidence < self.medium_confidence_threshold:
            return self.medium_confidence_penalty
        elif ocr_confidence < self.high_confidence_threshold:
            return self.high_confidence_penalty
        return 0.0


# ---------------------------------------------------------------------------
# Business Policy (Analytical)
# ---------------------------------------------------------------------------


@dataclass
class BusinessOCRPolicy:
    """Business Advisor's OCR confidence policy.

    Allows stronger conclusions while preserving uncertainty.
    """

    low_confidence_threshold: float = 0.35
    medium_confidence_threshold: float = 0.55
    high_confidence_threshold: float = 0.75

    low_confidence_penalty: float = 0.15
    medium_confidence_penalty: float = 0.08
    high_confidence_penalty: float = 0.02

    always_require_multiple_sources: bool = False
    always_increase_uncertainty: bool = False

    def calibrate_confidence(
        self,
        base_confidence: float,
        ocr_confidence: float,
        review_status: str,
    ) -> float:
        penalty = self.confidence_penalty(ocr_confidence)
        calibrated = base_confidence * (1.0 - penalty)
        return max(0.0, min(1.0, calibrated))

    def should_increase_uncertainty(
        self,
        ocr_confidence: float,
        review_status: str,
    ) -> bool:
        return ocr_confidence < self.low_confidence_threshold

    def should_prefer_alternative_source(
        self,
        ocr_confidence: float,
        has_native_alternative: bool,
    ) -> bool:
        if not has_native_alternative:
            return False
        return ocr_confidence < self.low_confidence_threshold

    def should_require_multiple_sources(
        self,
        ocr_confidence: float,
    ) -> bool:
        return ocr_confidence < self.low_confidence_threshold

    def confidence_penalty(
        self,
        ocr_confidence: float,
    ) -> float:
        if ocr_confidence < self.low_confidence_threshold:
            return self.low_confidence_penalty
        elif ocr_confidence < self.medium_confidence_threshold:
            return self.medium_confidence_penalty
        elif ocr_confidence < self.high_confidence_threshold:
            return self.high_confidence_penalty
        return 0.0


# ---------------------------------------------------------------------------
# Policy Registry
# ---------------------------------------------------------------------------


def get_ocr_policy(product_id: str) -> OCRConfidencePolicy:
    """Get the OCR confidence policy for a product."""
    policies: dict[str, OCRConfidencePolicy] = {
        "ayeneh": AyenehOCRPolicy(),
        "career": CareerOCRPolicy(),
        "business": BusinessOCRPolicy(),
    }
    return policies.get(product_id, AyenehOCRPolicy())
