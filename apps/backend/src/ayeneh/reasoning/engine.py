"""ReasoningEngine — multi-stage deliberative reasoning before LLM response generation.

This subsystem performs reasoning only. It does NOT generate assistant text.
It produces a ReasoningSummary consumed by PromptComposer.
"""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.reasoning.conflicts import ConflictDetector
from ayeneh.reasoning.evidence import EvidenceCollector
from ayeneh.reasoning.hypotheses import HypothesisGenerator
from ayeneh.reasoning.types import (
    Conflict,
    Evidence,
    Hypothesis,
    ReasoningSession,
    ReasoningStage,
    ReasoningSummary,
    ReasoningStep,
)
from ayeneh.reasoning.uncertainty import UncertaintyEstimator

logger = structlog.get_logger(__name__)


class ReasoningEngine:
    """Multi-stage deliberative reasoning engine.

    Executes: Understand → Objective → Evidence → Missing → Hypotheses →
    Evaluate → Conflicts → Confidence → Summary

    No stage generates user-facing text.
    """

    def __init__(
        self,
        goal_service: Any = None,
        goal_retrieval: Any = None,
        retrieval_service: Any = None,
    ) -> None:
        self._evidence_collector = EvidenceCollector(goal_service, goal_retrieval, retrieval_service)
        self._conflict_detector = ConflictDetector()
        self._hypothesis_generator = HypothesisGenerator()
        self._uncertainty_estimator = UncertaintyEstimator()

    async def reason(self, user_id: str, query: str, context: dict[str, Any] | None = None) -> ReasoningSession:
        session = ReasoningSession(user_id=user_id, query=query)
        ctx = context or {}

        session.add_step(ReasoningStage.UNDERSTAND, "Parsing user query and context")
        objective = await self._understand_request(query, ctx)
        session.objective = objective

        session.add_step(ReasoningStage.OBJECTIVE, f"Objective determined: {objective[:80]}")

        session.add_step(ReasoningStage.EVIDENCE, "Collecting evidence from all sources")
        evidence = await self._collect_evidence(session, user_id, query)
        session.evidence = evidence

        session.add_step(ReasoningStage.MISSING, "Checking for information gaps")
        self._detect_missing(evidence, session)

        session.add_step(ReasoningStage.HYPOTHESIS, "Generating competing hypotheses")
        hypotheses = self._generate_hypotheses(evidence, objective)
        session.hypotheses = hypotheses

        session.add_step(ReasoningStage.EVALUATE, f"Evaluating {len(hypotheses)} hypotheses")
        self._evaluate_hypotheses(hypotheses, evidence)

        session.add_step(ReasoningStage.CONFLICTS, "Detecting conflicts")
        conflicts = self._detect_conflicts(evidence)
        session.conflicts = conflicts

        session.add_step(ReasoningStage.CONFIDENCE, "Estimating uncertainty")
        confidence, uncertainty_reasons = self._estimate_confidence(evidence, conflicts, hypotheses)
        session.confidence_evolution.append(confidence)
        session.uncertainties = uncertainty_reasons

        session.add_step(ReasoningStage.SUMMARY, "Building reasoning summary")
        session.summary = self._build_summary(session, evidence, hypotheses, conflicts, confidence)

        import datetime as dt
        session.end_time = dt.datetime.now(dt.UTC)

        logger.info("reasoning_complete", session_id=session.id, confidence=confidence,
                     evidence=len(evidence), hypotheses=len(hypotheses), conflicts=len(conflicts))
        return session

    async def _understand_request(self, query: str, context: dict[str, Any]) -> str:
        if context.get("objective"):
            return context["objective"]
        return f"Address the user's inquiry: {query}"

    async def _collect_evidence(self, session: ReasoningSession, user_id: str, query: str) -> list[Evidence]:
        return await self._evidence_collector.collect_all(user_id, query)

    def _detect_missing(self, evidence: list[Evidence], session: ReasoningSession) -> None:
        source_types = set(e.source_type for e in evidence)
        required = {"goal", "memory", "knowledge"}
        missing = required - source_types
        for m in missing:
            session.uncertainties.append(f"No {m} evidence available")

    def _generate_hypotheses(self, evidence: list[Evidence], objective: str) -> list[Hypothesis]:
        return self._hypothesis_generator.generate(evidence, objective)

    def _evaluate_hypotheses(self, hypotheses: list[Hypothesis], evidence: list[Evidence]) -> None:
        evidence_map = {e.id: e for e in evidence}
        for h in hypotheses:
            support_conf = [evidence_map[eid].confidence for eid in h.supporting_evidence if eid in evidence_map]
            oppose_conf = [evidence_map[eid].confidence for eid in h.opposing_evidence if eid in evidence_map]
            if support_conf:
                h.confidence = sum(support_conf) / len(support_conf) * 0.7
            if oppose_conf:
                h.confidence *= (1.0 - sum(oppose_conf) / len(oppose_conf) * 0.3)
            h.confidence = max(0.05, min(0.95, h.confidence))

    def _detect_conflicts(self, evidence: list[Evidence]) -> list[Conflict]:
        return self._conflict_detector.detect(evidence)

    def _estimate_confidence(self, evidence: list[Evidence], conflicts: list[Conflict], hypotheses: list[Hypothesis]) -> tuple[float, list[str]]:
        return self._uncertainty_estimator.estimate(
            evidence, conflicts, len(hypotheses),
        )

    def _build_summary(
        self, session: ReasoningSession, evidence: list[Evidence],
        hypotheses: list[Hypothesis], conflicts: list[Conflict], confidence: float,
    ) -> ReasoningSummary:
        selected = []
        ignored = []
        for e in evidence:
            item = {"id": e.id, "source": e.source_type, "content": e.content[:200], "confidence": e.confidence}
            if e.confidence >= 0.4:
                selected.append(item)
            else:
                ignored.append(item)

        alt_hypotheses = [{"claim": h.claim, "confidence": h.confidence} for h in hypotheses[1:]]
        conflict_list = [{"type": c.conflict_type, "description": c.description[:200]} for c in conflicts]
        reasoning_path = [s.description for s in session.reasoning_steps]
        questions = []
        for u in session.uncertainties:
            questions.append(f"What is the {u.lower()}?")

        return ReasoningSummary(
            objective=session.objective,
            reasoning_path=reasoning_path,
            selected_evidence=selected,
            ignored_evidence=ignored,
            alternative_hypotheses=alt_hypotheses,
            conflicts=conflict_list,
            confidence=confidence,
            limitations=session.uncertainties.copy(),
            questions_for_clarification=questions,
            total_evidence_evaluated=len(evidence),
            alternatives_considered=len(hypotheses) - 1,
            conflicts_detected=len(conflicts),
            uncertainty_reasons=session.uncertainties.copy(),
        )

    def get_metrics(self) -> dict[str, Any]:
        return {
            "evidence_collector": "active",
            "conflict_detector": "active",
            "hypothesis_generator": "active",
            "uncertainty_estimator": "active",
        }
