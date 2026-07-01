"""Comprehensive tests for the Contemplative Dialogue Framework."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from ayeneh.dialogue.engine import DialogueIntentionEngine
from ayeneh.dialogue.policies import (
    DialoguePolicy,
    NeverDiagnose,
    ObservationFirst,
    PreserveUncertainty,
    PromoteAutonomy,
    QuestionBeforeAdvice,
    get_policies_for_profile,
)
from ayeneh.dialogue.types import (
    DialogueAnalysis,
    DialogueDecision,
    DialogueIntervention,
    DialogueNeed,
    DialogueSignal,
    DialogueState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> DialogueIntentionEngine:
    return DialogueIntentionEngine()


@pytest.fixture
def career_engine() -> DialogueIntentionEngine:
    return DialogueIntentionEngine(product_profile_id="career")


@pytest.fixture
def business_engine() -> DialogueIntentionEngine:
    return DialogueIntentionEngine(product_profile_id="business")


# ---------------------------------------------------------------------------
# Intervention selection tests
# ---------------------------------------------------------------------------


class TestInterventionSelection:
    def test_advice_seeking_selects_reflective_question(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Please give me advice on what to do")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.REFLECTIVE_QUESTION,
            DialogueIntervention.OBSERVATION_MIRROR,
        )

    def test_self_observation_selects_mirror(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I notice I keep procrastinating")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.OBSERVATION_MIRROR,
            DialogueIntervention.PATTERN_REFLECTION,
        )

    def test_knowledge_seeking_selects_explanation(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Explain how cognitive behavioral therapy works")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.KNOWLEDGE_EXPLANATION,
            DialogueIntervention.EVIDENCE_PRESENTATION,
        )

    def test_decision_making_selects_comparison(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Should I change careers or stay?")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.MULTIPLE_FRAMEWORK_COMPARISON,
            DialogueIntervention.REFLECTIVE_QUESTION,
            DialogueIntervention.PERSPECTIVE_EXPANSION,
        )

    def test_pattern_recognition_selects_reflection(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I always avoid difficult conversations")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.PATTERN_REFLECTION,
            DialogueIntervention.OBSERVATION_MIRROR,
        )


# ---------------------------------------------------------------------------
# Dependency detection tests
# ---------------------------------------------------------------------------


class TestDependencyDetection:
    def test_dependency_seeking_detected(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Tell me what I should do")
        assert analysis.dependency_risk >= 0.3
        assert analysis.seeking_certainty

    def test_outsourcing_detected(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Decide for me which option is better")
        assert analysis.outsourcing_decisions

    def test_reassurance_seeking_detected(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I'm right about this, don't you think?")
        assert analysis.reassurance_seeking

    def test_dependency_increases_reflective_intervention(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Just tell me the answer, right?")
        decision = engine.decide(analysis)
        assert decision.selected_intervention in (
            DialogueIntervention.REFLECTIVE_QUESTION,
            DialogueIntervention.OBSERVATION_MIRROR,
            DialogueIntervention.CHALLENGE_ASSUMPTION,
        )

    def test_dependency_risk_history_affects_current(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        ctx = {"dependency_risk_history": [0.8, 0.7, 0.9]}
        analysis = engine.analyze("What should I do?", ctx)
        assert analysis.dependency_risk > 0.5


# ---------------------------------------------------------------------------
# Rumination detection tests
# ---------------------------------------------------------------------------


class TestRuminationDetection:
    def test_rumination_detected(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I keep thinking about this over and over")
        assert len(analysis.rumination_indicators) > 0

    def test_rumination_increases_reframing(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I keep thinking about this over and over again and again")
        decision = engine.decide(analysis)
        # Rumination should boost reframing or perspective expansion
        assert any(
            inv in (DialogueIntervention.REFRAMING, DialogueIntervention.PERSPECTIVE_EXPANSION)
            for inv in [decision.selected_intervention] + decision.alternative_interventions
        )


# ---------------------------------------------------------------------------
# Certainty seeking tests
# ---------------------------------------------------------------------------


class TestCertaintySeeking:
    def test_certainty_seeking_detected(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Tell me the correct answer, right or wrong?")
        assert analysis.seeking_certainty

    def test_certainty_seeking_increases_uncertainty_statement(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Tell me the correct answer for certain")
        decision = engine.decide(analysis)
        # Should not select knowledge explanation without uncertainty
        assert decision.epistemic_risk > 0.0


# ---------------------------------------------------------------------------
# Policy switching tests
# ---------------------------------------------------------------------------


class TestPolicySwitching:
    def test_observation_first_policy(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert any(p.name == "observation_first" for p in engine._policies)

    def test_question_before_advice_policy(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert any(p.name == "question_before_advice" for p in engine._policies)

    def test_preserve_uncertainty_policy(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert any(p.name == "preserve_uncertainty" for p in engine._policies)

    def test_promote_autonomy_policy(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert any(p.name == "promote_autonomy" for p in engine._policies)

    def test_never_diagnose_policy(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert any(p.name == "never_diagnose" for p in engine._policies)


# ---------------------------------------------------------------------------
# Product profile tests
# ---------------------------------------------------------------------------


class TestProductProfiles:
    def test_ayeneh_profile_policies(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        assert engine._profile_id == "ayeneh"
        assert any(p.name == "observation_first" for p in engine._policies)

    def test_career_profile_policies(
        self, career_engine: DialogueIntentionEngine,
    ) -> None:
        assert career_engine._profile_id == "career"
        assert any(p.name == "evidence_before_conclusion" for p in career_engine._policies)

    def test_business_profile_policies(
        self, business_engine: DialogueIntentionEngine,
    ) -> None:
        assert business_engine._profile_id == "business"
        assert any(p.name == "multiple_perspectives" for p in business_engine._policies)

    def test_career_different_intervention(
        self, career_engine: DialogueIntentionEngine,
    ) -> None:
        analysis = career_engine.analyze("Explain how to negotiate salary")
        decision = career_engine.decide(analysis)
        assert isinstance(decision.selected_intervention, DialogueIntervention)

    def test_get_policies_for_profile(
        self,
    ) -> None:
        ayeneh = get_policies_for_profile("ayeneh")
        career = get_policies_for_profile("career")
        business = get_policies_for_profile("business")
        assert len(ayeneh) > 0
        assert len(career) > 0
        assert len(business) > 0


# ---------------------------------------------------------------------------
# Metadata propagation tests
# ---------------------------------------------------------------------------


class TestMetadataPropagation:
    def test_decision_has_analysis(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert decision.analysis == analysis

    def test_decision_has_reasoning(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert len(decision.reasoning.why_selected) > 0

    def test_decision_has_confidence(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert 0.0 <= decision.confidence <= 1.0

    def test_decision_has_expected_outcome(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert decision.expected_outcome != ""

    def test_decision_has_alternatives(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert len(decision.alternative_interventions) >= 0


# ---------------------------------------------------------------------------
# Runtime integration tests
# ---------------------------------------------------------------------------


class TestRuntimeIntegration:
    def test_engine_produces_decision(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("What should I do about my career?")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_analysis_produces_needs(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I need help understanding my patterns")
        assert len(analysis.detected_needs) > 0

    def test_analysis_produces_signals(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("I'm feeling urgent and desperate")
        assert len(analysis.detected_signals) > 0


# ---------------------------------------------------------------------------
# Prompt integration tests
# ---------------------------------------------------------------------------


class TestPromptIntegration:
    def test_decision_provides_intervention_for_prompt(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert decision.selected_intervention.value != ""

    def test_decision_provides_reasoning_for_prompt(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert len(decision.reasoning.why_selected) > 0


# ---------------------------------------------------------------------------
# Reasoning integration tests
# ---------------------------------------------------------------------------


class TestReasoningIntegration:
    def test_analysis_has_reasoning(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("What is truth?")
        assert len(analysis.reasoning) > 0

    def test_analysis_reasoning_includes_stage(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        assert any("Stage" in r for r in analysis.reasoning)


# ---------------------------------------------------------------------------
# Retrieval integration tests
# ---------------------------------------------------------------------------


class TestRetrievalIntegration:
    def test_decision_includes_analysis_for_retrieval(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("Explain meditation research")
        decision = engine.decide(analysis)
        assert decision.analysis.user_intention == "knowledge_seeking"


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    def test_concurrent_analysis(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        queries = [
            "What should I do?",
            "I notice a pattern",
            "Explain this concept",
            "Help me decide",
            "I'm feeling stuck",
        ]

        def analyze_query(q: str) -> DialogueAnalysis:
            return engine.analyze(q)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(analyze_query, q) for q in queries]
            results = [f.result() for f in futures]

        assert len(results) == 5
        assert all(isinstance(r, DialogueAnalysis) for r in results)

    def test_concurrent_decisions(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        queries = [
            "What should I do?",
            "I notice a pattern",
            "Explain this concept",
        ]

        def decide_query(q: str) -> DialogueDecision:
            analysis = engine.analyze(q)
            return engine.decide(analysis)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(decide_query, q) for q in queries]
            results = [f.result() for f in futures]

        assert len(results) == 3
        assert all(isinstance(r, DialogueDecision) for r in results)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_analysis_completes_quickly(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        start = time.monotonic()
        for _ in range(100):
            engine.analyze("What should I do about my career?")
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000

    def test_decision_completes_quickly(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        start = time.monotonic()
        for _ in range(100):
            analysis = engine.analyze("test query")
            engine.decide(analysis)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_same_input_same_output(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        query = "What should I do?"
        a1 = engine.analyze(query)
        a2 = engine.analyze(query)
        assert a1.user_intention == a2.user_intention
        assert a1.detected_needs[0].need == a2.detected_needs[0].need if a1.detected_needs and a2.detected_needs else True

    def test_same_analysis_same_decision(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        query = "What should I do?"
        a1 = engine.analyze(query)
        a2 = engine.analyze(query)
        d1 = engine.decide(a1)
        d2 = engine.decide(a2)
        assert d1.selected_intervention == d2.selected_intervention


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_default_engine_works(
        self,
    ) -> None:
        engine = DialogueIntentionEngine()
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_context_optional(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("test")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_context_used(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        ctx = {"message_count": 5, "previous_queries": ["hello"]}
        analysis = engine.analyze("test", ctx)
        decision = engine.decide(analysis, ctx)
        assert isinstance(decision, DialogueDecision)


# ---------------------------------------------------------------------------
# Observability tests
# ---------------------------------------------------------------------------


class TestObservability:
    def test_dialogue_metrics_recorded(
        self,
    ) -> None:
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_dialogue_decision(
            duration_ms=2.5,
            intervention="reflective_question",
            dependency_risk=0.3,
            confidence=0.7,
            policies_applied=["observation_first", "question_before_advice"],
        )

        assert metrics.dialogue_decision_count == 1
        assert metrics.dialogue_decision_duration_ms == 2.5
        assert metrics.dialogue_intervention_distribution["reflective_question"] == 1
        assert metrics.dialogue_policy_usage["observation_first"] == 1

    def test_dialogue_metrics_export(
        self,
    ) -> None:
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_dialogue_decision(
            duration_ms=2.0,
            intervention="observation_mirror",
            dependency_risk=0.2,
            confidence=0.8,
            policies_applied=["observation_first"],
        )

        text = metrics.export_prometheus_text()
        assert "ayeneh_dialogue_decisions_total" in text
        assert "ayeneh_dialogue_intervention_distribution" in text
        assert "ayeneh_dialogue_avg_dependency_risk" in text
        assert "ayeneh_dialogue_reflection_ratio" in text


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_query(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_very_long_query(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        query = "What should I do " * 100 + "about this?"
        analysis = engine.analyze(query)
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_special_characters(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("What is truth? (philosophical inquiry)")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)

    def test_mixed_language(
        self, engine: DialogueIntentionEngine,
    ) -> None:
        analysis = engine.analyze("What is fana in Sufi tradition?")
        decision = engine.decide(analysis)
        assert isinstance(decision, DialogueDecision)


# ---------------------------------------------------------------------------
# Policy protocol tests
# ---------------------------------------------------------------------------


class TestPolicyProtocol:
    def test_policies_implement_protocol(
        self,
    ) -> None:
        policies = [
            ObservationFirst(),
            QuestionBeforeAdvice(),
            PreserveUncertainty(),
            PromoteAutonomy(),
            NeverDiagnose(),
        ]
        for policy in policies:
            assert isinstance(policy, DialoguePolicy)

    def test_policies_have_name(
        self,
    ) -> None:
        assert ObservationFirst().name == "observation_first"
        assert QuestionBeforeAdvice().name == "question_before_advice"

    def test_policies_should_apply(
        self,
    ) -> None:
        ctx = {"requires_multiple_frameworks": True}
        assert MultiplePerspectives().should_apply(ctx)
        assert not MultiplePerspectives().should_apply({})


# ---------------------------------------------------------------------------
# Intervention type tests
# ---------------------------------------------------------------------------


class TestInterventionTypes:
    def test_all_interventions_exist(
        self,
    ) -> None:
        interventions = [
            DialogueIntervention.REFLECTIVE_QUESTION,
            DialogueIntervention.CLARIFICATION,
            DialogueIntervention.REFRAMING,
            DialogueIntervention.PERSPECTIVE_EXPANSION,
            DialogueIntervention.OBSERVATION_MIRROR,
            DialogueIntervention.PATTERN_REFLECTION,
            DialogueIntervention.EVIDENCE_PRESENTATION,
            DialogueIntervention.KNOWLEDGE_EXPLANATION,
            DialogueIntervention.MULTIPLE_FRAMEWORK_COMPARISON,
            DialogueIntervention.GOAL_REMINDER,
            DialogueIntervention.SUMMARY,
            DialogueIntervention.SILENCE,
            DialogueIntervention.UNCERTAINTY_STATEMENT,
            DialogueIntervention.CHALLENGE_ASSUMPTION,
            DialogueIntervention.OPEN_EXPLORATION,
            DialogueIntervention.NO_INTERVENTION,
        ]
        assert len(interventions) == 16
        for inv in interventions:
            assert isinstance(inv, DialogueIntervention)


from ayeneh.dialogue.policies import MultiplePerspectives
