"""DialogueIntentionEngine — single owner of all dialogue decisions.

This engine decides WHAT KIND OF INTERVENTION should happen
before any retrieval, reasoning, or response generation.

Ayeneh exists to improve the user's quality of observation
rather than to maximize answers.
"""

from __future__ import annotations

import re
import time
from typing import Any

import structlog

from ayeneh.dialogue.policies import (
    DialoguePolicy,
    get_policies_for_profile,
)
from ayeneh.dialogue.types import (
    DialogueAnalysis,
    DialogueDecision,
    DialogueIntervention,
    DialogueMetadata,
    DialogueNeed,
    DialogueNeedResult,
    DialogueReasoning,
    DialogueSignal,
    DialogueSignalResult,
    DialogueState,
)

logger = structlog.get_logger(__name__)


class DialogueIntentionEngine:
    """Single owner of all dialogue decisions.

    The engine determines intervention type before any retrieval,
    reasoning, or response generation occurs.
    """

    def __init__(
        self,
        policies: list[DialoguePolicy] | None = None,
        product_profile_id: str = "ayeneh",
    ) -> None:
        self._policies = policies or get_policies_for_profile(product_profile_id)
        self._profile_id = product_profile_id

    def analyze(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> DialogueAnalysis:
        """Analyze the dialogue state and detect needs/signals."""
        ctx = context or {}
        analysis = DialogueAnalysis()

        # Stage 1: Conversation metadata
        analysis.message_count = ctx.get("message_count", 0)
        analysis.conversation_stage = self._determine_stage(analysis.message_count)

        # Stage 2: User intention
        analysis.user_intention, analysis.intention_confidence = self._detect_intention(query)

        # Stage 3: Detect needs
        analysis.detected_needs = self._detect_needs(query, ctx)

        # Stage 4: Detect signals
        analysis.detected_signals = self._detect_signals(query, ctx)

        # Stage 5: Emotional state
        analysis.emotional_pressure = self._measure_emotional_pressure(query, ctx)
        analysis.urgency = self._measure_urgency(query)
        analysis.ambiguity = self._measure_ambiguity(query)

        # Stage 6: Dependency risk
        dep_result = self._assess_dependency_risk(query, ctx)
        analysis.dependency_risk = dep_result["risk"]
        analysis.seeking_certainty = dep_result["seeking_certainty"]
        analysis.outsourcing_decisions = dep_result["outsourcing"]
        analysis.reassurance_seeking = dep_result["reassurance"]

        # Stage 7: Avoidance and rumination
        analysis.avoidance_indicators = self._detect_avoidance(query)
        analysis.rumination_indicators = self._detect_rumination(query, ctx)

        # Stage 8: Confirmation seeking
        analysis.confirmation_seeking = self._detect_confirmation_seeking(query)

        # Stage 9: Confidence
        analysis.confidence = self._compute_analysis_confidence(analysis)

        # Stage 10: Reasoning
        analysis.reasoning = self._build_analysis_reasoning(analysis)

        return analysis

    def decide(
        self,
        analysis: DialogueAnalysis,
        context: dict[str, Any] | None = None,
    ) -> DialogueDecision:
        """Produce a structured dialogue decision from the analysis."""
        ctx = context or {}
        start = time.monotonic()

        decision = DialogueDecision(analysis=analysis)

        # Get applicable policies
        applicable = self._get_applicable_policies(ctx)

        # Score each intervention
        scores = self._score_interventions(analysis, applicable, ctx)

        # Select the best intervention
        sorted_interventions = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if sorted_interventions:
            decision.selected_intervention = sorted_interventions[0][0]
            decision.alternative_interventions = [
                inv for inv, _ in sorted_interventions[1:4]
            ]

        # Build reasoning
        decision.reasoning = self._build_decision_reasoning(
            decision.selected_intervention,
            scores,
            analysis,
            applicable,
        )

        # Risk assessments
        decision.dependency_risk = analysis.dependency_risk
        decision.epistemic_risk = self._compute_epistemic_risk(analysis)

        # Confidence
        decision.confidence = self._compute_decision_confidence(decision, analysis)

        # Expected outcome
        decision.expected_outcome = self._predict_outcome(decision)

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "dialogue_decision",
            intervention=decision.selected_intervention,
            confidence=round(decision.confidence, 2),
            latency_ms=round(elapsed_ms, 2),
        )

        return decision

    # ------------------------------------------------------------------
    # Stage 1: Conversation stage
    # ------------------------------------------------------------------

    def _determine_stage(self, message_count: int) -> DialogueState:
        if message_count == 0:
            return DialogueState.OPENING
        if message_count <= 3:
            return DialogueState.EXPLORING
        if message_count <= 8:
            return DialogueState.DEEPENING
        if message_count <= 15:
            return DialogueState.REFLECTING
        return DialogueState.INTEGRATING

    # ------------------------------------------------------------------
    # Stage 2: Intention
    # ------------------------------------------------------------------

    def _detect_intention(self, query: str) -> tuple[str, float]:
        q = query.lower()

        if any(w in q for w in ["should i", "which", "decide", "choose"]):
            return "decision_making", 0.8
        if any(w in q for w in ["i feel", "i notice", "i think", "reflecting"]):
            return "self_observation", 0.8
        if any(w in q for w in ["explain", "teach", "what is", "how does"]):
            return "knowledge_seeking", 0.7
        if any(w in q for w in ["help", "advice", "suggest", "recommend"]):
            return "advice_seeking", 0.8
        if any(w in q for w in ["my pattern", "always", "never", "keep"]):
            return "pattern_recognition", 0.7
        return "general_inquiry", 0.5

    # ------------------------------------------------------------------
    # Stage 3: Needs
    # ------------------------------------------------------------------

    def _detect_needs(self, query: str, ctx: dict) -> list[DialogueNeedResult]:
        results: list[DialogueNeedResult] = []
        q = query.lower()

        need_patterns: dict[DialogueNeed, list[str]] = {
            DialogueNeed.CERTAINTY: ["sure", "certain", "definitely", "prove", "fact"],
            DialogueNeed.EXPLORATION: ["explore", "wonder", "curious", "what if", "maybe"],
            DialogueNeed.CLARIFICATION: ["confused", "unclear", "don't understand", "meaning"],
            DialogueNeed.REFLECTION: ["reflect", "think about", "consider", "notice"],
            DialogueNeed.ACTION: ["do", "action", "step", "plan", "how to", "practice"],
            DialogueNeed.KNOWLEDGE: ["learn", "teach", "explain", "book", "research"],
            DialogueNeed.SILENCE: ["quiet", "pause", "stop", "enough"],
            DialogueNeed.CHALLENGE: ["challenge", "question", "disagree", "but"],
            DialogueNeed.VALIDATION: ["agree", "right", "correct", "confirm"],
            DialogueNeed.SUPPORT: ["help", "support", "struggling", "difficult", "hard"],
        }

        for need, keywords in need_patterns.items():
            matches = [kw for kw in keywords if kw in q]
            if matches:
                confidence = min(1.0, 0.4 + len(matches) * 0.2)
                results.append(DialogueNeedResult(
                    need=need,
                    confidence=confidence,
                    evidence=[f"matched: {', '.join(matches[:3])}"],
                ))

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Stage 4: Signals
    # ------------------------------------------------------------------

    def _detect_signals(self, query: str, ctx: dict) -> list[DialogueSignalResult]:
        results: list[DialogueSignalResult] = []
        q = query.lower()

        signal_patterns: dict[DialogueSignal, list[str]] = {
            DialogueSignal.EMOTIONAL_PRESSURE: [
                "urgent", "emergency", "can't", "breaking", "desperate", "panic",
            ],
            DialogueSignal.DEPENDENCY_SEEKING: [
                "tell me", "what should", "give me", "just answer", "right or wrong",
            ],
            DialogueSignal.RUMINATION: [
                "again", "keep thinking", "can't stop", "over and over", "loop",
            ],
            DialogueSignal.CONFIRMATION_SEEKING: [
                "right?", "don't you think?", "isn't it?", "agree?",
            ],
            DialogueSignal.URGENCY: [
                "now", "immediately", "asap", "hurry", "deadline",
            ],
            DialogueSignal.AVOIDANCE: [
                "don't want to", "avoid", "ignore", "skip", "not ready",
            ],
            DialogueSignal.AWARENESS: [
                "i notice", "i see", "i realize", "awareness", "observe",
            ],
            DialogueSignal.CURIOSITY: [
                "wonder", "curious", "what if", "interesting", "explore",
            ],
            DialogueSignal.RESISTANCE: [
                "no", "but", "however", "disagree", "wrong",
            ],
            DialogueSignal.OPENNESS: [
                "yes", "okay", "sure", "open", "willing", "ready",
            ],
        }

        for signal, keywords in signal_patterns.items():
            matches = [kw for kw in keywords if kw in q]
            if matches:
                confidence = min(1.0, 0.3 + len(matches) * 0.25)
                results.append(DialogueSignalResult(
                    signal=signal,
                    confidence=confidence,
                    evidence=[f"matched: {', '.join(matches[:3])}"],
                ))

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Stage 5: Emotional state
    # ------------------------------------------------------------------

    def _measure_emotional_pressure(self, query: str, ctx: dict) -> float:
        q = query.lower()
        pressure_words = [
            "urgent", "can't", "breaking", "desperate", "panic",
            "overwhelmed", "stuck", "trapped", "helpless",
        ]
        matches = sum(1 for w in pressure_words if w in q)
        history_pressure = ctx.get("previous_pressure", 0.0)
        return min(1.0, matches * 0.2 + history_pressure * 0.3)

    def _measure_urgency(self, query: str) -> float:
        q = query.lower()
        urgency_words = ["now", "immediately", "asap", "hurry", "deadline", "today"]
        matches = sum(1 for w in urgency_words if w in q)
        return min(1.0, matches * 0.25)

    def _measure_ambiguity(self, query: str) -> float:
        q = query.lower()
        ambiguous_markers = ["maybe", "perhaps", "somehow", "sort of", "kind of", "i guess"]
        clear_markers = ["definitely", "certainly", "exactly", "specifically"]
        ambig = sum(1 for m in ambiguous_markers if m in q)
        clear = sum(1 for m in clear_markers if m in q)
        return min(1.0, max(0.0, 0.5 + ambig * 0.15 - clear * 0.15))

    # ------------------------------------------------------------------
    # Stage 6: Dependency risk
    # ------------------------------------------------------------------

    def _assess_dependency_risk(self, query: str, ctx: dict) -> dict[str, Any]:
        q = query.lower()
        risk = 0.0
        seeking_certainty = False
        outsourcing = False
        reassurance = False

        # Certainty seeking
        certainty_words = ["tell me", "what should", "right or wrong", "correct answer"]
        if any(w in q for w in certainty_words):
            risk += 0.3
            seeking_certainty = True

        # Outsourcing decisions
        outsource_words = ["decide for me", "what should i", "give me advice"]
        if any(w in q for w in outsource_words):
            risk += 0.3
            outsourcing = True

        # Reassurance seeking
        reassurance_words = ["right?", "don't you think?", "isn't it?", "agree?"]
        if any(w in q for w in reassurance_words):
            risk += 0.2
            reassurance = True

        # History factor
        history_risk = ctx.get("dependency_risk_history", [])
        if history_risk:
            avg_history = sum(history_risk) / len(history_risk)
            risk = risk * 0.7 + avg_history * 0.3

        return {
            "risk": min(1.0, risk),
            "seeking_certainty": seeking_certainty,
            "outsourcing": outsourcing,
            "reassurance": reassurance,
        }

    # ------------------------------------------------------------------
    # Stage 7: Avoidance and rumination
    # ------------------------------------------------------------------

    def _detect_avoidance(self, query: str) -> list[str]:
        indicators: list[str] = []
        q = query.lower()
        if any(w in q for w in ["don't want to", "avoid", "ignore"]):
            indicators.append("explicit_avoidance")
        if any(w in q for w in ["not ready", "can't face", "too hard"]):
            indicators.append("readiness_block")
        if any(w in q for w in ["later", "not now", "skip"]):
            indicators.append("procrastination")
        return indicators

    def _detect_rumination(self, query: str, ctx: dict) -> list[str]:
        indicators: list[str] = []
        q = query.lower()
        if any(w in q for w in ["again", "keep thinking", "can't stop"]):
            indicators.append("repetitive_thought")
        if any(w in q for w in ["over and over", "loop", "same thing"]):
            indicators.append("thought_loop")
        previous_queries = ctx.get("previous_queries", [])
        if previous_queries:
            # Simple similarity check
            for prev in previous_queries[-3:]:
                if self._queries_similar(q, prev):
                    indicators.append("query_similarity")
                    break
        return indicators

    def _queries_similar(self, q1: str, q2: str) -> bool:
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap > 0.6

    def _detect_confirmation_seeking(self, query: str) -> bool:
        q = query.lower()
        return any(w in q for w in ["right?", "don't you think?", "isn't it?", "agree?"])

    # ------------------------------------------------------------------
    # Stage 8: Analysis confidence
    # ------------------------------------------------------------------

    def _compute_analysis_confidence(self, analysis: DialogueAnalysis) -> float:
        factors: list[float] = []
        factors.append(analysis.intention_confidence)
        if analysis.detected_needs:
            factors.append(analysis.detected_needs[0].confidence)
        if analysis.detected_signals:
            factors.append(analysis.detected_signals[0].confidence)
        return sum(factors) / len(factors) if factors else 0.5

    def _build_analysis_reasoning(self, analysis: DialogueAnalysis) -> list[str]:
        reasoning: list[str] = []
        reasoning.append(f"Stage: {analysis.conversation_stage}")
        reasoning.append(f"Intention: {analysis.user_intention} ({analysis.intention_confidence:.2f})")
        if analysis.detected_needs:
            top_needs = [n.need.value for n in analysis.detected_needs[:3]]
            reasoning.append(f"Top needs: {', '.join(top_needs)}")
        if analysis.dependency_risk > 0.5:
            reasoning.append(f"High dependency risk: {analysis.dependency_risk:.2f}")
        if analysis.emotional_pressure > 0.5:
            reasoning.append(f"High emotional pressure: {analysis.emotional_pressure:.2f}")
        return reasoning

    # ------------------------------------------------------------------
    # Decision: Intervention scoring
    # ------------------------------------------------------------------

    def _score_interventions(
        self,
        analysis: DialogueAnalysis,
        policies: list[DialoguePolicy],
        ctx: dict,
    ) -> dict[DialogueIntervention, float]:
        scores: dict[DialogueIntervention, float] = {}
        q = analysis.user_intention

        # Base scores by intention
        intention_scores: dict[str, dict[DialogueIntervention, float]] = {
            "advice_seeking": {
                DialogueIntervention.REFLECTIVE_QUESTION: 0.8,
                DialogueIntervention.OBSERVATION_MIRROR: 0.6,
                DialogueIntervention.NO_INTERVENTION: 0.3,
            },
            "self_observation": {
                DialogueIntervention.OBSERVATION_MIRROR: 0.9,
                DialogueIntervention.PATTERN_REFLECTION: 0.7,
                DialogueIntervention.REFLECTIVE_QUESTION: 0.6,
            },
            "knowledge_seeking": {
                DialogueIntervention.KNOWLEDGE_EXPLANATION: 0.8,
                DialogueIntervention.EVIDENCE_PRESENTATION: 0.7,
                DialogueIntervention.REFLECTIVE_QUESTION: 0.5,
            },
            "decision_making": {
                DialogueIntervention.MULTIPLE_FRAMEWORK_COMPARISON: 0.7,
                DialogueIntervention.REFLECTIVE_QUESTION: 0.8,
                DialogueIntervention.PERSPECTIVE_EXPANSION: 0.6,
            },
            "pattern_recognition": {
                DialogueIntervention.PATTERN_REFLECTION: 0.9,
                DialogueIntervention.OBSERVATION_MIRROR: 0.7,
            },
            "general_inquiry": {
                DialogueIntervention.REFLECTIVE_QUESTION: 0.7,
                DialogueIntervention.OPEN_EXPLORATION: 0.6,
                DialogueIntervention.CLARIFICATION: 0.5,
            },
        }

        base = intention_scores.get(q, intention_scores.get("general_inquiry", {}))
        scores.update(base)

        # Dependency risk adjustments
        if analysis.dependency_risk > 0.6:
            scores[DialogueIntervention.REFLECTIVE_QUESTION] = scores.get(
                DialogueIntervention.REFLECTIVE_QUESTION, 0.5
            ) + 0.3
            scores[DialogueIntervention.OBSERVATION_MIRROR] = scores.get(
                DialogueIntervention.OBSERVATION_MIRROR, 0.5
            ) + 0.2
            scores[DialogueIntervention.CHALLENGE_ASSUMPTION] = scores.get(
                DialogueIntervention.CHALLENGE_ASSUMPTION, 0.3
            ) + 0.2

        # Emotional pressure adjustments
        if analysis.emotional_pressure > 0.6:
            scores[DialogueIntervention.SILENCE] = scores.get(
                DialogueIntervention.SILENCE, 0.2
            ) + 0.3
            scores[DialogueIntervention.UNCERTAINTY_STATEMENT] = scores.get(
                DialogueIntervention.UNCERTAINTY_STATEMENT, 0.3
            ) + 0.2

        # Rumination adjustments
        if analysis.rumination_indicators:
            scores[DialogueIntervention.REFRAMING] = scores.get(
                DialogueIntervention.REFRAMING, 0.3
            ) + 0.3
            scores[DialogueIntervention.PERSPECTIVE_EXPANSION] = scores.get(
                DialogueIntervention.PERSPECTIVE_EXPANSION, 0.4
            ) + 0.2

        # Policy adjustments
        for policy in policies:
            if policy.should_apply(ctx):
                # Policies can boost certain interventions
                if policy.name == "observation_first":
                    scores[DialogueIntervention.OBSERVATION_MIRROR] = scores.get(
                        DialogueIntervention.OBSERVATION_MIRROR, 0.5
                    ) + 0.2
                elif policy.name == "question_before_advice":
                    scores[DialogueIntervention.REFLECTIVE_QUESTION] = scores.get(
                        DialogueIntervention.REFLECTIVE_QUESTION, 0.5
                    ) + 0.2
                elif policy.name == "preserve_uncertainty":
                    scores[DialogueIntervention.UNCERTAINTY_STATEMENT] = scores.get(
                        DialogueIntervention.UNCERTAINTY_STATEMENT, 0.3
                    ) + 0.2
                elif policy.name == "promote_autonomy":
                    scores[DialogueIntervention.CHALLENGE_ASSUMPTION] = scores.get(
                        DialogueIntervention.CHALLENGE_ASSUMPTION, 0.3
                    ) + 0.1

        # Normalize
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _get_applicable_policies(self, ctx: dict) -> list[DialoguePolicy]:
        return [p for p in self._policies if p.should_apply(ctx)]

    def _build_decision_reasoning(
        self,
        selected: DialogueIntervention,
        scores: dict[DialogueIntervention, float],
        analysis: DialogueAnalysis,
        policies: list[DialoguePolicy],
    ) -> DialogueReasoning:
        reasoning = DialogueReasoning()

        # Why selected
        reasoning.why_selected.append(
            f"Selected {selected.value} with score {scores.get(selected, 0):.2f}"
        )
        if analysis.dependency_risk > 0.5:
            reasoning.dependency_considerations.append(
                f"Dependency risk elevated ({analysis.dependency_risk:.2f}), prefer reflective interventions"
            )

        # Why rejected
        for inv, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            if inv != selected and score > 0.3:
                reasoning.why_rejected[inv.value] = [f"Score {score:.2f} lower than selected"]

        # Policy considerations
        for policy in policies:
            reasoning.policy_considerations.append(f"Applied policy: {policy.name}")

        return reasoning

    def _compute_epistemic_risk(self, analysis: DialogueAnalysis) -> float:
        risk = 0.0
        if analysis.seeking_certainty:
            risk += 0.3
        if analysis.confirmation_seeking:
            risk += 0.2
        if analysis.ambiguity > 0.7:
            risk += 0.2
        return min(1.0, risk)

    def _compute_decision_confidence(
        self,
        decision: DialogueDecision,
        analysis: DialogueAnalysis,
    ) -> float:
        factors = [analysis.confidence]
        if decision.dependency_risk > 0.7:
            factors.append(0.3)
        else:
            factors.append(0.7)
        return sum(factors) / len(factors)

    def _predict_outcome(self, decision: DialogueDecision) -> str:
        outcomes: dict[DialogueIntervention, str] = {
            DialogueIntervention.REFLECTIVE_QUESTION: "User explores their own thinking",
            DialogueIntervention.OBSERVATION_MIRROR: "User gains awareness of patterns",
            DialogueIntervention.CHALLENGE_ASSUMPTION: "User questions their assumptions",
            DialogueIntervention.UNCERTAINTY_STATEMENT: "User sits with uncertainty",
            DialogueIntervention.SILENCE: "User has space to process",
            DialogueIntervention.KNOWLEDGE_EXPLANATION: "User gains understanding",
            DialogueIntervention.PATTERN_REFLECTION: "User recognizes behavioral patterns",
            DialogueIntervention.REFRAMING: "User sees situation from new angle",
            DialogueIntervention.PERSPECTIVE_EXPANSION: "User considers multiple viewpoints",
            DialogueIntervention.NO_INTERVENTION: "Conversation continues naturally",
        }
        return outcomes.get(decision.selected_intervention, "Conversation continues")
