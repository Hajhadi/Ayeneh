"""Comprehensive tests for the Epistemic Safety Layer."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import (
    AuthorityDetector,
    DependencyDetector,
    EpistemicSafetyEngine,
    EvidenceValidator,
    FrameworkAttributor,
    ResponseReviser,
    ScopeValidator,
    StatementClassifier,
    UncertaintyCalibrator,
)
from ayeneh.epistemic_safety.types import (
    AuthorityCheck,
    AuthorityRisk,
    DependencyCheck,
    DependencyRisk,
    EpistemicSafetyResult,
    EvidenceStatus,
    FrameworkAttribution,
    Revision,
    SafetyRecommendation,
    StatementClassification,
    UncertaintyLevel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> EpistemicSafetyEngine:
    return EpistemicSafetyEngine()


@pytest.fixture
def classifier() -> StatementClassifier:
    return StatementClassifier()


@pytest.fixture
def evidence_validator() -> EvidenceValidator:
    return EvidenceValidator()


@pytest.fixture
def framework_attributor() -> FrameworkAttributor:
    return FrameworkAttributor()


@pytest.fixture
def scope_validator() -> ScopeValidator:
    return ScopeValidator()


@pytest.fixture
def uncertainty_calibrator() -> UncertaintyCalibrator:
    return UncertaintyCalibrator()


@pytest.fixture
def dependency_detector() -> DependencyDetector:
    return DependencyDetector()


@pytest.fixture
def authority_detector() -> AuthorityDetector:
    return AuthorityDetector()


@pytest.fixture
def response_reviser() -> ResponseReviser:
    return ResponseReviser()


# ---------------------------------------------------------------------------
# Statement Classifier tests
# ---------------------------------------------------------------------------


class TestStatementClassifier:
    def test_classifies_observation(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("I notice a pattern in your behavior")
        assert result == StatementClassification.OBSERVATION

    def test_classifies_interpretation(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("This means you are avoiding the issue")
        assert result == StatementClassification.INTERPRETATION

    def test_classifies_hypothesis(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("This might suggest a deeper issue")
        assert result == StatementClassification.HYPOTHESIS

    def test_classifies_inference(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("Therefore, we can conclude this")
        assert result == StatementClassification.INFERENCE

    def test_classifies_advice(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("You should try meditation")
        assert result == StatementClassification.ADVICE

    def test_classifies_question(self, classifier: StatementClassifier) -> None:
        result = classifier.classify("What do you think about this?")
        assert result == StatementClassification.QUESTION


# ---------------------------------------------------------------------------
# Evidence Validator tests
# ---------------------------------------------------------------------------


class TestEvidenceValidator:
    def test_validates_supported(self, evidence_validator: EvidenceValidator) -> None:
        result = evidence_validator.validate("According to the text, this is true")
        assert result == EvidenceStatus.SUPPORTED

    def test_validates_speculative(self, evidence_validator: EvidenceValidator) -> None:
        result = evidence_validator.validate("This might possibly be the case")
        assert result == EvidenceStatus.SPECULATIVE

    def test_validates_unsupported(self, evidence_validator: EvidenceValidator) -> None:
        result = evidence_validator.validate("You are clearly doing this wrong")
        assert result == EvidenceStatus.UNSUPPORTED


# ---------------------------------------------------------------------------
# Framework Attributor tests
# ---------------------------------------------------------------------------


class TestFrameworkAttributor:
    def test_attributes_neuroscience(self, framework_attributor: FrameworkAttributor) -> None:
        result = framework_attributor.attribute("The brain processes this through neural pathways")
        assert result == FrameworkAttribution.NEUROSCIENCE

    def test_attributes_act(self, framework_attributor: FrameworkAttributor) -> None:
        result = framework_attributor.attribute("This relates to acceptance and commitment therapy")
        assert result == FrameworkAttribution.ACT

    def test_attributes_zen(self, framework_attributor: FrameworkAttributor) -> None:
        result = framework_attributor.attribute("This is similar to Zen meditation practice")
        assert result == FrameworkAttribution.ZEN

    def test_attributes_unknown(self, framework_attributor: FrameworkAttributor) -> None:
        result = framework_attributor.attribute("Some random text without framework keywords")
        assert result == FrameworkAttribution.UNKNOWN


# ---------------------------------------------------------------------------
# Scope Validator tests
# ---------------------------------------------------------------------------


class TestScopeValidator:
    def test_valid_scope(self, scope_validator: ScopeValidator) -> None:
        is_valid, reason = scope_validator.validate("This meditation practice helps")
        assert is_valid is True

    def test_contemplative_to_scientific(self, scope_validator: ScopeValidator) -> None:
        is_valid, reason = scope_validator.validate(
            "Meditation scientifically proves brain changes"
        )
        assert is_valid is False
        assert "contemplative" in reason.lower() or "scientific" in reason.lower()

    def test_neuroscience_to_spiritual(self, scope_validator: ScopeValidator) -> None:
        is_valid, reason = scope_validator.validate(
            "Neuroscience proves spiritual enlightenment"
        )
        assert is_valid is False


# ---------------------------------------------------------------------------
# Uncertainty Calibrator tests
# ---------------------------------------------------------------------------


class TestUncertaintyCalibrator:
    def test_high_uncertainty(self, uncertainty_calibrator: UncertaintyCalibrator) -> None:
        result = uncertainty_calibrator.calibrate("This is uncertain and unclear", EvidenceStatus.SPECULATIVE)
        assert result == UncertaintyLevel.HIGH

    def test_low_uncertainty(self, uncertainty_calibrator: UncertaintyCalibrator) -> None:
        result = uncertainty_calibrator.calibrate("This is clearly true", EvidenceStatus.SUPPORTED)
        assert result == UncertaintyLevel.LOW

    def test_medium_uncertainty(self, uncertainty_calibrator: UncertaintyCalibrator) -> None:
        result = uncertainty_calibrator.calibrate("This may be the case", EvidenceStatus.SUPPORTED_INDIRECTLY)
        assert result == UncertaintyLevel.MEDIUM


# ---------------------------------------------------------------------------
# Dependency Detector tests
# ---------------------------------------------------------------------------


class TestDependencyDetector:
    def test_detects_no_dependency(self, dependency_detector: DependencyDetector) -> None:
        result = dependency_detector.detect("I notice a pattern in your thinking")
        assert result.detected is False
        assert result.risk_level == DependencyRisk.NONE

    def test_detects_low_dependency(self, dependency_detector: DependencyDetector) -> None:
        result = dependency_detector.detect("You must do this now")
        assert result.detected is True
        assert result.risk_level == DependencyRisk.LOW

    def test_detects_high_dependency(self, dependency_detector: DependencyDetector) -> None:
        result = dependency_detector.detect(
            "You should trust me. I know your real problem. You must do this."
        )
        assert result.detected is True
        assert result.risk_level in (DependencyRisk.MEDIUM, DependencyRisk.HIGH)


# ---------------------------------------------------------------------------
# Authority Detector tests
# ---------------------------------------------------------------------------


class TestAuthorityDetector:
    def test_detects_no_authority(self, authority_detector: AuthorityDetector) -> None:
        result = authority_detector.detect("This is one perspective to consider")
        assert result.detected is False
        assert result.risk_level == AuthorityRisk.NONE

    def test_detects_diagnosis(self, authority_detector: AuthorityDetector) -> None:
        result = authority_detector.detect("You have anxiety disorder")
        assert result.detected is True
        assert "diagnosis" in result.violations

    def test_detects_spiritual_ranking(self, authority_detector: AuthorityDetector) -> None:
        result = authority_detector.detect("You are enlightened now")
        assert result.detected is True
        assert "spiritual_ranking" in result.violations or "enlightenment_claim" in result.violations


# ---------------------------------------------------------------------------
# Response Reviser tests
# ---------------------------------------------------------------------------


class TestResponseReviser:
    def test_revises_this_means(self, response_reviser: ResponseReviser) -> None:
        revised, revisions = response_reviser.revise("This means you are wrong")
        assert "may suggest" in revised.lower()
        assert len(revisions) > 0

    def test_revises_you_are(self, response_reviser: ResponseReviser) -> None:
        revised, revisions = response_reviser.revise("You are clearly anxious")
        assert "explore whether" in revised.lower()
        assert len(revisions) > 0

    def test_no_revision_needed(self, response_reviser: ResponseReviser) -> None:
        revised, revisions = response_reviser.revise("This is a neutral statement")
        assert revised == "This is a neutral statement"
        assert len(revisions) == 0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestEpistemicSafetyEngine:
    def test_validates_safe_response(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("I notice a pattern in your thinking about this topic")
        assert result.overall_safety_score > 0.5
        assert result.recommendation in (SafetyRecommendation.PASS, SafetyRecommendation.REVISE)

    def test_detects_dependency_risk(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("You should trust me on this. I know your real problem.")
        assert result.dependency_risk in (DependencyRisk.LOW, DependencyRisk.MEDIUM, DependencyRisk.HIGH)

    def test_detects_authority_risk(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("You have anxiety disorder and need treatment")
        assert result.authority_risk in (AuthorityRisk.LOW, AuthorityRisk.MEDIUM, AuthorityRisk.HIGH)

    def test_blocks_dangerous_response(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate(
            "You should trust me. I know your real problem. "
            "You must do this. You are clearly at stage 3."
        )
        assert result.recommendation == SafetyRecommendation.BLOCK

    def test_revises_response(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("This means you are definitely wrong about everything")
        assert len(result.revisions_performed) > 0

    def test_returns_revised_response(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("This means you are wrong")
        assert result.revised_response != "This means you are wrong"

    def test_has_stages_completed(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("test")
        assert len(result.stages_completed) >= 7

    def test_counts_statements(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("First statement. Second statement. Third statement.")
        assert result.statement_count == 3

    def test_safe_response_passes(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate(
            "Based on the text, this passage suggests that "
            "contemplative practice may be beneficial for mental clarity"
        )
        assert result.recommendation == SafetyRecommendation.PASS


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_pipeline(self, engine: EpistemicSafetyEngine) -> None:
        response = (
            "I notice you've been reflecting on meditation. "
            "This might suggest a connection to mindfulness practice. "
            "One possible interpretation is that regular practice could help."
        )
        result = engine.validate(response)
        assert result.overall_safety_score > 0.5
        assert result.observation_count > 0
        assert result.interpretation_count > 0

    def test_with_context(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate(
            "According to the research, meditation helps",
            context={"sources": [{"title": "meditation research"}], "source_domain": "science"},
        )
        assert result.statement_count > 0


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_result_has_all_fields(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("test")
        assert hasattr(result, "overall_safety_score")
        assert hasattr(result, "recommendation")
        assert hasattr(result, "revisions_performed")
        assert hasattr(result, "revised_response")
