"""Identity Coherence Estimator — COG-09 supporting module.

Measures structural consistency between identity components and the
cognitive subsystems they connect to: beliefs, values, goals, and
narratives. A coherent identity exhibits alignment across all four axes.
"""

from __future__ import annotations

import structlog

from ayeneh.cog.identity.types import IdentityComponent

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# IdentityCoherenceEstimator
# ---------------------------------------------------------------------------


class IdentityCoherenceEstimator:
    """Estimates coherence between identity and supporting cognitive structures.

    Coherence is computed as the weighted average of four alignment dimensions:
        1. Behavioral alignment — evidence-backed components are coherent.
        2. Value–belief consistency — values and beliefs mutually reinforce.
        3. Goal–value alignment — goals emerge from stated values.
        4. Narrative–belief coherence — narratives reflect underlying beliefs.
    """

    # Dimension weights (must sum to 1.0)
    WEIGHT_BEHAVIORAL: float = 0.30
    WEIGHT_VALUE_BELIEF: float = 0.25
    WEIGHT_GOAL_VALUE: float = 0.25
    WEIGHT_NARRATIVE_BELIEF: float = 0.20

    def estimate(
        self,
        components: dict[str, IdentityComponent],
        beliefs: list[str] | None = None,
        values: list[str] | None = None,
        goals: list[str] | None = None,
    ) -> float:
        """Estimate alignment between identity, beliefs, values, and goals.

        Returns a float in [0.0, 1.0] where 1.0 means perfect coherence.
        """
        if not components:
            logger.info('cog.identity.coherence.no_components')
            return 0.0

        beliefs = beliefs or []
        values = values or []
        goals = goals or []

        behavioral = self._behavioral_alignment(components)
        value_belief = self._value_belief_consistency(components, beliefs, values)
        goal_value = self._goal_value_alignment(components, goals, values)
        narrative_belief = self._narrative_belief_coherence(components, beliefs)

        overall = (
            behavioral * self.WEIGHT_BEHAVIORAL
            + value_belief * self.WEIGHT_VALUE_BELIEF
            + goal_value * self.WEIGHT_GOAL_VALUE
            + narrative_belief * self.WEIGHT_NARRATIVE_BELIEF
        )

        logger.info(
            'cog.identity.coherence.estimated',
            behavioral=behavioral,
            value_belief=value_belief,
            goal_value=goal_value,
            narrative_belief=narrative_belief,
            overall=overall,
        )
        return overall

    # ------------------------------------------------------------------
    # Dimension 1: Behavioral alignment
    # ------------------------------------------------------------------

    @staticmethod
    def _behavioral_alignment(components: dict[str, IdentityComponent]) -> float:
        """Fraction of components that have supporting evidence."""
        if not components:
            return 0.0
        backed = sum(
            1 for c in components.values() if len(c.supporting_evidence) > 0
        )
        return backed / len(components)

    # ------------------------------------------------------------------
    # Dimension 2: Value–belief consistency
    # ------------------------------------------------------------------

    @staticmethod
    def _value_belief_consistency(
        components: dict[str, IdentityComponent],
        beliefs: list[str],
        values: list[str],
    ) -> float:
        """Check that components referencing values also reference beliefs."""
        if not components:
            return 0.0
        if not values:
            return 0.5  # neutral when no values provided

        value_linked = 0
        for comp in components.values():
            has_value = any(v in comp.supporting_values for v in values)
            has_belief = any(b in comp.supporting_beliefs for b in beliefs) if beliefs else False
            if has_value and has_belief:
                value_linked += 1
            elif has_value:
                value_linked += 0.5  # partial credit

        return min(1.0, value_linked / len(components))

    # ------------------------------------------------------------------
    # Dimension 3: Goal–value alignment
    # ------------------------------------------------------------------

    @staticmethod
    def _goal_value_alignment(
        components: dict[str, IdentityComponent],
        goals: list[str],
        values: list[str],
    ) -> float:
        """Check that goals are anchored in values."""
        if not goals:
            return 0.5  # neutral when no goals provided
        if not values:
            return 0.5

        aligned = 0
        for comp in components.values():
            has_goal = any(g in comp.supporting_goals for g in goals)
            has_value = any(v in comp.supporting_values for v in values)
            if has_goal and has_value:
                aligned += 1

        if not components:
            return 0.0
        return min(1.0, aligned / len(components))

    # ------------------------------------------------------------------
    # Dimension 4: Narrative–belief coherence
    # ------------------------------------------------------------------

    @staticmethod
    def _narrative_belief_coherence(
        components: dict[str, IdentityComponent],
        beliefs: list[str],
    ) -> float:
        """Check that narratives are grounded in beliefs."""
        if not components:
            return 0.0
        if not beliefs:
            return 0.5  # neutral when no beliefs provided

        coherent = 0
        for comp in components.values():
            has_narrative = len(comp.supporting_narratives) > 0
            has_belief = any(b in comp.supporting_beliefs for b in beliefs)
            if has_narrative and has_belief:
                coherent += 1
            elif not has_narrative:
                coherent += 0.3  # no narrative is less risky than contradictory

        return min(1.0, coherent / len(components))
