"""Comprehensive tests for the Epistemic Analyzer."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from ayeneh.application.services.epistemic_analysis import (
    AnalysisExplanation,
    ClaimType,
    EpistemicAnalysisEngine,
    EpistemicAnalyzer,
    EpistemicFramework,
    EpistemicFrameworkResult,
    EpistemicIntent,
    EpistemicIntentResult,
    EpistemicQueryAnalysis,
    EpistemicSignal,
    EpistemicSignalResult,
    RuleBasedEpistemicAnalyzer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> EpistemicAnalyzer:
    return EpistemicAnalyzer()


@pytest.fixture
def rule_engine() -> RuleBasedEpistemicAnalyzer:
    return RuleBasedEpistemicAnalyzer()


# ---------------------------------------------------------------------------
# Intent recognition tests
# ---------------------------------------------------------------------------


class TestIntentRecognition:
    def test_question_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the meaning of life?")
        assert result.primary_intent == EpistemicIntent.QUESTION
        assert result.intent_confidence >= 0.8

    def test_reflection_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I notice I keep avoiding difficult conversations")
        assert result.primary_intent == EpistemicIntent.REFLECTION
        assert result.intent_confidence >= 0.7

    def test_decision_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Should I change careers?")
        assert result.primary_intent == EpistemicIntent.DECISION
        assert result.intent_confidence >= 0.7

    def test_self_observation_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("My pattern is to always procrastinate")
        assert result.primary_intent == EpistemicIntent.SELF_OBSERVATION
        assert result.intent_confidence >= 0.7

    def test_learning_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Explain how cognitive behavioral therapy works")
        assert result.primary_intent == EpistemicIntent.LEARNING
        assert result.intent_confidence >= 0.6

    def test_comparison_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Compare Stoicism and Buddhism")
        assert result.primary_intent == EpistemicIntent.COMPARISON
        assert result.intent_confidence >= 0.7

    def test_meaning_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I'm seeking the meaning and significance of this experience")
        assert result.primary_intent == EpistemicIntent.MEANING
        assert result.intent_confidence >= 0.6

    def test_practice_intent(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I want to practice mindfulness meditation techniques")
        assert result.primary_intent == EpistemicIntent.PRACTICE
        assert result.intent_confidence >= 0.6


# ---------------------------------------------------------------------------
# Signal extraction tests
# ---------------------------------------------------------------------------


class TestSignalExtraction:
    def test_scientific_signal(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does neuroscience research say about memory?")
        assert "scientific" in result.analysis_explanation.primary_signals

    def test_clinical_signal(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("How is anxiety treated in clinical settings?")
        assert "clinical" in result.analysis_explanation.primary_signals

    def test_philosophical_signal(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the nature of consciousness?")
        assert "philosophical" in result.analysis_explanation.primary_signals

    def test_contemplative_signal(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is fana in Sufi mysticism?")
        assert "contemplative" in result.analysis_explanation.primary_signals

    def test_multiple_signals(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze(
            "How does meditation affect brain function and spiritual experience?"
        )
        assert len(result.analysis_explanation.primary_signals) >= 2


# ---------------------------------------------------------------------------
# Framework inference tests
# ---------------------------------------------------------------------------


class TestFrameworkInference:
    def test_rationalist_framework(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the logical argument for free will?")
        frameworks = [f.framework for f in result.candidate_frameworks]
        assert EpistemicFramework.RATIONALIST in frameworks

    def test_empiricist_framework(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does the evidence show about habit formation?")
        frameworks = [f.framework for f in result.candidate_frameworks]
        assert EpistemicFramework.EMPIRICIST in frameworks

    def test_phenomenological_framework(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the lived experience of grief?")
        frameworks = [f.framework for f in result.candidate_frameworks]
        assert EpistemicFramework.PHENOMENOLOGICAL in frameworks

    def test_multiple_frameworks(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze(
            "How do reason and experience combine in understanding truth?"
        )
        assert len(result.candidate_frameworks) >= 2
        assert result.requires_multiple_frameworks

    def test_framework_confidence(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the scientific method?")
        for fw in result.candidate_frameworks:
            assert 0.0 <= fw.confidence <= 1.0


# ---------------------------------------------------------------------------
# Evidence expectation tests
# ---------------------------------------------------------------------------


class TestEvidenceExpectation:
    def test_empirical_evidence(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Neuroscience research and empirical data on sleep and cognition")
        assert result.expected_evidence_level == "empirical"

    def test_phenomenological_evidence(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the felt sense of anxiety?")
        assert result.expected_evidence_level == "phenomenological"

    def test_contemplative_evidence(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does meditation reveal about the mind?")
        assert result.expected_evidence_level == "contemplative"

    def test_preferred_sources(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does research say about therapy outcomes?")
        assert len(result.preferred_sources) > 0

    def test_discouraged_sources(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does research say about therapy outcomes?")
        assert len(result.discouraged_sources) > 0


# ---------------------------------------------------------------------------
# Claim type tests
# ---------------------------------------------------------------------------


class TestClaimType:
    def test_descriptive_claim(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is cognitive behavioral therapy?")
        assert result.claim_type == ClaimType.DESCRIPTIVE

    def test_normative_claim(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Should we always tell the truth?")
        assert result.claim_type == ClaimType.NORMATIVE

    def test_interpretive_claim(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does this dream mean?")
        assert result.claim_type == ClaimType.INTERPRETIVE


# ---------------------------------------------------------------------------
# Reasoning style tests
# ---------------------------------------------------------------------------


class TestReasoningStyle:
    def test_deductive_style(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("Why does anxiety cause physical symptoms?")
        assert result.reasoning_style == "deductive"

    def test_inductive_style(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What pattern do you notice in my behavior?")
        assert result.reasoning_style == "inductive"

    def test_abductive_style(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("This might suggest a deeper issue")
        assert result.reasoning_style == "abductive"

    def test_contemplative_style(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I feel a deep sense of inner peace")
        assert result.reasoning_style == "contemplative"


# ---------------------------------------------------------------------------
# Requirements tests
# ---------------------------------------------------------------------------


class TestRequirements:
    def test_uncertainty_statement_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I'm uncertain about my future")
        assert result.requires_uncertainty_statement

    def test_citations_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does the research show?")
        assert result.requires_citations

    def test_reflective_dialogue_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("I notice I keep avoiding things")
        assert result.requires_reflective_dialogue

    def test_goal_context_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("How am I progressing on my goals?")
        assert result.requires_goal_context

    def test_memory_context_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What did I say before about this?")
        assert result.requires_memory_context

    def test_knowledge_context_required(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What does the book say about this?")
        assert result.requires_knowledge_context

    def test_cross_framework_reasoning(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze(
            "How do science and spirituality integrate their perspectives?"
        )
        assert result.requires_cross_framework_reasoning


# ---------------------------------------------------------------------------
# Domain inference tests
# ---------------------------------------------------------------------------


class TestDomainInference:
    def test_philosophy_domain(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the nature of reality?")
        assert "philosophy" in result.primary_domains

    def test_psychology_domain(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("How does anxiety affect daily functioning?")
        assert "psychology" in result.primary_domains

    def test_spirituality_domain(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is meditation and how does it work?")
        assert "spirituality" in result.primary_domains

    def test_multiple_domains(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze(
            "Neuroscience research on meditation and contemplative spiritual practice"
        )
        total_domains = len(result.primary_domains) + len(result.secondary_domains)
        assert total_domains >= 2


# ---------------------------------------------------------------------------
# Rule-based engine tests
# ---------------------------------------------------------------------------


class TestRuleBasedEngine:
    def test_engine_implements_protocol(self, rule_engine: RuleBasedEpistemicAnalyzer) -> None:
        assert isinstance(rule_engine, EpistemicAnalysisEngine)

    def test_engine_analyze_returns_analysis(self, rule_engine: RuleBasedEpistemicAnalyzer) -> None:
        result = rule_engine.analyze("test query")
        assert isinstance(result, EpistemicQueryAnalysis)

    def test_engine_stages_completed(self, rule_engine: RuleBasedEpistemicAnalyzer) -> None:
        result = rule_engine.analyze("test query")
        assert len(result.analysis_explanation.stages_completed) >= 8

    def test_engine_confidence_range(self, rule_engine: RuleBasedEpistemicAnalyzer) -> None:
        result = rule_engine.analyze("test query")
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Engine swapping tests
# ---------------------------------------------------------------------------


class TestEngineSwapping:
    def test_analyzer_accepts_custom_engine(self) -> None:
        class CustomEngine:
            def analyze(self, query: str, context: dict | None = None) -> EpistemicQueryAnalysis:
                return EpistemicQueryAnalysis(
                    query=query,
                    primary_intent=EpistemicIntent.LEARNING,
                    confidence=0.9,
                )

        analyzer = EpistemicAnalyzer(engine=CustomEngine())
        result = analyzer.analyze("test")
        assert result.primary_intent == EpistemicIntent.LEARNING
        assert result.confidence == 0.9

    def test_analyzer_set_engine(self) -> None:
        analyzer = EpistemicAnalyzer()

        class NewEngine:
            def analyze(self, query: str, context: dict | None = None) -> EpistemicQueryAnalysis:
                return EpistemicQueryAnalysis(query=query, confidence=0.95)

        analyzer.set_engine(NewEngine())
        result = analyzer.analyze("test")
        assert result.confidence == 0.95


# ---------------------------------------------------------------------------
# Analysis explanation tests
# ---------------------------------------------------------------------------


class TestAnalysisExplanation:
    def test_explanation_has_stages(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is truth?")
        assert len(result.analysis_explanation.stages_completed) >= 8

    def test_explanation_has_reasoning(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is truth?")
        assert len(result.analysis_explanation.inference_reasoning) > 0

    def test_explanation_has_signals(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is the scientific evidence for mindfulness?")
        assert len(result.analysis_explanation.primary_signals) > 0


# ---------------------------------------------------------------------------
# Metadata propagation tests
# ---------------------------------------------------------------------------


class TestMetadataPropagation:
    def test_analysis_version(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("test")
        assert result.analysis_version == "1.0.0"

    def test_query_preserved(self, analyzer: EpistemicAnalyzer) -> None:
        query = "What is the meaning of life?"
        result = analyzer.analyze(query)
        assert result.query == query

    def test_confidence_range(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("test")
        assert 0.0 <= result.confidence <= 1.0

    def test_uncertainty_tolerance_range(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("test")
        assert 0.0 <= result.uncertainty_tolerance <= 1.0


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_analysis_completes_quickly(self, analyzer: EpistemicAnalyzer) -> None:
        start = time.monotonic()
        for _ in range(100):
            analyzer.analyze("What is the nature of reality and consciousness?")
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1000  # 100 analyses in under 1 second

    def test_concurrent_analysis(self, analyzer: EpistemicAnalyzer) -> None:
        queries = [
            "What is truth?",
            "How does anxiety work?",
            "What is meditation?",
            "Why do we suffer?",
            "What is the good life?",
        ]

        def analyze_query(q: str) -> EpistemicQueryAnalysis:
            return analyzer.analyze(q)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(analyze_query, q) for q in queries]
            results = [f.result() for f in futures]

        assert len(results) == 5
        assert all(isinstance(r, EpistemicQueryAnalysis) for r in results)


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_same_input_same_output(self, analyzer: EpistemicAnalyzer) -> None:
        query = "What is the meaning of life?"
        result1 = analyzer.analyze(query)
        result2 = analyzer.analyze(query)

        assert result1.primary_intent == result2.primary_intent
        assert result1.primary_domains == result2.primary_domains
        assert result1.reasoning_style == result2.reasoning_style
        assert abs(result1.confidence - result2.confidence) < 1e-10


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_default_analyzer_works(self) -> None:
        analyzer = EpistemicAnalyzer()
        result = analyzer.analyze("test query")
        assert isinstance(result, EpistemicQueryAnalysis)

    def test_rule_engine_is_default(self) -> None:
        analyzer = EpistemicAnalyzer()
        assert isinstance(analyzer._engine, RuleBasedEpistemicAnalyzer)

    def test_context_parameter_optional(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("test")
        assert isinstance(result, EpistemicQueryAnalysis)

    def test_context_parameter_used(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("test", context={"user_id": "123"})
        assert isinstance(result, EpistemicQueryAnalysis)


# ---------------------------------------------------------------------------
# Observability tests
# ---------------------------------------------------------------------------


class TestObservability:
    def test_analysis_metrics_recorded(self) -> None:
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_epistemic_analysis(
            duration_ms=5.2,
            confidence=0.75,
            frameworks=["rationalist", "empiricist"],
            intent="question",
            requires_uncertainty=True,
            cross_framework=False,
        )

        assert metrics.epistemic_analysis_count == 1
        assert metrics.epistemic_analysis_duration_ms == 5.2
        assert metrics.epistemic_framework_distribution["rationalist"] == 1
        assert metrics.epistemic_intent_distribution["question"] == 1
        assert metrics.epistemic_uncertainty_requests == 1
        assert metrics.epistemic_cross_framework_requests == 0

    def test_analysis_metrics_export(self) -> None:
        from ayeneh.infrastructure.observability import PrometheusMetrics

        metrics = PrometheusMetrics()
        metrics.record_epistemic_analysis(
            duration_ms=5.0,
            confidence=0.8,
            frameworks=["philosophical"],
            intent="reflection",
            requires_uncertainty=False,
            cross_framework=True,
        )

        text = metrics.export_prometheus_text()
        assert "ayeneh_epistemic_analyses_total" in text
        assert "ayeneh_epistemic_analysis_duration_ms_total" in text
        assert "ayeneh_epistemic_framework_distribution" in text
        assert "ayeneh_epistemic_intent_distribution" in text
        assert "ayeneh_epistemic_uncertainty_requests" in text
        assert "ayeneh_epistemic_cross_framework_requests" in text


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_query(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("")
        assert isinstance(result, EpistemicQueryAnalysis)
        assert result.confidence >= 0.0

    def test_very_long_query(self, analyzer: EpistemicAnalyzer) -> None:
        query = "What is " + "the meaning of " * 50 + "life?"
        result = analyzer.analyze(query)
        assert isinstance(result, EpistemicQueryAnalysis)

    def test_special_characters(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is truth? (philosophical inquiry)")
        assert isinstance(result, EpistemicQueryAnalysis)

    def test_mixed_language_query(self, analyzer: EpistemicAnalyzer) -> None:
        result = analyzer.analyze("What is fana in Sufi tradition?")
        assert isinstance(result, EpistemicQueryAnalysis)
