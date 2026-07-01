"""Comprehensive tests for the Cognitive Evaluation Framework."""

from __future__ import annotations

import pytest

from ayeneh.evaluation.annotations import AnnotationStore, HumanAnnotation
from ayeneh.evaluation.benchmarks.golden import (
    BLIND_SPOT_BENCHMARKS,
    CONVERSATION_BENCHMARKS,
    MEMORY_BENCHMARKS,
    PATTERN_BENCHMARKS,
    REFLECTION_BENCHMARKS,
    get_all_benchmarks,
    get_benchmarks,
)
from ayeneh.evaluation.core import EvalCase, EvalReport, EvalResult, QualityThreshold
from ayeneh.evaluation.evaluators import (
    BlindSpotEvaluator,
    ConversationEvaluator,
    MemoryEvaluator,
    PatternEvaluator,
    ReflectionEvaluator,
)
from ayeneh.evaluation.evaluators.judge import LLMJudge
from ayeneh.evaluation.reports import (
    generate_dashboard_data,
    generate_json_report,
    generate_text_report,
)
from ayeneh.evaluation.runner import EvalRunConfig, EvaluationRunner
from ayeneh.evaluation.scorers import (
    citation_correctness,
    consistency_score,
    contains_match,
    exact_match,
    f1_score,
    groundedness_score,
    hallucination_rate,
    precision_score,
    recall_score,
)


# ════════════════════════════════════════════════════════════════════════
# Scorer tests
# ════════════════════════════════════════════════════════════════════════

class TestScorers:
    def test_groundedness_high(self) -> None:
        score = groundedness_score(
            "CBT is therapy.", ["Cognitive behavioral therapy is a structured therapy."]
        )
        assert score > 0.5

    def test_groundedness_low(self) -> None:
        score = groundedness_score(
            "Quantum physics explains everything.", ["CBT is therapy."]
        )
        assert score < 0.5

    def test_hallucination_rate(self) -> None:
        rate = hallucination_rate(
            "CBT is therapy for anxiety.",
            ["CBT is therapy for anxiety and depression."],
        )
        assert rate < 0.5

    def test_precision(self) -> None:
        assert precision_score(["a", "b", "c"], ["a", "b", "d"]) == pytest.approx(2 / 3)

    def test_recall(self) -> None:
        assert recall_score(["a", "b"], ["a", "b", "c"]) == pytest.approx(2 / 3)

    def test_f1(self) -> None:
        score = f1_score(["a", "b"], ["a", "b", "c"])
        assert score > 0.5

    def test_f1_empty(self) -> None:
        assert f1_score([], []) == 1.0

    def test_consistency(self) -> None:
        score = consistency_score(["hello world", "hello there"])
        assert score > 0.0

    def test_citation_correctness(self) -> None:
        score = citation_correctness(
            [{"excerpt": "therapy helps"}, {"excerpt": "fake claim"}],
            ["therapy helps anxiety"],
        )
        assert score == pytest.approx(0.5)

    def test_exact_match(self) -> None:
        assert exact_match("hello", "hello") == 1.0
        assert exact_match("hello", "world") == 0.0

    def test_contains_match(self) -> None:
        assert contains_match("I like cats", ["cats", "dogs"]) == pytest.approx(0.5)
        assert contains_match("I like cats", ["cats"]) == 1.0


# ════════════════════════════════════════════════════════════════════════
# Evaluator tests
# ════════════════════════════════════════════════════════════════════════

class TestEvaluators:
    def test_conversation_evaluator_pass(self) -> None:
        case = EvalCase(
            case_id="c1", agent_type="conversation",
            input_data={"message": "hi"},
            expected_output={"keywords": ["hello"]},
            context={"source_texts": ["Hello to users. How can I help you today with your request."]},
        )
        actual = {"response_text": "Hello! How can I help you today with your request?"}
        result = ConversationEvaluator().evaluate(case, actual)
        assert result.passed is True
        assert "groundedness" in result.metrics

    def test_conversation_evaluator_fail(self) -> None:
        case = EvalCase(
            case_id="c2", agent_type="conversation",
            input_data={"message": "hi"},
            expected_output={"keywords": ["quantum"]},
            context={"source_texts": ["Say hello."]},
        )
        actual = {"response_text": "The economy is doing well."}
        result = ConversationEvaluator().evaluate(case, actual)
        assert result.passed is False

    def test_memory_evaluator(self) -> None:
        case = EvalCase(
            case_id="m1", agent_type="memory",
            input_data={"message": "I love cats"},
            expected_output={"expected_memories": [{"content": "loves cats"}]},
        )
        actual = {"memories": [{"content": "loves cats"}, {"content": "likes dogs"}]}
        result = MemoryEvaluator().evaluate(case, actual)
        assert result.metrics["precision"] > 0.0
        assert result.metrics["recall"] == 1.0

    def test_pattern_evaluator(self) -> None:
        case = EvalCase(
            case_id="p1", agent_type="pattern",
            input_data={"memories": ["avoid conflict"]},
            expected_output={"expected_patterns": [{"description": "conflict avoidance"}]},
        )
        actual = {"patterns": [{"description": "conflict avoidance"}]}
        result = PatternEvaluator().evaluate(case, actual)
        assert result.passed is True

    def test_reflection_evaluator(self) -> None:
        case = EvalCase(
            case_id="r1", agent_type="reflection",
            input_data={"memories": ["value honesty"]},
            expected_output={"keywords": ["honesty"]},
            context={"source_texts": ["User values honesty in relationships and values personal growth."]},
        )
        actual = {"narrative": "You value honesty in relationships and personal growth."}
        result = ReflectionEvaluator().evaluate(case, actual)
        assert result.passed is True

    def test_blind_spot_evaluator(self) -> None:
        case = EvalCase(
            case_id="b1", agent_type="blind_spot",
            input_data={"memories": ["I never fail", "I failed yesterday"]},
            expected_output={
                "expected_observations": [
                    {"content": "contradiction between claim and experience"}
                ]
            },
            context={"source_texts": ["There is a contradiction between the claim of never failing and the experience of failing yesterday."]},
        )
        actual = {
            "observations": [
                {"content": "contradiction between claim and experience"}
            ]
        }
        result = BlindSpotEvaluator().evaluate(case, actual)
        assert result.passed is True


# ════════════════════════════════════════════════════════════════════════
# Benchmark tests
# ════════════════════════════════════════════════════════════════════════

class TestBenchmarks:
    def test_all_benchmarks_exist(self) -> None:
        assert len(CONVERSATION_BENCHMARKS) >= 3
        assert len(MEMORY_BENCHMARKS) >= 3
        assert len(PATTERN_BENCHMARKS) >= 2
        assert len(REFLECTION_BENCHMARKS) >= 1
        assert len(BLIND_SPOT_BENCHMARKS) >= 2

    def test_get_benchmarks_by_type(self) -> None:
        conv = get_benchmarks("conversation")
        assert len(conv) >= 3
        for c in conv:
            assert c.agent_type == "conversation"

    def test_get_all_benchmarks(self) -> None:
        all_b = get_all_benchmarks()
        assert len(all_b) >= 10

    def test_benchmark_case_ids_unique(self) -> None:
        all_b = get_all_benchmarks()
        ids = [c.case_id for c in all_b]
        assert len(ids) == len(set(ids))


# ════════════════════════════════════════════════════════════════════════
# Runner tests
# ════════════════════════════════════════════════════════════════════════

class TestEvaluationRunner:
    def test_run_conversation(self) -> None:
        def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {"response_text": "Hello! Ayeneh is your companion."}

        runner = EvaluationRunner()
        report = runner.run(agent_fn, EvalRunConfig(agent_type="conversation"))
        assert report.total_cases >= 3
        assert report.passed_cases + report.failed_cases == report.total_cases

    def test_run_memory(self) -> None:
        def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            msg = input_data.get("message", "")
            return {"memories": [{"content": msg[:50], "type": "semantic"}]}

        runner = EvaluationRunner()
        report = runner.run(agent_fn, EvalRunConfig(agent_type="memory"))
        assert report.total_cases >= 3

    def test_run_custom_cases(self) -> None:
        custom = [
            EvalCase(
                case_id="custom-1", agent_type="conversation",
                input_data={"message": "test"},
                expected_output={"keywords": ["test"]},
                context={"source_texts": ["test response"]},
            )
        ]

        def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {"response_text": "This is a test response."}

        runner = EvaluationRunner()
        report = runner.run(agent_fn, EvalRunConfig(custom_cases=custom))
        assert report.total_cases == 1

    def test_regression_detection(self) -> None:
        def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {"response_text": "Hello!"}

        runner = EvaluationRunner()
        report = runner.run(agent_fn, EvalRunConfig(agent_type="conversation"))

        bad_baseline = {k: 1.0 for k in report.metrics_summary}
        _, details = runner._check_regression(
            report.metrics_summary, bad_baseline, tolerance=0.01
        )
        assert details

    def test_threshold_checking(self) -> None:
        report = EvalReport(
            agent_type="conversation",
            total_cases=10, passed_cases=8, failed_cases=2,
            metrics_summary={"groundedness": 0.85, "hallucination_rate": 0.1},
            results=[],
        )
        runner = EvaluationRunner()
        violations = runner.check_thresholds(report, [
            QualityThreshold(metric_name="groundedness", min_value=0.8),
            QualityThreshold(metric_name="hallucination_rate", max_value=0.2),
        ])
        assert len(violations) == 0

        violations_fail = runner.check_thresholds(report, [
            QualityThreshold(metric_name="groundedness", min_value=0.9),
        ])
        assert len(violations_fail) == 1


# ════════════════════════════════════════════════════════════════════════
# Judge tests
# ════════════════════════════════════════════════════════════════════════

class TestLLMJudge:
    def test_heuristic_judge(self) -> None:
        judge = LLMJudge(llm_gateway=None)
        score, reasoning = judge.judge(
            input_data={"msg": "hi"},
            expected={"response": "hello there"},
            actual={"response": "hello there friend"},
        )
        assert 0.0 <= score <= 1.0
        assert reasoning

    def test_heuristic_judge_missing_key(self) -> None:
        judge = LLMJudge(llm_gateway=None)
        score, _ = judge.judge(
            input_data={"msg": "hi"},
            expected={"response": "hello", "tone": "friendly"},
            actual={"response": "hello"},
        )
        assert score < 1.0


# ════════════════════════════════════════════════════════════════════════
# Annotation tests
# ════════════════════════════════════════════════════════════════════════

class TestAnnotations:
    def test_add_and_retrieve(self) -> None:
        store = AnnotationStore()
        ann = HumanAnnotation(
            annotation_id="a1", case_id="c1", annotator_id="u1",
            rating=0.8, label="good",
        )
        store.add_annotation(ann)
        assert len(store.get_annotations("c1")) == 1

    def test_inter_annotator_agreement(self) -> None:
        store = AnnotationStore()
        store.add_annotation(HumanAnnotation(
            annotation_id="a1", case_id="c1", annotator_id="u1", rating=0.9, label="good"))
        store.add_annotation(HumanAnnotation(
            annotation_id="a2", case_id="c1", annotator_id="u2", rating=0.85, label="good"))
        agreement = store.get_inter_annotator_agreement("c1")
        assert agreement > 0.9

    def test_summary(self) -> None:
        store = AnnotationStore()
        store.add_annotation(HumanAnnotation(
            annotation_id="a1", case_id="c1", annotator_id="u1", rating=0.7, label="ok"))
        store.add_annotation(HumanAnnotation(
            annotation_id="a2", case_id="c2", annotator_id="u1", rating=0.9, label="good"))
        summary = store.get_annotation_summary()
        assert summary["total_annotations"] == 2
        assert summary["cases_annotated"] == 2


# ════════════════════════════════════════════════════════════════════════
# Report generation tests
# ════════════════════════════════════════════════════════════════════════

class TestReportGeneration:
    def test_json_report(self) -> None:
        report = EvalReport(
            agent_type="conversation",
            total_cases=5, passed_cases=4, failed_cases=1,
            metrics_summary={"groundedness": 0.8},
            results=[],
        )
        data = generate_json_report(report)
        assert data["agent_type"] == "conversation"
        assert data["pass_rate"] == pytest.approx(0.8)

    def test_text_report(self) -> None:
        report = EvalReport(
            agent_type="memory",
            total_cases=3, passed_cases=2, failed_cases=1,
            metrics_summary={"precision": 0.7},
            results=[EvalResult(
                case_id="m1", agent_type="memory",
                metrics={"precision": 0.8}, passed=True, actual_output={},
            )],
        )
        text = generate_text_report(report)
        assert "MEMORY" in text
        assert "PASS" in text

    def test_dashboard_data(self) -> None:
        report = EvalReport(
            agent_type="pattern",
            total_cases=10, passed_cases=8, failed_cases=2,
            metrics_summary={"f1": 0.75},
            results=[EvalResult(
                case_id="p1", agent_type="pattern",
                metrics={"f1": 0.8}, passed=True, actual_output={}, duration_ms=10.0,
            )],
        )
        data = generate_dashboard_data(report)
        assert data["pass_rate"] == pytest.approx(0.8)
        assert data["avg_duration_ms"] == pytest.approx(10.0)
