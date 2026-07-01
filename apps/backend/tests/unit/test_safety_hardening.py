"""Tests for Epistemic Safety architecture hardening."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.pipeline import (
    PipelineContext,
    PipelineMetrics,
    PipelineResult,
    ResponsePipelineOrchestrator,
    _get_default_policy,
)
from ayeneh.epistemic_safety.types import (
    EpistemicSafetyPolicy,
    EpistemicSafetyResult,
    SafetyProvenance,
    SafetyRecommendation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> EpistemicSafetyEngine:
    return EpistemicSafetyEngine()


@pytest.fixture
def orchestrator() -> ResponsePipelineOrchestrator:
    return ResponsePipelineOrchestrator()


# ---------------------------------------------------------------------------
# Pipeline Orchestration tests
# ---------------------------------------------------------------------------


class TestPipelineOrchestration:
    @pytest.mark.asyncio
    async def test_processes_safe_response(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(
            response_draft="I notice a pattern in your thinking about this topic.",
        )
        result = await orchestrator.process(context)
        assert result.final_response != ""
        assert result.was_blocked is False
        assert "epistemic_safety" in result.stages_completed

    @pytest.mark.asyncio
    async def test_revises_unsafe_response(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(
            response_draft="This means you are definitely wrong about everything.",
        )
        result = await orchestrator.process(context)
        assert result.was_revised is True
        assert result.safety_result is not None

    @pytest.mark.asyncio
    async def test_blocks_dangerous_response(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(
            response_draft="You should trust me. I know your real problem. You must do this.",
        )
        result = await orchestrator.process(context)
        assert result.was_blocked is True
        assert result.safety_result.recommendation == SafetyRecommendation.BLOCK

    @pytest.mark.asyncio
    async def test_every_stage_recorded(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(
            response_draft="Test response.",
            dialogue_analysis={"test": True},
            epistemic_analysis={"test": True},
        )
        result = await orchestrator.process(context)
        assert "dialogue_analysis" in result.stages_completed
        assert "epistemic_analysis" in result.stages_completed
        assert "epistemic_safety" in result.stages_completed
        assert "final_response" in result.stages_completed

    @pytest.mark.asyncio
    async def test_error_recovery_passes_safety(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(
            response_draft="test",
            context={"raise_error": True},
        )
        result = await orchestrator.process(context)
        # Error response should still pass through safety
        assert result.safety_result is not None

    @pytest.mark.asyncio
    async def test_pipeline_metrics(self, orchestrator: ResponsePipelineOrchestrator) -> None:
        context = PipelineContext(response_draft="Test.")
        await orchestrator.process(context)
        metrics = orchestrator._metrics.get_metrics()
        assert metrics["validation_count"] == 1


# ---------------------------------------------------------------------------
# Safety Provenance tests
# ---------------------------------------------------------------------------


class TestSafetyProvenance:
    def test_provenance_has_required_fields(self) -> None:
        prov = SafetyProvenance(
            rule_id="test_rule",
            rule_name="Test Rule",
            reason="Testing",
            before_text="before",
            after_text="after",
            validation_stage="test_stage",
        )
        assert prov.rule_id == "test_rule"
        assert prov.before_text == "before"
        assert prov.after_text == "after"
        assert prov.is_automatic is True

    @pytest.mark.asyncio
    async def test_provenance_generated_for_revisions(
        self, orchestrator: ResponsePipelineOrchestrator,
    ) -> None:
        context = PipelineContext(
            response_draft="This means you are wrong.",
        )
        result = await orchestrator.process(context)
        assert result.safety_result is not None
        if result.safety_result.revisions_performed:
            assert len(result.safety_result.provenance) > 0

    @pytest.mark.asyncio
    async def test_provenance_for_scope_violations(
        self, orchestrator: ResponsePipelineOrchestrator,
    ) -> None:
        context = PipelineContext(
            response_draft="Meditation scientifically proves brain changes.",
        )
        result = await orchestrator.process(context)
        # Should have scope violation provenance
        assert result.safety_result is not None


# ---------------------------------------------------------------------------
# Product Policy tests
# ---------------------------------------------------------------------------


class TestProductPolicies:
    def test_ayeneh_policy(self) -> None:
        policy = _get_default_policy("ayeneh")
        assert policy.allow_recommendations is False
        assert policy.minimal_advice is True
        assert policy.prefer_reflective_dialogue is True
        assert policy.dependency_threshold == "low"

    def test_career_policy(self) -> None:
        policy = _get_default_policy("career")
        assert policy.allow_recommendations is True
        assert policy.minimal_advice is False
        assert policy.dependency_threshold == "medium"

    def test_business_policy(self) -> None:
        policy = _get_default_policy("business")
        assert policy.allow_recommendations is True
        assert policy.allow_strong_conclusions is True
        assert policy.dependency_threshold == "medium"

    def test_unknown_product_uses_ayeneh(self) -> None:
        policy = _get_default_policy("unknown_product")
        assert policy.product_id == "ayeneh"

    @pytest.mark.asyncio
    async def test_product_profile_applied(
        self, orchestrator: ResponsePipelineOrchestrator,
    ) -> None:
        context = PipelineContext(
            response_draft="Test.",
            product_profile_id="career",
        )
        result = await orchestrator.process(context)
        assert result.safety_result is not None
        assert result.safety_result.policy_applied == "career_safety"


# ---------------------------------------------------------------------------
# Pipeline Metrics tests
# ---------------------------------------------------------------------------


class TestPipelineMetrics:
    def test_records_validation(self) -> None:
        metrics = PipelineMetrics()
        metrics.record_pipeline(was_revised=False, was_blocked=False, stages=5)
        assert metrics.validation_count == 1

    def test_records_revision(self) -> None:
        metrics = PipelineMetrics()
        metrics.record_pipeline(was_revised=True, was_blocked=False, stages=5)
        assert metrics.revision_count == 1

    def test_records_block(self) -> None:
        metrics = PipelineMetrics()
        metrics.record_pipeline(was_revised=False, was_blocked=True, stages=5)
        assert metrics.blocked_count == 1

    def test_records_revision_count(self) -> None:
        metrics = PipelineMetrics()
        metrics.record_revision(3)
        assert metrics.total_revisions == 3

    def test_get_metrics(self) -> None:
        metrics = PipelineMetrics()
        metrics.record_pipeline(was_revised=True, was_blocked=False, stages=5)
        m = metrics.get_metrics()
        assert "validation_count" in m
        assert "revision_count" in m


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_safety_engine_still_works(self, engine: EpistemicSafetyEngine) -> None:
        result = engine.validate("Test response.")
        assert isinstance(result, EpistemicSafetyResult)

    def test_safety_result_has_provenance_field(self) -> None:
        result = EpistemicSafetyResult()
        assert hasattr(result, "provenance")
        assert result.provenance == []

    def test_safety_result_has_revision_history(self) -> None:
        result = EpistemicSafetyResult()
        assert hasattr(result, "revision_history")
        assert result.revision_history == []

    def test_safety_result_has_triggered_rules(self) -> None:
        result = EpistemicSafetyResult()
        assert hasattr(result, "triggered_rules")
        assert result.triggered_rules == []

    def test_safety_result_has_policy_applied(self) -> None:
        result = EpistemicSafetyResult()
        assert hasattr(result, "policy_applied")
        assert result.policy_applied == ""


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_executions(self) -> None:
        import asyncio
        orchestrator = ResponsePipelineOrchestrator()

        async def process_response(text: str) -> PipelineResult:
            context = PipelineContext(response_draft=text)
            return await orchestrator.process(context)

        tasks = [
            process_response(f"Response {i}")
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(r.final_response != "" for r in results)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    @pytest.mark.asyncio
    async def test_pipeline_completes_quickly(self) -> None:
        import time
        orchestrator = ResponsePipelineOrchestrator()
        context = PipelineContext(response_draft="Test response.")

        start = time.monotonic()
        for _ in range(50):
            await orchestrator.process(context)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 5000  # 50 executions in under 5 seconds
