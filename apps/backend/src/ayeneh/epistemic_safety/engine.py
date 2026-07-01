"""EpistemicSafetyEngine — single owner of epistemic validation.

This is a cross-cutting architectural layer that sits above
Retrieval, Reasoning, Dialogue, Interpretation and Response Generation.

Its responsibility is to preserve epistemic humility, transparency
and intellectual honesty across the entire Ayeneh system.
"""

from __future__ import annotations

import re
import time
from typing import Any

import structlog

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
    StatementValidation,
    UncertaintyLevel,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Observation vs Interpretation
# ---------------------------------------------------------------------------


class StatementClassifier:
    """Classifies statements as observation, interpretation, hypothesis, etc."""

    def classify(self, text: str) -> str:
        """Classify a statement."""
        text_lower = text.lower()

        # Observation patterns
        if any(w in text_lower for w in [
            "i notice", "i observe", "i see", "i feel",
            "the user said", "the text states", "according to",
        ]):
            return StatementClassification.OBSERVATION

        # Interpretation patterns
        if any(w in text_lower for w in [
            "this means", "this suggests", "this indicates",
            "this could be interpreted", "one possible interpretation",
        ]):
            return StatementClassification.INTERPRETATION

        # Hypothesis patterns
        if any(w in text_lower for w in [
            "hypothesis", "might", "possibly", "perhaps",
            "it could be", "one possibility", "speculate",
        ]):
            return StatementClassification.HYPOTHESIS

        # Inference patterns
        if any(w in text_lower for w in [
            "therefore", "thus", "consequently", "implies",
            "based on", "given that", "since",
        ]):
            return StatementClassification.INFERENCE

        # Advice patterns
        if any(w in text_lower for w in [
            "you should", "you might want to", "consider",
            "try", "practice", "建议",
        ]):
            return StatementClassification.ADVICE

        # Question patterns
        if text.strip().endswith("?") or any(w in text_lower for w in [
            "what if", "have you considered", "i wonder",
        ]):
            return StatementClassification.QUESTION

        return StatementClassification.UNKNOWN


# ---------------------------------------------------------------------------
# Stage 2: Evidence Validation
# ---------------------------------------------------------------------------


class EvidenceValidator:
    """Validates evidence supporting claims."""

    def validate(
        self,
        text: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> str:
        """Validate evidence status."""
        text_lower = text.lower()

        # Check for explicit source references
        if sources:
            for source in sources:
                if source.get("title", "").lower() in text_lower:
                    return EvidenceStatus.SUPPORTED

        # Check for hedging language (indicates speculation)
        if any(w in text_lower for w in ["might", "possibly", "perhaps", "could be"]):
            return EvidenceStatus.SPECULATIVE

        # Check for direct quotes or references
        if any(w in text_lower for w in ["according to", "as stated", "the text says"]):
            return EvidenceStatus.SUPPORTED

        # Check for unsupported claims
        if any(w in text_lower for w in [
            "you are", "you must", "you should trust",
            "i know", "clearly", "obviously", "definitely",
        ]):
            return EvidenceStatus.UNSUPPORTED

        return EvidenceStatus.SUPPORTED_INDIRECTLY


# ---------------------------------------------------------------------------
# Stage 3: Framework Attribution
# ---------------------------------------------------------------------------


class FrameworkAttributor:
    """Attribue frameworks to claims."""

    def attribute(self, text: str) -> str:
        """Attribute a framework to the statement."""
        text_lower = text.lower()

        framework_keywords: dict[str, list[str]] = {
            FrameworkAttribution.NEUROSCIENCE: [
                "brain", "neural", "cognitive", "neuroscience", "prefrontal",
            ],
            FrameworkAttribution.ACT: [
                "acceptance", "commitment", "defusion", "values", "psychological flexibility",
            ],
            FrameworkAttribution.ANALYTICAL_PHILOSOPHY: [
                "truth", "reality", "knowledge", "logic", "argument",
            ],
            FrameworkAttribution.ZEN: [
                "zen", "meditation", "mindfulness", "presence", "awareness",
            ],
            FrameworkAttribution.KHORASAN_MYSTICISM: [
                "sufi", "mysticism", "divine", "love", "surrender",
            ],
            FrameworkAttribution.HISTORICAL_SOURCE: [
                "tradition", "historical", "ancient", "classical",
            ],
            FrameworkAttribution.COMPARATIVE_INTERPRETATION: [
                "compare", "similar", "different", "contrast", "versus",
            ],
        }

        for framework, keywords in framework_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return framework

        return FrameworkAttribution.UNKNOWN


# ---------------------------------------------------------------------------
# Stage 4: Scope Validation
# ---------------------------------------------------------------------------


class ScopeValidator:
    """Validates whether statements exceed their source scope."""

    def validate(
        self,
        text: str,
        source_domain: str = "",
    ) -> tuple[bool, str]:
        """Validate scope. Returns (is_valid, violation_reason)."""
        text_lower = text.lower()

        # Contemplative texts should not become scientific claims
        contemplative_terms = ["meditation", "contemplation", "spiritual", "mystical"]
        scientific_claims = [
            "proves", "scientifically proven", "research shows",
            "data indicates", "empirical evidence",
        ]

        if any(t in text_lower for t in contemplative_terms):
            if any(c in text_lower for c in scientific_claims):
                return False, "Contemplative source used to make scientific claims"

        # Neuroscience papers should not become spiritual authority
        neuroscience_terms = ["neuroscience", "brain", "neural", "cognitive"]
        spiritual_claims = [
            "enlightenment", "awakening", "spiritual truth",
            "divine revelation", "absolute truth",
        ]

        if any(t in text_lower for t in neuroscience_terms):
            if any(c in text_lower for c in spiritual_claims):
                return False, "Neuroscience source used to make spiritual authority claims"

        # Check for universal claims from limited sources
        universal_claims = [
            "always true", "never false", "universal truth",
            "absolute certainty", "proven beyond doubt",
        ]
        if any(c in text_lower for c in universal_claims):
            return False, "Universal claim from limited source"

        return True, ""


# ---------------------------------------------------------------------------
# Stage 5: Uncertainty Calibration
# ---------------------------------------------------------------------------


class UncertaintyCalibrator:
    """Calibrates uncertainty levels."""

    def calibrate(self, text: str, evidence_status: str) -> str:
        """Calibrate uncertainty level."""
        text_lower = text.lower()

        # High uncertainty indicators
        if any(w in text_lower for w in [
            "uncertain", "unclear", "ambiguous", "complex",
            "paradox", "tension", "difficult to say",
        ]):
            return UncertaintyLevel.HIGH

        if evidence_status == EvidenceStatus.SPECULATIVE:
            return UncertaintyLevel.HIGH

        if evidence_status == EvidenceStatus.UNSUPPORTED:
            return UncertaintyLevel.VERY_HIGH

        # Low uncertainty indicators
        if any(w in text_lower for w in [
            "clearly", "obviously", "definitely", "certainly",
        ]):
            return UncertaintyLevel.LOW

        if evidence_status == EvidenceStatus.SUPPORTED:
            return UncertaintyLevel.LOW

        return UncertaintyLevel.MEDIUM


# ---------------------------------------------------------------------------
# Stage 6: Dependency Safety
# ---------------------------------------------------------------------------


class DependencyDetector:
    """Detects dependency-creating language."""

    def detect(self, text: str) -> DependencyCheck:
        """Detect dependency risk."""
        text_lower = text.lower()
        patterns_found: list[str] = []
        suggestions: list[str] = []

        # Dependency patterns
        dependency_patterns: dict[str, list[str]] = {
            "trust_authority": ["you should trust me", "trust me on this"],
            "claim_knowledge": ["i know your real problem", "i know what you need"],
            "stage_claim": ["you are clearly at stage", "you are now ready"],
            "imperative": ["you must", "you need to", "you have to"],
            "certainty_claim": ["i am certain", "there is no doubt"],
        }

        for pattern_name, keywords in dependency_patterns.items():
            if any(kw in text_lower for kw in keywords):
                patterns_found.append(pattern_name)
                suggestions.append(f"Rewrite to avoid {pattern_name.replace('_', ' ')}")

        risk_level = DependencyRisk.NONE
        if len(patterns_found) >= 3:
            risk_level = DependencyRisk.HIGH
        elif len(patterns_found) >= 2:
            risk_level = DependencyRisk.MEDIUM
        elif len(patterns_found) >= 1:
            risk_level = DependencyRisk.LOW

        return DependencyCheck(
            detected=len(patterns_found) > 0,
            risk_level=risk_level,
            patterns_found=patterns_found,
            suggestions=suggestions,
        )


# ---------------------------------------------------------------------------
# Stage 7: Authority Safety
# ---------------------------------------------------------------------------


class AuthorityDetector:
    """Detects unauthorized authority claims."""

    def detect(self, text: str) -> AuthorityCheck:
        """Detect authority risk."""
        text_lower = text.lower()
        violations: list[str] = []
        suggestions: list[str] = []

        # Authority violation patterns
        authority_patterns: dict[str, list[str]] = {
            "diagnosis": ["you have", "you are diagnosed", "this is a disorder"],
            "spiritual_ranking": ["you are enlightened", "you have achieved"],
            "enlightenment_claim": ["you are awakened", "you have awakened"],
            "hidden_motives": ["your real motive", "subconsciously you"],
            "subconscious_certainty": ["you secretly", "deep down you know"],
        }

        for pattern_name, keywords in authority_patterns.items():
            if any(kw in text_lower for kw in keywords):
                violations.append(pattern_name)
                suggestions.append(f"Avoid {pattern_name.replace('_', ' ')} claims")

        risk_level = AuthorityRisk.NONE
        if len(violations) >= 3:
            risk_level = AuthorityRisk.HIGH
        elif len(violations) >= 2:
            risk_level = AuthorityRisk.MEDIUM
        elif len(violations) >= 1:
            risk_level = AuthorityRisk.LOW

        return AuthorityCheck(
            detected=len(violations) > 0,
            risk_level=risk_level,
            violations=violations,
            suggestions=suggestions,
        )


# ---------------------------------------------------------------------------
# Stage 8: Response Revision
# ---------------------------------------------------------------------------


class ResponseReviser:
    """Revises wording without changing meaning."""

    def revise(self, text: str) -> tuple[str, list[Revision]]:
        """Revise the response. Returns (revised_text, revisions)."""
        revisions: list[Revision] = []
        revised = text

        # Revision patterns
        revision_patterns: list[tuple[str, str, str, str]] = [
            # (pattern, replacement, reason, type)
            (r"This means", "This may suggest", "Hedging interpretation", "hedging"),
            (r"You are", "It might be useful to explore whether you are", "Reducing authority claim", "authority"),
            (r"This is because", "One possible interpretation is", "Hedging causal claim", "hedging"),
            (r"You should", "You might consider", "Reducing imperative", "dependency"),
            (r"You must", "It may be helpful to", "Reducing imperative", "dependency"),
            (r"I know", "It seems", "Reducing certainty claim", "authority"),
            (r"Clearly", "It appears", "Reducing certainty claim", "hedging"),
            (r"Obviously", "It seems", "Reducing certainty claim", "hedging"),
            (r"Definitely", "It likely", "Reducing certainty claim", "hedging"),
        ]

        for pattern, replacement, reason, rev_type in revision_patterns:
            matches = re.finditer(pattern, revised, re.IGNORECASE)
            for match in matches:
                original = match.group(0)
                revisions.append(Revision(
                    original=original,
                    revised=replacement,
                    reason=reason,
                    revision_type=rev_type,
                ))
                revised = revised.replace(original, replacement, 1)

        return revised, revisions


# ---------------------------------------------------------------------------
# Epistemic Safety Engine
# ---------------------------------------------------------------------------


class EpistemicSafetyEngine:
    """Single owner of epistemic validation.

    This is a cross-cutting architectural layer that sits above
    Retrieval, Reasoning, Dialogue, Interpretation and Response Generation.
    """

    def __init__(self) -> None:
        self._classifier = StatementClassifier()
        self._evidence_validator = EvidenceValidator()
        self._framework_attributor = FrameworkAttributor()
        self._scope_validator = ScopeValidator()
        self._uncertainty_calibrator = UncertaintyCalibrator()
        self._dependency_detector = DependencyDetector()
        self._authority_detector = AuthorityDetector()
        self._response_reviser = ResponseReviser()

    def validate(
        self,
        response: str,
        context: dict[str, Any] | None = None,
    ) -> EpistemicSafetyResult:
        """Validate a response through the multi-stage pipeline."""
        start = time.monotonic()
        ctx = context or {}

        result = EpistemicSafetyResult()

        # Stage 1: Classify statements
        statements = self._split_statements(response)
        for stmt in statements:
            classification = self._classifier.classify(stmt)
            if classification == StatementClassification.OBSERVATION:
                result.observation_count += 1
            elif classification == StatementClassification.INTERPRETATION:
                result.interpretation_count += 1
            elif classification == StatementClassification.HYPOTHESIS:
                result.hypothesis_count += 1

        result.statement_count = len(statements)
        result.stages_completed.append("statement_classification")

        # Stage 2: Evidence validation
        sources = ctx.get("sources", [])
        for stmt in statements:
            evidence = self._evidence_validator.validate(stmt, sources)
            if evidence == EvidenceStatus.UNSUPPORTED:
                result.unsupported_claims += 1
                result.unsupported_claim_texts.append(stmt[:100])
        result.stages_completed.append("evidence_validation")

        # Stage 3: Framework attribution
        frameworks_used: set[str] = set()
        for stmt in statements:
            framework = self._framework_attributor.attribute(stmt)
            frameworks_used.add(framework)
        result.stages_completed.append("framework_attribution")

        # Stage 4: Scope validation
        source_domain = ctx.get("source_domain", "")
        for stmt in statements:
            is_valid, reason = self._scope_validator.validate(stmt, source_domain)
            if not is_valid:
                result.scope_violations.append(reason)
        result.stages_completed.append("scope_validation")

        # Stage 5: Uncertainty calibration
        evidence_status = EvidenceStatus.SUPPORTED
        if result.unsupported_claims > 0:
            evidence_status = EvidenceStatus.UNSUPPORTED
        result.uncertainty_level = self._uncertainty_calibrator.calibrate(
            response, evidence_status,
        )
        result.stages_completed.append("uncertainty_calibration")

        # Stage 6: Dependency detection
        dep_check = self._dependency_detector.detect(response)
        result.dependency_check = dep_check
        result.dependency_risk = dep_check.risk_level
        result.stages_completed.append("dependency_detection")

        # Stage 7: Authority detection
        auth_check = self._authority_detector.detect(response)
        result.authority_check = auth_check
        result.authority_risk = auth_check.risk_level
        result.stages_completed.append("authority_detection")

        # Stage 8: Response revision
        revised, revisions = self._response_reviser.revise(response)
        result.revisions_performed = revisions
        result.revised_response = revised
        result.stages_completed.append("response_revision")

        # Compute overall safety score
        result.overall_safety_score = self._compute_safety_score(result)

        # Determine recommendation
        result.recommendation = self._determine_recommendation(result)

        result.validation_duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "epistemic_safety_validated",
            score=round(result.overall_safety_score, 2),
            recommendation=result.recommendation,
            revisions=len(revisions),
            duration_ms=round(result.validation_duration_ms, 2),
        )

        return result

    def _split_statements(self, text: str) -> list[str]:
        """Split text into individual statements."""
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _compute_safety_score(self, result: EpistemicSafetyResult) -> float:
        """Compute overall safety score."""
        score = 1.0

        # Penalize unsupported claims
        if result.unsupported_claims > 0:
            score -= 0.1 * min(result.unsupported_claims, 5)

        # Penalize scope violations
        if result.scope_violations:
            score -= 0.15 * min(len(result.scope_violations), 3)

        # Penalize dependency risk
        dep_penalties = {
            DependencyRisk.LOW: 0.1,
            DependencyRisk.MEDIUM: 0.2,
            DependencyRisk.HIGH: 0.3,
        }
        score -= dep_penalties.get(result.dependency_risk, 0)

        # Penalize authority risk
        auth_penalties = {
            AuthorityRisk.LOW: 0.1,
            AuthorityRisk.MEDIUM: 0.2,
            AuthorityRisk.HIGH: 0.3,
        }
        score -= auth_penalties.get(result.authority_risk, 0)

        # Penalize high uncertainty with unsupported claims
        if result.uncertainty_level == UncertaintyLevel.VERY_HIGH and result.unsupported_claims > 0:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _determine_recommendation(self, result: EpistemicSafetyResult) -> str:
        """Determine safety recommendation."""
        # Block if critical issues
        if result.authority_risk == AuthorityRisk.HIGH:
            return SafetyRecommendation.BLOCK
        if result.dependency_risk == DependencyRisk.HIGH:
            return SafetyRecommendation.BLOCK
        if result.unsupported_claims >= 3:
            return SafetyRecommendation.BLOCK

        # Revise if moderate issues
        if result.scope_violations:
            return SafetyRecommendation.REVISE
        if result.revisions_performed:
            return SafetyRecommendation.REVISE
        if result.unsupported_claims > 0:
            return SafetyRecommendation.REVISE
        if result.dependency_risk == DependencyRisk.MEDIUM:
            return SafetyRecommendation.REVISE
        if result.authority_risk == AuthorityRisk.MEDIUM:
            return SafetyRecommendation.REVISE

        # Pass if score is acceptable
        if result.overall_safety_score >= 0.7:
            return SafetyRecommendation.PASS

        # Revise if score is borderline
        return SafetyRecommendation.REVISE
