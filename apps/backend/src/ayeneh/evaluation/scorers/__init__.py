"""Scoring functions for evaluation metrics."""

from __future__ import annotations

import re
from typing import Any


def groundedness_score(
    response: str, source_texts: list[str], threshold: float = 0.5
) -> float:
    """Measure what fraction of response sentences are supported by sources."""
    if not response or not source_texts:
        return 0.0

    sentences = _split_sentences(response)
    if not sentences:
        return 0.0

    source_combined = " ".join(source_texts).lower()
    supported = sum(
        1 for s in sentences
        if _sentence_supported(s, source_combined)
    )
    return supported / len(sentences)


def hallucination_rate(
    response: str, source_texts: list[str]
) -> float:
    """Fraction of response not grounded in any source. Lower is better."""
    return 1.0 - groundedness_score(response, source_texts)


def precision_score(predicted: list[str], expected: list[str]) -> float:
    """Fraction of predicted items that are in expected."""
    if not predicted:
        return 1.0
    pred_set = set(predicted)
    exp_set = set(expected)
    return len(pred_set & exp_set) / len(pred_set) if pred_set else 0.0


def recall_score(predicted: list[str], expected: list[str]) -> float:
    """Fraction of expected items that appear in predicted."""
    if not expected:
        return 1.0
    pred_set = set(predicted)
    exp_set = set(expected)
    return len(pred_set & exp_set) / len(exp_set) if exp_set else 0.0


def f1_score(predicted: list[str], expected: list[str]) -> float:
    p = precision_score(predicted, expected)
    r = recall_score(predicted, expected)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def consistency_score(responses: list[str]) -> float:
    """Measure semantic consistency across multiple responses to similar inputs."""
    if len(responses) < 2:
        return 1.0

    word_sets = [set(r.lower().split()) for r in responses]
    all_words = set()
    for ws in word_sets:
        all_words |= ws

    if not all_words:
        return 0.0

    consistency_scores = []
    for ws in word_sets:
        overlap = len(ws & all_words) / len(all_words) if all_words else 0
        consistency_scores.append(overlap)

    return sum(consistency_scores) / len(consistency_scores)


def citation_correctness(
    citations: list[dict[str, Any]], source_texts: list[str]
) -> float:
    """Fraction of citations that reference content actually present in sources."""
    if not citations:
        return 1.0
    if not source_texts:
        return 0.0

    source_combined = " ".join(source_texts).lower()
    correct = 0
    for citation in citations:
        excerpt = citation.get("excerpt", "").lower()
        if excerpt and excerpt in source_combined:
            correct += 1
    return correct / len(citations)


def exact_match(predicted: str, expected: str) -> float:
    return 1.0 if predicted.strip().lower() == expected.strip().lower() else 0.0


def contains_match(predicted: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    pred_lower = predicted.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in pred_lower)
    return found / len(expected_keywords)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in parts if s.strip()]


def _sentence_supported(sentence: str, source_text: str) -> bool:
    words = set(sentence.lower().split())
    if len(words) < 2:
        return True
    source_words = set(source_text.split())
    overlap = len(words & source_words)
    return overlap / len(words) >= 0.4
