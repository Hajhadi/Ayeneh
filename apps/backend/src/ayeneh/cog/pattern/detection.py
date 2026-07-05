"""Loop, Fractal, and Recursive Pattern Detection — COG-11 supporting module.

Provides specialised detectors for closed behavioural/cognitive loops,
fractal self-similar patterns across scales, and recursive structures.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.cog.pattern.types import BehavioralLoop, PatternObject

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# LoopDetector
# ---------------------------------------------------------------------------


class LoopDetector:
    """Detects closed feedback loops in behavioral and cognitive patterns."""

    def detect_behavioral_loops(
        self, patterns: list[PatternObject],
    ) -> list[BehavioralLoop]:
        """Detect behavioral loops from patterns.

        A behavioral loop is inferred when a pattern has trigger and
        termination conditions that reference each other, or when multiple
        patterns form a cycle.
        """
        loops: list[BehavioralLoop] = []

        behavioral = [p for p in patterns if p.pattern_type == 'behavioral_loop']

        for pattern in behavioral:
            if pattern.frequency < 2:
                continue

            # Build loop from pattern evidence
            trigger = pattern.trigger_conditions[0] if pattern.trigger_conditions else 'unknown_trigger'
            behavior = pattern.supporting_behaviors[0] if pattern.supporting_behaviors else pattern.pattern_description
            outcome = pattern.termination_conditions[0] if pattern.termination_conditions else 'reinforcement'

            loop = BehavioralLoop(
                loop_id=str(uuid.uuid4()),
                trigger=trigger,
                narrative_activation=pattern.associated_narratives[0] if pattern.associated_narratives else '',
                belief_activation=pattern.associated_beliefs[0] if pattern.associated_beliefs else '',
                emotion='',
                decision='',
                behavior=behavior,
                outcome=outcome,
                reinforcement=outcome,
                confidence=pattern.confidence,
            )
            loops.append(loop)

        logger.info('cog.pattern.loop_detector.behavioral_loops', count=len(loops))
        return loops

    def detect_cognitive_loops(
        self, patterns: list[PatternObject],
    ) -> list[BehavioralLoop]:
        """Detect cognitive loops from patterns.

        A cognitive loop involves recursive thinking patterns where
        beliefs reinforce narratives which reinforce beliefs.
        """
        loops: list[BehavioralLoop] = []

        cognitive = [p for p in patterns if p.pattern_type == 'cognitive_loop']

        for pattern in cognitive:
            if pattern.frequency < 2:
                continue

            belief = pattern.associated_beliefs[0] if pattern.associated_beliefs else 'unknown_belief'
            narrative = pattern.associated_narratives[0] if pattern.associated_narratives else 'unknown_narrative'

            loop = BehavioralLoop(
                loop_id=str(uuid.uuid4()),
                trigger=belief,
                narrative_activation=narrative,
                belief_activation=belief,
                emotion='',
                decision='',
                behavior=pattern.pattern_description,
                outcome=f"Reinforcement of {belief}",
                reinforcement=f"Cognitive loop reinforcing {belief}",
                confidence=pattern.confidence,
            )
            loops.append(loop)

        logger.info('cog.pattern.loop_detector.cognitive_loops', count=len(loops))
        return loops


# ---------------------------------------------------------------------------
# FractalDetector
# ---------------------------------------------------------------------------


class FractalDetector:
    """Detects fractal (self-similar) patterns across scales."""

    def detect_fractal_patterns(
        self, patterns: list[PatternObject],
    ) -> list[PatternObject]:
        """Detect patterns that exhibit self-similarity across scales."""
        fractals: list[PatternObject] = []

        for i, a in enumerate(patterns):
            for b in patterns[i + 1:]:
                similarity = self.compute_cross_scale_similarity(a, b)
                if similarity > 0.7:
                    # Mark as fractal
                    fractal = PatternObject(
                        identifier=str(uuid.uuid4()),
                        pattern_description=(
                            f"Fractal similarity ({similarity:.2f}) between "
                            f"'{a.pattern_description[:50]}' and "
                            f"'{b.pattern_description[:50]}'"
                        ),
                        pattern_type='fractal',
                        frequency=a.frequency + b.frequency,
                        consistency=similarity,
                        confidence=similarity * 0.8,
                        stability=max(a.stability, b.stability),
                        influence=max(a.influence, b.influence),
                        supporting_evidence=a.supporting_evidence + b.supporting_evidence,
                        supporting_behaviors=a.supporting_behaviors + b.supporting_behaviors,
                        associated_narratives=a.associated_narratives + b.associated_narratives,
                        associated_beliefs=a.associated_beliefs + b.associated_beliefs,
                        lifecycle_state='candidate',
                    )
                    fractals.append(fractal)

        logger.info('cog.pattern.fractal_detector.detected', count=len(fractals))
        return fractals

    @staticmethod
    def compute_cross_scale_similarity(
        pattern_a: Any, pattern_b: Any,
    ) -> float:
        """Compute similarity between two patterns across scales.

        Uses a weighted overlap of shared attributes.
        """
        if pattern_a is None or pattern_b is None:
            return 0.0

        scores: list[float] = []

        # Type similarity
        if hasattr(pattern_a, 'pattern_type') and hasattr(pattern_b, 'pattern_type'):
            type_match = 1.0 if pattern_a.pattern_type == pattern_b.pattern_type else 0.0
            scores.append(type_match * 0.3)

        # Evidence overlap
        ev_a = set(pattern_a.supporting_evidence) if hasattr(pattern_a, 'supporting_evidence') else set()
        ev_b = set(pattern_b.supporting_evidence) if hasattr(pattern_b, 'supporting_evidence') else set()
        if ev_a or ev_b:
            overlap = len(ev_a & ev_b) / max(len(ev_a | ev_b), 1)
            scores.append(overlap * 0.3)

        # Belief overlap
        bel_a = set(pattern_a.associated_beliefs) if hasattr(pattern_a, 'associated_beliefs') else set()
        bel_b = set(pattern_b.associated_beliefs) if hasattr(pattern_b, 'associated_beliefs') else set()
        if bel_a or bel_b:
            overlap = len(bel_a & bel_b) / max(len(bel_a | bel_b), 1)
            scores.append(overlap * 0.2)

        # Narrative overlap
        nar_a = set(pattern_a.associated_narratives) if hasattr(pattern_a, 'associated_narratives') else set()
        nar_b = set(pattern_b.associated_narratives) if hasattr(pattern_b, 'associated_narratives') else set()
        if nar_a or nar_b:
            overlap = len(nar_a & nar_b) / max(len(nar_a | nar_b), 1)
            scores.append(overlap * 0.2)

        if not scores:
            return 0.0

        return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# RecursiveDetector
# ---------------------------------------------------------------------------


class RecursiveDetector:
    """Detects recursive structures in patterns."""

    def detect_recursive_structures(
        self, patterns: list[PatternObject],
    ) -> list[PatternObject]:
        """Detect patterns that reference or contain themselves.

        A recursive pattern is one where the pattern's outcome feeds back
        into its trigger.
        """
        recursive: list[PatternObject] = []

        for pattern in patterns:
            if self._is_recursive(pattern):
                recursive.append(PatternObject(
                    identifier=str(uuid.uuid4()),
                    pattern_description=(
                        f"Recursive structure in: {pattern.pattern_description[:80]}"
                    ),
                    pattern_type='recursive',
                    frequency=pattern.frequency,
                    consistency=pattern.consistency,
                    confidence=pattern.confidence * 0.9,
                    stability=pattern.stability,
                    influence=pattern.influence,
                    trigger_conditions=pattern.trigger_conditions,
                    termination_conditions=pattern.trigger_conditions,  # feeds back
                    contexts=pattern.contexts,
                    supporting_behaviors=pattern.supporting_behaviors,
                    supporting_evidence=pattern.supporting_evidence,
                    associated_narratives=pattern.associated_narratives,
                    associated_beliefs=pattern.associated_beliefs,
                    lifecycle_state='candidate',
                ))

        logger.info('cog.pattern.recursive_detector.detected', count=len(recursive))
        return recursive

    @staticmethod
    def _is_recursive(pattern: PatternObject) -> bool:
        """Check if a pattern's outcome feeds back into its trigger."""
        if not pattern.trigger_conditions or not pattern.termination_conditions:
            return False

        trigger_set = set(t.lower() for t in pattern.trigger_conditions)
        term_set = set(t.lower() for t in pattern.termination_conditions)

        # Check for overlap between triggers and terminations
        return bool(trigger_set & term_set)
