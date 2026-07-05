"""Response Validation and Generation Pipeline — per SPEC-25.

Final Runtime stage: validates reasoning and generates user-visible response.
No response may bypass this specification.

Processing Phases (SPEC-25 §4):
1. Preparation
2. Validation
3. Response Construction
4. Response Publication
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Response Artifact (SPEC-25 §13)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseArtifact:
    """Immutable response artifact — per SPEC-25 §13."""

    # Identity
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    request_id: str = ""
    reasoning_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Version tracking
    knowledge_version: str = "0.0.0"
    reasoning_version: str = "1.0.0"
    provider_version: str = "0.0.0"

    # Content
    response_text: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    uncertainty_statements: list[str] = field(default_factory=list)
    follow_up_suggestions: list[str] = field(default_factory=list)

    # Confidence
    overall_confidence: float = 0.0
    confidence_components: dict[str, float] = field(default_factory=dict)

    # Validation
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)

    # Metadata
    duration_ms: float = 0.0
    provider_used: str = ""
    producer: str = "response_engine"


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseValidationResult:
    """Result of response validation."""
    is_valid: bool = True
    evidence_complete: bool = True
    citation_complete: bool = True
    epistemic_safe: bool = True
    reasoning_intact: bool = True
    confidence_threshold: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Response Pipeline
# ---------------------------------------------------------------------------


class ResponsePipeline:
    """SPEC-25 compliant Response Validation and Generation pipeline.

    Validates reasoning artifacts and generates user-visible response.
    """

    def execute(
        self,
        reasoning_result: Any,
        query_analysis: Any = None,
        session_id: str = "",
        knowledge_version: str = "0.0.0",
    ) -> ResponseArtifact:
        """Execute the full Response pipeline."""
        start = time.monotonic()

        # Phase 1: Preparation
        phase1 = self._phase_preparation(reasoning_result, query_analysis)

        # Phase 2: Validation
        phase2 = self._phase_validation(reasoning_result, query_analysis)

        # Phase 3: Response Construction
        phase3 = self._phase_response_construction(reasoning_result, query_analysis, phase2)

        # Phase 4: Publication
        duration_ms = (time.monotonic() - start) * 1000
        result = self._phase_publication(
            reasoning_result, phase3, phase2,
            session_id, knowledge_version, duration_ms,
        )

        logger.debug(
            "response_complete",
            response_id=result.response_id,
            valid=result.validation_passed,
            text_length=len(result.response_text),
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: Preparation (SPEC-25 §5)
    # ------------------------------------------------------------------

    def _phase_preparation(self, reasoning_result: Any, query_analysis: Any) -> dict[str, Any]:
        """Validate upstream artifacts."""
        return {
            "reasoning_valid": reasoning_result is not None,
            "conclusions_available": len(getattr(reasoning_result, 'conclusions', [])) > 0,
            "query_analysis_valid": query_analysis is not None,
        }

    # ------------------------------------------------------------------
    # Phase 2: Validation (SPEC-25 §6-7)
    # ------------------------------------------------------------------

    def _phase_validation(
        self, reasoning_result: Any, query_analysis: Any
    ) -> ResponseValidationResult:
        """Validate reasoning before response generation."""
        conclusions = getattr(reasoning_result, 'conclusions', [])
        conflicts = getattr(reasoning_result, 'conflicts', [])
        evidence_refs = getattr(reasoning_result, 'evidence_references', [])
        confidence = getattr(reasoning_result, 'overall_confidence', 0.0)

        errors = []
        warnings = []

        # Evidence completeness
        evidence_complete = len(conclusions) > 0
        if not evidence_complete:
            errors.append("No conclusions available for response generation")

        # Citation completeness
        citation_complete = len(evidence_refs) > 0
        if not citation_complete:
            warnings.append("No evidence references available")

        # Epistemic safety (simplified)
        epistemic_safe = True
        if confidence < 0.3:
            warnings.append("Low confidence may affect response quality")

        # Reasoning integrity
        reasoning_intact = len(conclusions) > 0

        # Confidence threshold
        confidence_threshold = confidence >= 0.3
        if not confidence_threshold:
            warnings.append("Confidence below recommended threshold")

        return ResponseValidationResult(
            is_valid=len(errors) == 0,
            evidence_complete=evidence_complete,
            citation_complete=citation_complete,
            epistemic_safe=epistemic_safe,
            reasoning_intact=reasoning_intact,
            confidence_threshold=confidence_threshold,
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Phase 3: Response Construction (SPEC-25 §8-9)
    # ------------------------------------------------------------------

    def _phase_response_construction(
        self,
        reasoning_result: Any,
        query_analysis: Any,
        validation: ResponseValidationResult,
    ) -> dict[str, Any]:
        """Construct user-facing response from validated reasoning."""
        if not validation.is_valid:
            return {
                "response_text": "متأسفانه قادر به تولید پاسخ نیستم. لطفاً سؤال خود را واضح‌تر مطرح کنید.",
                "citations": [],
                "uncertainty": ["Validation failed"],
                "follow_up": [],
            }

        conclusions = getattr(reasoning_result, 'conclusions', [])
        evidence_refs = getattr(reasoning_result, 'evidence_references', [])
        conflicts = getattr(reasoning_result, 'conflicts', [])
        uncertainty = getattr(reasoning_result, 'uncertainty_statements', [])
        confidence = getattr(reasoning_result, 'overall_confidence', 0.5)
        intent = getattr(query_analysis, 'intent', 'question') if query_analysis else 'question'

        # Build response text from conclusions
        response_parts = []
        for conclusion in conclusions[:3]:
            statement = conclusion.get("statement", "")
            source = conclusion.get("source", "")
            if statement:
                response_parts.append(statement)

        response_text = " ".join(response_parts) if response_parts else "پاسخی یافت نشد."

        # Add uncertainty if present
        if uncertainty:
            response_text += "\n\nتوجه: " + " ".join(uncertainty[:2])

        # Build citations
        citations = []
        for ref in evidence_refs[:5]:
            citations.append({
                "source": ref.get("source", ""),
                "type": ref.get("type", "evidence"),
            })

        # Generate follow-up suggestions
        follow_up = []
        if intent == "definition":
            follow_up.append("آیا می‌خواهید درباره این موضوع بیشتر توضیح دهم؟")
        elif intent == "comparison":
            follow_up.append("آیا مقایسه عمیق‌تری می‌خواهید؟")
        else:
            follow_up.append("آیا سؤال دیگری دارید؟")

        return {
            "response_text": response_text,
            "citations": citations,
            "uncertainty": uncertainty,
            "follow_up": follow_up,
        }

    # ------------------------------------------------------------------
    # Phase 4: Response Publication (SPEC-25 §13)
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        reasoning_result: Any,
        construction: dict,
        validation: ResponseValidationResult,
        session_id: str,
        knowledge_version: str,
        duration_ms: float,
    ) -> ResponseArtifact:
        """Publish exactly one immutable ResponseArtifact."""
        return ResponseArtifact(
            session_id=session_id,
            reasoning_id=getattr(reasoning_result, 'reasoning_id', ''),
            knowledge_version=knowledge_version,
            reasoning_version=getattr(reasoning_result, 'reasoning_version', '1.0.0'),
            response_text=construction.get("response_text", ""),
            citations=construction.get("citations", []),
            uncertainty_statements=construction.get("uncertainty", []),
            follow_up_suggestions=construction.get("follow_up", []),
            overall_confidence=getattr(reasoning_result, 'overall_confidence', 0.5),
            confidence_components=getattr(reasoning_result, 'confidence_components', {}),
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
            duration_ms=duration_ms,
        )
