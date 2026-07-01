"""Hypothesis generation — produces competing hypotheses with supporting/opposing evidence."""

from __future__ import annotations

import structlog

from ayeneh.reasoning.types import Evidence, Hypothesis

logger = structlog.get_logger(__name__)


class HypothesisGenerator:
    """Generates multiple competing hypotheses from evidence."""

    def generate(self, evidence: list[Evidence], objective: str) -> list[Hypothesis]:
        if not evidence:
            return [Hypothesis(
                claim=f"Limited evidence available for: {objective}",
                confidence=0.1,
                missing_evidence=["Any supporting evidence"],
            )]

        by_source: dict[str, list[Evidence]] = {}
        for e in evidence:
            by_source.setdefault(e.source_type, []).append(e)

        hypotheses: list[Hypothesis] = []

        hypotheses.append(self._primary_hypothesis(evidence, objective))
        hypotheses.append(self._alternative_hypothesis(evidence, objective))

        if len(evidence) > 3:
            hypotheses.append(self._contrarian_hypothesis(evidence, objective))

        for h in hypotheses:
            self._assign_evidence(h, evidence)

        return hypotheses

    def _primary_hypothesis(self, evidence: list[Evidence], objective: str) -> Hypothesis:
        high_conf = [e for e in evidence if e.confidence >= 0.6]
        if high_conf:
            claim = f"Based on {len(high_conf)} high-confidence evidence items, the most supported view is that {objective.lower()}"
        else:
            claim = f"The available evidence provides limited support for addressing: {objective}"
        return Hypothesis(claim=claim, confidence=0.6 if high_conf else 0.3)

    def _alternative_hypothesis(self, evidence: list[Evidence], objective: str) -> Hypothesis:
        low_conf = [e for e in evidence if e.confidence < 0.5]
        if low_conf:
            claim = f"A weaker interpretation based on {len(low_conf)} lower-confidence signals suggests {objective.lower()} may need further investigation"
        else:
            claim = f"An alternative perspective to consider: {objective} might be viewed differently with additional context"
        return Hypothesis(claim=claim, confidence=0.3)

    def _contrarian_hypothesis(self, evidence: list[Evidence], objective: str) -> Hypothesis:
        sources = set(e.source_type for e in evidence)
        claim = f"Consider the possibility that {objective} is more nuanced than the {len(sources)} available evidence sources suggest"
        return Hypothesis(claim=claim, confidence=0.2)

    def _assign_evidence(self, hypothesis: Hypothesis, all_evidence: list[Evidence]) -> None:
        for e in all_evidence:
            if e.confidence >= 0.5:
                hypothesis.supporting_evidence.append(e.id)
            else:
                hypothesis.opposing_evidence.append(e.id)

        if len(hypothesis.supporting_evidence) == 0:
            hypothesis.missing_evidence.append("Higher-confidence supporting evidence")
        if len(hypothesis.opposing_evidence) == 0:
            hypothesis.missing_evidence.append("Opposing or contradictory evidence")
