"""Comprehensive tests for OCR confidence policy."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.ocr_policy import (
    AyenehOCRPolicy,
    BusinessOCRPolicy,
    CareerOCRPolicy,
    get_ocr_policy,
)
from ayeneh.epistemic_safety.types import EpistemicSafetyResult, UncertaintyLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def safety_engine() -> EpistemicSafetyEngine:
    return EpistemicSafetyEngine()


@pytest.fixture
def ayeneh_policy() -> AyenehOCRPolicy:
    return AyenehOCRPolicy()


@pytest.fixture
def career_policy() -> CareerOCRPolicy:
    return CareerOCRPolicy()


@pytest.fixture
def business_policy() -> BusinessOCRPolicy:
    return BusinessOCRPolicy()


# ---------------------------------------------------------------------------
# Policy Registry tests
# ---------------------------------------------------------------------------


class TestPolicyRegistry:
    def test_get_ayeneh_policy(self) -> None:
        policy = get_ocr_policy("ayeneh")
        assert isinstance(policy, AyenehOCRPolicy)

    def test_get_career_policy(self) -> None:
        policy = get_ocr_policy("career")
        assert isinstance(policy, CareerOCRPolicy)

    def test_get_business_policy(self) -> None:
        policy = get_ocr_policy("business")
        assert isinstance(policy, BusinessOCRPolicy)

    def test_unknown_product_returns_ayeneh(self) -> None:
        policy = get_ocr_policy("unknown")
        assert isinstance(policy, AyenehOCRPolicy)


# ---------------------------------------------------------------------------
# Ayeneh Policy tests
# ---------------------------------------------------------------------------


class TestAyenehOCRPolicy:
    def test_low_confidence_penalty(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        penalty = ayeneh_policy.confidence_penalty(0.3)
        assert penalty == 0.3

    def test_medium_confidence_penalty(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        penalty = ayeneh_policy.confidence_penalty(0.6)
        assert penalty == 0.15

    def test_high_confidence_penalty(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        penalty = ayeneh_policy.confidence_penalty(0.75)
        assert penalty == 0.05

    def test_no_penalty_high_confidence(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        penalty = ayeneh_policy.confidence_penalty(0.9)
        assert penalty == 0.0

    def test_calibrate_confidence(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        result = ayeneh_policy.calibrate_confidence(0.8, 0.5, "none")
        assert result < 0.8

    def test_should_increase_uncertainty(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        assert ayeneh_policy.should_increase_uncertainty(0.5, "none") is True
        assert ayeneh_policy.should_increase_uncertainty(0.9, "none") is False

    def test_should_prefer_alternative(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        assert ayeneh_policy.should_prefer_alternative_source(0.5, True) is True
        assert ayeneh_policy.should_prefer_alternative_source(0.9, True) is False
        assert ayeneh_policy.should_prefer_alternative_source(0.5, False) is False

    def test_should_require_multiple_sources(self, ayeneh_policy: AyenehOCRPolicy) -> None:
        assert ayeneh_policy.should_require_multiple_sources(0.5) is True
        assert ayeneh_policy.should_require_multiple_sources(0.9) is False


# ---------------------------------------------------------------------------
# Career Policy tests
# ---------------------------------------------------------------------------


class TestCareerOCRPolicy:
    def test_lower_thresholds(self, career_policy: CareerOCRPolicy) -> None:
        assert career_policy.low_confidence_threshold == 0.4
        assert career_policy.medium_confidence_threshold == 0.6

    def test_lower_penalties(self, career_policy: CareerOCRPolicy) -> None:
        penalty = career_policy.confidence_penalty(0.5)
        assert penalty == 0.1  # 0.5 is in medium range (0.4-0.6)

    def test_more_permissive(self, career_policy: CareerOCRPolicy) -> None:
        # Career policy should be more permissive than Ayeneh
        ayeneh = AyenehOCRPolicy()
        assert career_policy.confidence_penalty(0.6) < ayeneh.confidence_penalty(0.6)


# ---------------------------------------------------------------------------
# Business Policy tests
# ---------------------------------------------------------------------------


class TestBusinessOCRPolicy:
    def test_lowest_thresholds(self, business_policy: BusinessOCRPolicy) -> None:
        assert business_policy.low_confidence_threshold == 0.35
        assert business_policy.medium_confidence_threshold == 0.55

    def test_lowest_penalties(self, business_policy: BusinessOCRPolicy) -> None:
        penalty = business_policy.confidence_penalty(0.5)
        assert penalty == 0.08


# ---------------------------------------------------------------------------
# Safety Engine with Policy tests
# ---------------------------------------------------------------------------


class TestSafetyEngineWithPolicy:
    def test_safety_uses_policy_not_hardcoded(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "Test passage",
            context={"ocr_confidence": 0.5, "product_id": "career"},
        )
        assert result.overall_safety_score > 0.5

    def test_safety_different_products_different_results(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        ayeneh_result = safety_engine.validate(
            "Test passage",
            context={"ocr_confidence": 0.6},
        )
        career_result = safety_engine.validate(
            "Test passage",
            context={"ocr_confidence": 0.6, "product_id": "career"},
        )
        # Career policy is more permissive
        assert career_result.overall_safety_score >= ayeneh_result.overall_safety_score

    def test_no_hardcoded_thresholds_in_engine(self) -> None:
        """Verify engine doesn't contain hard-coded OCR thresholds."""
        import inspect
        source = inspect.getsource(EpistemicSafetyEngine._calibrate_ocr_confidence)
        assert "0.5" not in source
        assert "0.7" not in source
        assert "0.8" not in source


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_engine_still_works_without_product_id(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate(
            "Test passage",
            context={"ocr_confidence": 0.5},
        )
        assert isinstance(result, EpistemicSafetyResult)

    def test_engine_still_works_without_ocr_context(
        self, safety_engine: EpistemicSafetyEngine,
    ) -> None:
        result = safety_engine.validate("Test passage")
        assert isinstance(result, EpistemicSafetyResult)
