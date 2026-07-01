"""Agent-specific evaluators."""

from __future__ import annotations

from typing import Any

from ayeneh.evaluation.core import EvalCase, EvalResult
from ayeneh.evaluation.scorers import (
    citation_correctness,
    consistency_score,
    contains_match,
    f1_score,
    groundedness_score,
    hallucination_rate,
    precision_score,
    recall_score,
)


class ConversationEvaluator:
    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult:
        response = actual.get("response_text", "")
        sources = case.context.get("source_texts", [])
        expected = case.expected_output

        metrics = {
            "groundedness": groundedness_score(response, sources),
            "hallucination_rate": hallucination_rate(response, sources),
            "contains_keywords": contains_match(response, expected.get("keywords", [])),
            "citation_correctness": citation_correctness(
                actual.get("citations", []), sources
            ),
        }

        passed = metrics["hallucination_rate"] < 0.3 and metrics["groundedness"] > 0.5
        return EvalResult(
            case_id=case.case_id,
            agent_type="conversation",
            metrics=metrics,
            passed=passed,
            actual_output=actual,
        )


class MemoryEvaluator:
    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult:
        extracted = actual.get("memories", [])
        expected = case.expected_output.get("expected_memories", [])
        expected_contents = [m.get("content", "") for m in expected]
        extracted_contents = [m.get("content", "") for m in extracted]

        metrics = {
            "precision": precision_score(extracted_contents, expected_contents),
            "recall": recall_score(extracted_contents, expected_contents),
            "f1": f1_score(extracted_contents, expected_contents),
        }
        metrics["f1"] = 2 * metrics["precision"] * metrics["recall"] / (
            metrics["precision"] + metrics["recall"]
        ) if (metrics["precision"] + metrics["recall"]) > 0 else 0.0

        passed = metrics["f1"] >= 0.5
        return EvalResult(
            case_id=case.case_id,
            agent_type="memory",
            metrics=metrics,
            passed=passed,
            actual_output=actual,
        )


class PatternEvaluator:
    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult:
        detected = actual.get("patterns", [])
        expected = case.expected_output.get("expected_patterns", [])
        detected_descs = [p.get("description", "") for p in detected]
        expected_descs = [p.get("description", "") for p in expected]

        metrics = {
            "precision": precision_score(detected_descs, expected_descs),
            "recall": recall_score(detected_descs, expected_descs),
            "f1": f1_score(detected_descs, expected_descs),
            "consistency": consistency_score(detected_descs) if len(detected_descs) > 1 else 1.0,
        }

        passed = metrics["f1"] >= 0.4
        return EvalResult(
            case_id=case.case_id,
            agent_type="pattern",
            metrics=metrics,
            passed=passed,
            actual_output=actual,
        )


class ReflectionEvaluator:
    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult:
        narrative = actual.get("narrative", "")
        sources = case.context.get("source_texts", [])

        metrics = {
            "groundedness": groundedness_score(narrative, sources),
            "hallucination_rate": hallucination_rate(narrative, sources),
            "citation_correctness": citation_correctness(
                actual.get("citations", []), sources
            ),
            "contains_keywords": contains_match(
                narrative, case.expected_output.get("keywords", [])
            ),
        }

        passed = metrics["groundedness"] > 0.4 and metrics["hallucination_rate"] < 0.4
        return EvalResult(
            case_id=case.case_id,
            agent_type="reflection",
            metrics=metrics,
            passed=passed,
            actual_output=actual,
        )


class BlindSpotEvaluator:
    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult:
        observations = actual.get("observations", [])
        expected = case.expected_output.get("expected_observations", [])
        obs_contents = [o.get("content", "") for o in observations]
        exp_contents = [o.get("content", "") for o in expected]

        metrics = {
            "precision": precision_score(obs_contents, exp_contents),
            "recall": recall_score(obs_contents, exp_contents),
            "f1": f1_score(obs_contents, exp_contents),
            "groundedness": groundedness_score(
                " ".join(obs_contents), case.context.get("source_texts", [])
            ),
        }

        passed = metrics["f1"] >= 0.3 and metrics["groundedness"] > 0.3
        return EvalResult(
            case_id=case.case_id,
            agent_type="blind_spot",
            metrics=metrics,
            passed=passed,
            actual_output=actual,
        )
