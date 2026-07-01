"""Pipeline Orchestration — guarantees mandatory Epistemic Safety gate.

This module ensures that EVERY user-visible response passes through
the Epistemic Safety Layer. No response path may bypass it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import structlog

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.types import (
    EpistemicSafetyPolicy,
    EpistemicSafetyResult,
    SafetyRecommendation,
    SafetyProvenance,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline Context
# ---------------------------------------------------------------------------


@dataclass
class PipelineContext:
    """Context for the response pipeline."""

    user_id: str = ""
    conversation_id: str = ""
    product_profile_id: str = "ayeneh"
    query: str = ""
    dialogue_analysis: Any = None
    epistemic_analysis: Any = None
    retrieval_result: Any = None
    reasoning_summary: Any = None
    interpretation: Any = None
    response_draft: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of the response pipeline."""

    final_response: str = ""
    safety_result: EpistemicSafetyResult | None = None
    was_revised: bool = False
    was_blocked: bool = False
    pipeline_duration_ms: float = 0.0
    stages_completed: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline Orchestrator
# ---------------------------------------------------------------------------


class ResponsePipelineOrchestrator:
    """Single orchestration point for the response pipeline.

    Guarantees that EVERY user-visible response passes through
    the Epistemic Safety Layer. No response path may bypass it.
    """

    def __init__(
        self,
        safety_engine: EpistemicSafetyEngine | None = None,
        policy_provider: Any | None = None,
    ) -> None:
        self._safety_engine = safety_engine or EpistemicSafetyEngine()
        self._policy_provider = policy_provider
        self._metrics = PipelineMetrics()

    async def process(
        self,
        context: PipelineContext,
    ) -> PipelineResult:
        """Process a response through the mandatory pipeline.

        This is the ONLY entry point for user-visible responses.
        """
        start = time.monotonic()
        result = PipelineResult()

        try:
            # Stage 1: Dialogue Analysis (if provided)
            if context.dialogue_analysis:
                result.stages_completed.append("dialogue_analysis")

            # Stage 2: Epistemic Analysis (if provided)
            if context.epistemic_analysis:
                result.stages_completed.append("epistemic_analysis")

            # Stage 3: Knowledge Retrieval (if provided)
            if context.retrieval_result:
                result.stages_completed.append("knowledge_retrieval")

            # Stage 4: Reasoning Engine (if provided)
            if context.reasoning_summary:
                result.stages_completed.append("reasoning_engine")

            # Stage 5: Interpretation Layer (if provided)
            if context.interpretation:
                result.stages_completed.append("interpretation_layer")

            # Stage 6: Response Draft
            response = context.response_draft
            result.stages_completed.append("response_draft")

            # Stage 7: MANDATORY Epistemic Safety Layer
            safety_result = await self._validate_response(response, context)
            result.safety_result = safety_result
            result.stages_completed.append("epistemic_safety")

            # Stage 8: Apply safety decision
            if safety_result.recommendation == SafetyRecommendation.BLOCK:
                result.final_response = self._generate_blocked_response(safety_result)
                result.was_blocked = True
                self._metrics.record_block()
            elif safety_result.recommendation == SafetyRecommendation.REVISE:
                result.final_response = safety_result.revised_response
                result.was_revised = True
                self._metrics.record_revision(len(safety_result.revisions_performed))
            else:
                result.final_response = response

            result.stages_completed.append("final_response")

        except Exception as exc:
            # Error recovery responses must also pass through safety
            logger.exception("pipeline_error", error=str(exc))
            error_response = self._generate_error_response(exc)
            safety_result = await self._validate_response(error_response, context)
            result.final_response = safety_result.revised_response
            result.safety_result = safety_result
            result.was_revised = safety_result.recommendation == SafetyRecommendation.REVISE
            result.stages_completed.append("error_recovery")

        result.pipeline_duration_ms = (time.monotonic() - start) * 1000

        # Record metrics
        self._metrics.record_pipeline(
            was_revised=result.was_revised,
            was_blocked=result.was_blocked,
            stages=len(result.stages_completed),
        )

        return result

    async def process_streaming(
        self,
        context: PipelineContext,
    ) -> AsyncIterator[str]:
        """Process a streaming response through the mandatory pipeline.

        Streaming responses must also be validated.
        """
        # Collect the full response first for validation
        chunks: list[str] = []
        async for chunk in self._stream_generator(context):
            chunks.append(chunk)

        full_response = "".join(chunks)

        # Validate the full response
        safety_result = await self._validate_response(full_response, context)

        # Yield the validated response
        if safety_result.recommendation == SafetyRecommendation.BLOCK:
            yield self._generate_blocked_response(safety_result)
        elif safety_result.recommendation == SafetyRecommendation.REVISE:
            yield safety_result.revised_response
        else:
            yield full_response

    async def _stream_generator(
        self,
        context: PipelineContext,
    ) -> AsyncIterator[str]:
        """Generate streaming chunks (placeholder for actual streaming)."""
        # In production, this would call the actual LLM streaming
        yield context.response_draft

    async def _validate_response(
        self,
        response: str,
        context: PipelineContext,
    ) -> EpistemicSafetyResult:
        """Validate response through the Epistemic Safety Layer."""
        # Load product-specific policy
        policy = await self._load_policy(context.product_profile_id)

        # Build validation context
        validation_context = {
            "sources": context.context.get("sources", []),
            "source_domain": context.context.get("source_domain", ""),
            "product_profile": context.product_profile_id,
            "policy": policy,
        }

        # Run safety validation
        result = self._safety_engine.validate(response, validation_context)

        # Apply policy-specific adjustments
        if policy:
            result = self._apply_policy(result, policy)

        # Record provenance
        result.provenance = self._build_provenance(result, context)

        return result

    async def _load_policy(self, product_id: str) -> EpistemicSafetyPolicy | None:
        """Load product-specific safety policy."""
        if self._policy_provider:
            try:
                return await self._policy_provider.get_policy(product_id)
            except Exception:
                pass
        return _get_default_policy(product_id)

    def _apply_policy(
        self,
        result: EpistemicSafetyResult,
        policy: EpistemicSafetyPolicy,
    ) -> EpistemicSafetyResult:
        """Apply product-specific policy to safety result."""
        result.policy_applied = policy.policy_id or policy.product_id

        # Apply threshold adjustments
        if policy.dependency_threshold == "high" and result.dependency_risk == "medium":
            result.recommendation = SafetyRecommendation.PASS

        if policy.authority_threshold == "high" and result.authority_risk == "medium":
            result.recommendation = SafetyRecommendation.PASS

        # Apply intervention threshold
        if not policy.allow_recommendations and result.recommendation == SafetyRecommendation.PASS:
            # Check if advice was detected
            if any(r.revision_type == "dependency" for r in result.revisions_performed):
                result.recommendation = SafetyRecommendation.REVISE

        return result

    def _build_provenance(
        self,
        result: EpistemicSafetyResult,
        context: PipelineContext,
    ) -> list[SafetyProvenance]:
        """Build provenance for all safety interventions."""
        provenance: list[SafetyProvenance] = []

        for revision in result.revisions_performed:
            provenance.append(SafetyProvenance(
                rule_id=f"revision_{revision.revision_type}",
                rule_name=f"Auto-revision: {revision.revision_type}",
                reason=revision.reason,
                before_text=revision.original,
                after_text=revision.revised,
                affected_statement=revision.original[:100],
                validation_stage="response_revision",
                confidence=1.0,
                severity="low",
                is_automatic=True,
            ))

        for violation in result.scope_violations:
            provenance.append(SafetyProvenance(
                rule_id="scope_violation",
                rule_name="Scope Validation",
                reason=violation,
                validation_stage="scope_validation",
                confidence=0.9,
                severity="medium",
                is_automatic=True,
            ))

        for claim in result.unsupported_claim_texts:
            provenance.append(SafetyProvenance(
                rule_id="unsupported_claim",
                rule_name="Evidence Validation",
                reason=f"Unsupported claim detected: {claim[:50]}",
                affected_statement=claim,
                validation_stage="evidence_validation",
                confidence=0.8,
                severity="medium",
                is_automatic=True,
            ))

        return provenance

    def _generate_blocked_response(self, result: EpistemicSafetyResult) -> str:
        """Generate a safe blocked response."""
        return (
            "I notice this response may not meet our epistemic safety standards. "
            "Let me rephrase to ensure accuracy and appropriateness."
        )

    def _generate_error_response(self, exc: Exception) -> str:
        """Generate a safe error response."""
        return (
            "I encountered an issue while processing your request. "
            "Let me try a different approach."
        )


# ---------------------------------------------------------------------------
# Pipeline Metrics
# ---------------------------------------------------------------------------


@dataclass
class PipelineMetrics:
    """Metrics for pipeline operations."""

    validation_count: int = 0
    revision_count: int = 0
    blocked_count: int = 0
    total_revisions: int = 0
    average_revisions_per_response: float = 0.0

    def record_pipeline(
        self,
        was_revised: bool,
        was_blocked: bool,
        stages: int,
    ) -> None:
        """Record pipeline execution."""
        self.validation_count += 1
        if was_revised:
            self.revision_count += 1
        if was_blocked:
            self.blocked_count += 1

    def record_revision(self, count: int) -> None:
        """Record revisions."""
        self.total_revisions += count
        if self.validation_count > 0:
            self.average_revisions_per_response = (
                self.total_revisions / self.validation_count
            )

    def record_block(self) -> None:
        """Record a blocked response."""
        self.blocked_count += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get pipeline metrics."""
        return {
            "validation_count": self.validation_count,
            "revision_count": self.revision_count,
            "blocked_count": self.blocked_count,
            "total_revisions": self.total_revisions,
            "average_revisions_per_response": self.average_revisions_per_response,
        }


# ---------------------------------------------------------------------------
# Default Policies
# ---------------------------------------------------------------------------


def _get_default_policy(product_id: str) -> EpistemicSafetyPolicy:
    """Get default safety policy for a product."""
    policies: dict[str, EpistemicSafetyPolicy] = {
        "ayeneh": EpistemicSafetyPolicy(
            policy_id="ayeneh_safety",
            product_id="ayeneh",
            dependency_threshold="low",
            authority_threshold="low",
            uncertainty_disclosure_threshold="medium",
            allow_recommendations=False,
            allow_strong_conclusions=False,
            require_evidence_citations=True,
            require_uncertainty_disclosure=True,
            require_framework_attribution=True,
            require_scope_validation=True,
            prefer_reflective_dialogue=True,
            minimal_advice=True,
            intervention_threshold=0.7,
            block_threshold=0.3,
        ),
        "career": EpistemicSafetyPolicy(
            policy_id="career_safety",
            product_id="career",
            dependency_threshold="medium",
            authority_threshold="medium",
            uncertainty_disclosure_threshold="low",
            allow_recommendations=True,
            allow_strong_conclusions=False,
            require_evidence_citations=True,
            require_uncertainty_disclosure=False,
            require_framework_attribution=True,
            require_scope_validation=True,
            prefer_reflective_dialogue=False,
            minimal_advice=False,
            intervention_threshold=0.6,
            block_threshold=0.25,
        ),
        "business": EpistemicSafetyPolicy(
            policy_id="business_safety",
            product_id="business",
            dependency_threshold="medium",
            authority_threshold="medium",
            uncertainty_disclosure_threshold="low",
            allow_recommendations=True,
            allow_strong_conclusions=True,
            require_evidence_citations=True,
            require_uncertainty_disclosure=False,
            require_framework_attribution=False,
            require_scope_validation=True,
            prefer_reflective_dialogue=False,
            minimal_advice=False,
            intervention_threshold=0.5,
            block_threshold=0.2,
        ),
    }
    return policies.get(product_id, policies["ayeneh"])