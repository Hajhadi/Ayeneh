"""Decision Learning — COG-10 supporting module.

Analyses decision outcomes, detects regret, and extracts learning objects
that feed back into the cognitive system for future decision improvement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from ayeneh.cog.decision.types import DecisionObject

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Learning types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegretObject:
    """Captures post-decision regret when outcomes diverge from expectations."""

    decision_id: str
    regret_level: float = 0.0
    expectation: str = ''
    actual_outcome: str = ''
    learning: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class DecisionLearningObject:
    """A generalised learning extracted from a decision outcome."""

    decision_id: str
    learning_statement: str
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Outcome analysis result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutcomeAnalysis:
    """Full result of analysing a single decision outcome."""

    decision_id: str
    outcome_category: str = 'pending'
    regret: RegretObject | None = None
    learning: DecisionLearningObject | None = None
    adjustments: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# DecisionLearner
# ---------------------------------------------------------------------------


class DecisionLearner:
    """Analyses decision outcomes and extracts learning objects.

    Pipeline:
        1. Outcome Classification — categorise the outcome
        2. Regret Detection — compare expectation vs actual
        3. Learning Extraction — generalise actionable insight
        4. Adjustment Propagation — identify downstream adjustments
    """

    def analyze_outcome(
        self,
        decision: DecisionObject,
        outcome: str,
    ) -> OutcomeAnalysis:
        """Analyse the outcome of a decision and return structured learning.

        Parameters
        ----------
        decision:
            The decision object to analyse.
        outcome:
            Description of the actual outcome.
        """
        logger.info(
            'cog.decision.learning.analysing',
            decision_id=decision.identifier,
        )

        category = self._classify_outcome(decision, outcome)
        regret = self._detect_regret(decision, outcome)
        learning = self._extract_learning(decision, outcome)
        adjustments = self._identify_adjustments(decision, category, regret)

        return OutcomeAnalysis(
            decision_id=decision.identifier,
            outcome_category=category,
            regret=regret,
            learning=learning,
            adjustments=tuple(adjustments),
        )

    # ------------------------------------------------------------------
    # Phase 1: Outcome Classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_outcome(decision: DecisionObject, outcome: str) -> str:
        """Classify the outcome as positive, negative, neutral, or mixed."""
        if not outcome:
            return 'pending'

        outcome_lower = outcome.lower()
        positive_signals = ('success', 'positive', 'good', 'improved', 'benefit')
        negative_signals = ('failure', 'negative', 'bad', 'worsened', 'cost', 'loss')

        pos = sum(1 for s in positive_signals if s in outcome_lower)
        neg = sum(1 for s in negative_signals if s in outcome_lower)

        if pos > 0 and neg > 0:
            return 'mixed'
        if pos > 0:
            return 'positive'
        if neg > 0:
            return 'negative'
        return 'neutral'

    # ------------------------------------------------------------------
    # Phase 2: Regret Detection
    # ------------------------------------------------------------------

    def _detect_regret(
        self,
        decision: DecisionObject,
        outcome: str,
    ) -> RegretObject | None:
        """Detect regret when outcome diverges from expectation."""
        if not decision.chosen_alternative or not outcome:
            return None

        # Regret is detected when rejected alternatives might have been better
        if not decision.rejected_alternatives:
            return None

        outcome_lower = outcome.lower()
        regret_signals = ('should have', 'regret', 'wish i had', 'better if', 'mistake')

        has_regret_signal = any(s in outcome_lower for s in regret_signals)
        negative_outcome = any(
            neg in outcome_lower
            for neg in ('failure', 'negative', 'bad', 'loss', 'worse')
        )

        if not has_regret_signal and not negative_outcome:
            return None

        # Compute regret level
        regret_level = 0.0
        if has_regret_signal:
            regret_level = 0.7
        elif negative_outcome:
            regret_level = 0.4

        # Higher regret when decision inertia was high (hard to change)
        regret_level = min(1.0, regret_level + decision.decision_inertia * 0.2)

        expectation = f"Expected positive outcome from '{decision.chosen_alternative}'"

        return RegretObject(
            decision_id=decision.identifier,
            regret_level=regret_level,
            expectation=expectation,
            actual_outcome=outcome,
            learning=f"Outcome of '{decision.chosen_alternative}' diverged from expectation",
        )

    # ------------------------------------------------------------------
    # Phase 3: Learning Extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_learning(
        decision: DecisionObject,
        outcome: str,
    ) -> DecisionLearningObject | None:
        """Extract a generalised learning from the decision-outcome pair."""
        if not outcome:
            return None

        # Build learning from activated structures
        activated = []
        if decision.activated_beliefs:
            activated.append(f"beliefs: {', '.join(decision.activated_beliefs)}")
        if decision.activated_values:
            activated.append(f"values: {', '.join(decision.activated_values)}")
        if decision.activated_narratives:
            activated.append(f"narratives: {', '.join(decision.activated_narratives)}")

        activation_str = '; '.join(activated) if activated else 'no activated structures'
        learning_text = (
            f"Decision '{decision.decision_statement}' in context '{decision.context}' "
            f"with {activation_str} led to outcome: {outcome}"
        )

        # Confidence based on evidence strength
        evidence_count = len(decision.supporting_evidence)
        confidence = min(1.0, 0.3 + evidence_count * 0.1)

        return DecisionLearningObject(
            decision_id=decision.identifier,
            learning_statement=learning_text,
            confidence=confidence,
            evidence=decision.supporting_evidence,
        )

    # ------------------------------------------------------------------
    # Phase 4: Adjustment Identification
    # ------------------------------------------------------------------

    @staticmethod
    def _identify_adjustments(
        decision: DecisionObject,
        outcome_category: str,
        regret: RegretObject | None,
    ) -> list[str]:
        """Identify downstream adjustments needed based on outcome."""
        adjustments: list[str] = []

        if outcome_category == 'negative':
            adjustments.append('reconsider_activated_beliefs')
            if decision.activated_narratives:
                adjustments.append('review_narrative_influence')
        elif outcome_category == 'mixed':
            adjustments.append('refine_alternative_generation')
        elif outcome_category == 'positive':
            adjustments.append('reinforce_decision_pattern')

        if regret and regret.regret_level > 0.5:
            adjustments.append('high_priority_regret_processing')
            if decision.rejected_alternatives:
                adjustments.append('revisit_rejected_alternatives')

        return adjustments
