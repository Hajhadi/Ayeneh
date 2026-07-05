"""Decision Architecture Engine — COG-10.

Reconstructs the decision-making process by extracting decisions from evidence,
activating relevant cognitive structures (beliefs, values, goals, narratives,
identity), evaluating alternatives, detecting recurring patterns, and tracking
trade-offs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from ayeneh.cog.decision.learning import DecisionLearner, OutcomeAnalysis
from ayeneh.cog.decision.types import (
    DecisionObject,
    DecisionPattern,
    DecisionResult,
    TradeOff,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Decision Architecture Engine
# ---------------------------------------------------------------------------


class DecisionArchitectureEngine:
    """Models how decisions emerge from interacting cognitive structures (COG-10).

    Pipeline:
        1. Situation Extraction — identify decision situations from evidence
        2. Structure Activation — activate beliefs, values, goals, narratives
        3. Alternative Generation — enumerate considered alternatives
        4. Evaluation — score alternatives against activated structures
        5. Decision Recording — capture the full decision object
        6. Pattern Detection — find recurring decision structures
        7. Trade-Off Tracking — identify value conflicts
    """

    def __init__(self) -> None:
        self._decisions: dict[str, DecisionObject] = {}
        self._patterns: dict[str, DecisionPattern] = {}
        self._learner = DecisionLearner()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[dict[str, str]],
        beliefs: list[str] | None = None,
        values: list[str] | None = None,
        goals: list[str] | None = None,
        narratives: list[str] | None = None,
        identity: list[str] | None = None,
    ) -> DecisionResult:
        """Run the full COG-10 pipeline.

        Parameters
        ----------
        evidence:
            List of evidence dicts with ``'text'``, ``'id'``, and optional
            ``'category'`` keys.
        beliefs, values, goals, narratives, identity:
            Lists of string identifiers from upstream cognitive subsystems.
        """
        logger.info('cog.decision.pipeline_started', evidence_count=len(evidence))

        # Phase 1 — Situation Extraction
        candidates = self._extract_decisions(evidence)

        # Phase 2–5 — Activation → Evaluation → Recording
        activated = self._activate_structures(
            candidates, beliefs, values, goals, narratives, identity,
        )
        evaluated = self._evaluate(activated)
        recorded = self._record(evaluated)

        # Phase 6 — Pattern Detection
        patterns = self._detect_patterns(recorded)

        # Phase 7 — Trade-Off Tracking
        trade_offs = self._track_trade_offs(recorded, values)

        # Store decisions
        for d in recorded.values():
            self._decisions[d.identifier] = d

        lifecycle_summary: dict[str, int] = {}
        for d in recorded.values():
            lifecycle_summary[d.lifecycle_state] = (
                lifecycle_summary.get(d.lifecycle_state, 0) + 1
            )

        result = DecisionResult(
            decisions=recorded,
            patterns=patterns,
            trade_offs=tuple(trade_offs),
            total_extracted=len(recorded),
            lifecycle_summary=lifecycle_summary,
        )

        logger.info(
            'cog.decision.pipeline_completed',
            total_extracted=result.total_extracted,
            patterns_found=len(patterns),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Situation Extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_decisions(evidence: list[dict[str, str]]) -> list[DecisionObject]:
        """Identify decision situations from evidence."""
        candidates: list[DecisionObject] = []

        for ev in evidence:
            text = ev.get('text', '')
            ev_id = ev.get('id', '')
            category = ev.get('category', '')

            if not DecisionArchitectureEngine._is_decision_relevant(text, category):
                continue

            # Extract alternatives if mentioned
            alternatives = DecisionArchitectureEngine._extract_alternatives(text)
            chosen = alternatives[0] if alternatives else ''
            rejected = tuple(alternatives[1:]) if len(alternatives) > 1 else ()

            comp = DecisionObject(
                identifier=str(uuid.uuid4()),
                decision_statement=text,
                context=category or 'general',
                alternatives=tuple(alternatives),
                chosen_alternative=chosen,
                rejected_alternatives=rejected,
                supporting_evidence=(ev_id,) if ev_id else (),
                confidence=0.3,
                uncertainty=0.5,
                lifecycle_state='candidate',
            )
            candidates.append(comp)

        logger.info('cog.decision.candidates_extracted', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Structure Activation
    # ------------------------------------------------------------------

    @staticmethod
    def _activate_structures(
        candidates: list[DecisionObject],
        beliefs: list[str] | None,
        values: list[str] | None,
        goals: list[str] | None,
        narratives: list[str] | None,
        identity: list[str] | None,
    ) -> list[DecisionObject]:
        """Activate cognitive structures relevant to each decision."""
        beliefs = beliefs or []
        values = values or []
        goals = goals or []
        narratives = narratives or []
        identity = identity or []

        activated: list[DecisionObject] = []
        for c in candidates:
            # Activate structures based on text matching
            act_beliefs = DecisionArchitectureEngine._match_structures(
                c.decision_statement, beliefs,
            )
            act_values = DecisionArchitectureEngine._match_structures(
                c.decision_statement, values,
            )
            act_goals = DecisionArchitectureEngine._match_structures(
                c.decision_statement, goals,
            )
            act_narratives = DecisionArchitectureEngine._match_structures(
                c.decision_statement, narratives,
            )
            act_identity = DecisionArchitectureEngine._match_structures(
                c.decision_statement, identity,
            )

            activated.append(DecisionObject(
                identifier=c.identifier,
                decision_statement=c.decision_statement,
                context=c.context,
                alternatives=c.alternatives,
                chosen_alternative=c.chosen_alternative,
                rejected_alternatives=c.rejected_alternatives,
                supporting_evidence=c.supporting_evidence,
                activated_narratives=tuple(act_narratives),
                activated_beliefs=tuple(act_beliefs),
                activated_values=tuple(act_values),
                activated_goals=tuple(act_goals),
                activated_identity_components=tuple(act_identity),
                confidence=c.confidence,
                uncertainty=c.uncertainty,
                behavioral_outcome=c.behavioral_outcome,
                decision_inertia=c.decision_inertia,
                lifecycle_state='emerging',
                creation_timestamp=c.creation_timestamp,
            ))

        logger.info('cog.decision.structures_activated', count=len(activated))
        return activated

    # ------------------------------------------------------------------
    # Phase 3: Evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate(
        activated: list[DecisionObject],
    ) -> dict[str, DecisionObject]:
        """Evaluate decisions — adjust confidence based on activated structures."""
        evaluated: dict[str, DecisionObject] = {}

        for c in activated:
            # Confidence increases with more activated structures
            total_activated = (
                len(c.activated_beliefs)
                + len(c.activated_values)
                + len(c.activated_goals)
                + len(c.activated_narratives)
                + len(c.activated_identity_components)
            )
            confidence = min(1.0, 0.3 + total_activated * 0.08)

            # Uncertainty decreases with more structures and alternatives
            uncertainty = max(0.0, 0.5 - total_activated * 0.04 - len(c.alternatives) * 0.05)

            # Decision inertia: more alternatives considered → more inertia
            inertia = min(1.0, len(c.alternatives) * 0.15 + total_activated * 0.05)

            evaluated[c.identifier] = DecisionObject(
                identifier=c.identifier,
                decision_statement=c.decision_statement,
                context=c.context,
                alternatives=c.alternatives,
                chosen_alternative=c.chosen_alternative,
                rejected_alternatives=c.rejected_alternatives,
                supporting_evidence=c.supporting_evidence,
                activated_narratives=c.activated_narratives,
                activated_beliefs=c.activated_beliefs,
                activated_values=c.activated_values,
                activated_goals=c.activated_goals,
                activated_identity_components=c.activated_identity_components,
                confidence=confidence,
                uncertainty=uncertainty,
                behavioral_outcome=c.behavioral_outcome,
                decision_inertia=inertia,
                lifecycle_state='validated',
                creation_timestamp=c.creation_timestamp,
            )

        logger.info('cog.decision.evaluated', count=len(evaluated))
        return evaluated

    # ------------------------------------------------------------------
    # Phase 4: Recording
    # ------------------------------------------------------------------

    @staticmethod
    def _record(evaluated: dict[str, DecisionObject]) -> dict[str, DecisionObject]:
        """Finalise decisions and record them."""
        # Decisions pass through as-is (already validated in Phase 3)
        logger.info('cog.decision.recorded', count=len(evaluated))
        return evaluated

    # ------------------------------------------------------------------
    # Phase 5: Pattern Detection
    # ------------------------------------------------------------------

    def _detect_patterns(
        self, decisions: dict[str, DecisionObject]
    ) -> dict[str, DecisionPattern]:
        """Detect recurring decision patterns."""
        patterns: dict[str, DecisionPattern] = {}

        # Group by common activated values
        value_groups: dict[str, list[str]] = {}
        for d in decisions.values():
            for v in d.activated_values:
                value_groups.setdefault(v, []).append(d.identifier)

        for value, d_ids in value_groups.items():
            if len(d_ids) >= 2:
                pattern = DecisionPattern(
                    pattern_id=str(uuid.uuid4()),
                    description=f"Recurring decision pattern aligned with value: {value}",
                    frequency=len(d_ids),
                    confidence=min(1.0, len(d_ids) * 0.2),
                    decision_ids=tuple(d_ids),
                    common_activations={'values': (value,)},
                )
                patterns[pattern.pattern_id] = pattern

        # Group by common activated beliefs
        belief_groups: dict[str, list[str]] = {}
        for d in decisions.values():
            for b in d.activated_beliefs:
                belief_groups.setdefault(b, []).append(d.identifier)

        for belief, d_ids in belief_groups.items():
            if len(d_ids) >= 2:
                pattern = DecisionPattern(
                    pattern_id=str(uuid.uuid4()),
                    description=f"Recurring decision pattern driven by belief: {belief}",
                    frequency=len(d_ids),
                    confidence=min(1.0, len(d_ids) * 0.2),
                    decision_ids=tuple(d_ids),
                    common_activations={'beliefs': (belief,)},
                )
                patterns[pattern.pattern_id] = pattern

        logger.info('cog.decision.patterns_detected', count=len(patterns))
        return patterns

    # ------------------------------------------------------------------
    # Phase 6: Trade-Off Tracking
    # ------------------------------------------------------------------

    @staticmethod
    def _track_trade_offs(
        decisions: dict[str, DecisionObject],
        values: list[str] | None,
    ) -> list[TradeOff]:
        """Identify value conflicts in decisions."""
        trade_offs: list[TradeOff] = []
        values = values or []

        for d in decisions.values():
            if len(d.activated_values) < 2 or not d.rejected_alternatives:
                continue

            # Each pair of activated values represents a potential trade-off
            act_vals = list(d.activated_values)
            for i in range(len(act_vals)):
                for j in range(i + 1, len(act_vals)):
                    trade_offs.append(TradeOff(
                        decision_id=d.identifier,
                        value_a=act_vals[i],
                        value_b=act_vals[j],
                        chosen=d.chosen_alternative,
                        rejected=d.rejected_alternatives[0] if d.rejected_alternatives else '',
                        opportunity_cost=0.5,
                    ))

        return trade_offs

    # ------------------------------------------------------------------
    # Learning interface
    # ------------------------------------------------------------------

    def learn_from_outcome(
        self, decision_id: str, outcome: str,
    ) -> OutcomeAnalysis | None:
        """Analyse a decision outcome and extract learning."""
        decision = self._decisions.get(decision_id)
        if decision is None:
            logger.warning(
                'cog.decision.learning.unknown_decision', decision_id=decision_id,
            )
            return None
        return self._learner.analyze_outcome(decision, outcome)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_decision_relevant(text: str, category: str) -> bool:
        """Determine if evidence text describes a decision."""
        if category in ('decision_report', 'intention', 'commitment'):
            return True
        decision_keywords = (
            'decided', 'chose', 'i will', 'i decided', 'i chose',
            'my plan', 'i chose to', 'rather than', 'instead of',
            'option', 'alternative', 'trade-off', 'trade off',
        )
        text_lower = text.lower()
        return any(kw in text_lower for kw in decision_keywords)

    @staticmethod
    def _extract_alternatives(text: str) -> list[str]:
        """Extract alternatives from decision text."""
        alternatives: list[str] = []

        # Check for "rather than" / "instead of" pattern
        for separator in ('rather than', 'instead of', 'instead', 'versus', 'vs'):
            if separator in text.lower():
                parts = text.lower().split(separator, 1)
                if len(parts) == 2:
                    alternatives.append(parts[0].strip())
                    alternatives.append(parts[1].strip())
                    return alternatives

        # Default: the text itself is the chosen alternative
        alternatives.append(text)
        return alternatives

    @staticmethod
    def _match_structures(
        text: str, structures: list[str],
    ) -> list[str]:
        """Match a decision text against a list of cognitive structures."""
        matched: list[str] = []
        text_lower = text.lower()
        for s in structures:
            s_lower = s.lower()
            # Simple keyword overlap matching
            if s_lower in text_lower or any(
                word in text_lower for word in s_lower.split() if len(word) > 3
            ):
                matched.append(s)
        return matched
