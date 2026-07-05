"""Identity Graph Engine — COG-09.

Models the evolving cognitive graph of self-understanding. Detects identity
components from evidence, validates them against beliefs/values/goals/narratives,
computes centrality and influence, builds a relational graph, and tracks the
observer-self capacity.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from ayeneh.cog.identity.coherence import IdentityCoherenceEstimator
from ayeneh.cog.identity.types import (
    IdentityComponent,
    IdentityGraph,
    IdentityResult,
    ObserverSelf,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Identity Graph Engine
# ---------------------------------------------------------------------------


class IdentityGraphEngine:
    """Models the evolving cognitive graph of self-understanding (COG-09).

    Pipeline:
        1. Candidate Detection — extract identity statements from evidence
        2. Validation — cross-check against beliefs, values, goals, narratives
        3. Metric Computation — confidence, stability, centrality, influence
        4. Graph Construction — build edges and compute network properties
        5. Coherence Estimation — structural consistency across subsystems
        6. Observer Update — update meta-cognitive observer-self capacity
    """

    def __init__(self) -> None:
        self._components: dict[str, IdentityComponent] = {}
        self._observer = ObserverSelf()
        self._coherence_estimator = IdentityCoherenceEstimator()

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
    ) -> IdentityResult:
        """Run the full COG-09 pipeline.

        Parameters
        ----------
        evidence:
            List of evidence dicts with at least ``'text'`` and ``'id'`` keys.
        beliefs, values, goals, narratives:
            Lists of string identifiers from upstream cognitive subsystems.
        """
        logger.info('cog.identity.pipeline_started', evidence_count=len(evidence))

        # Phase 1 — Candidate Detection
        candidates = self._detect_candidates(evidence, beliefs, values, goals, narratives)

        # Phase 2 — Validation
        validated = self._validate(candidates)

        # Phase 3 — Metric Computation
        scored = self._compute_metrics(validated, evidence)

        # Phase 4 — Graph Construction
        network = self._build_graph(scored)

        # Phase 5 — Coherence Estimation
        coherence = self._estimate_coherence(scored, beliefs, values, goals)

        # Phase 6 — Observer Update
        observer = self._update_observer(evidence)

        # Build result
        lifecycle_summary: dict[str, int] = {}
        for comp in scored.values():
            lifecycle_summary[comp.lifecycle_state] = (
                lifecycle_summary.get(comp.lifecycle_state, 0) + 1
            )

        result = IdentityResult(
            components=scored,
            graph=network,
            observer_self=observer,
            coherence_score=coherence,
            total_components=len(scored),
            lifecycle_summary=lifecycle_summary,
        )

        logger.info(
            'cog.identity.pipeline_completed',
            total_components=result.total_components,
            coherence=coherence,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Candidate Detection
    # ------------------------------------------------------------------

    def _detect_candidates(
        self,
        evidence: list[dict[str, str]],
        beliefs: list[str] | None,
        values: list[str] | None,
        goals: list[str] | None,
        narratives: list[str] | None,
    ) -> list[IdentityComponent]:
        """Extract identity component candidates from evidence."""
        candidates: list[IdentityComponent] = []
        beliefs = beliefs or []
        values = values or []
        goals = goals or []
        narratives = narratives or []

        for ev in evidence:
            text = ev.get('text', '')
            ev_id = ev.get('id', '')
            category = ev.get('category', '')

            # Only process identity-relevant evidence
            if not self._is_identity_relevant(text, category):
                continue

            comp = IdentityComponent(
                identifier=str(uuid.uuid4()),
                identity_statement=text,
                confidence=0.3,  # initial low confidence
                stability=0.1,
                centrality=0.0,
                influence=0.0,
                observer_strength=0.0,
                supporting_evidence=(ev_id,) if ev_id else (),
                lifecycle_state='candidate',
            )
            candidates.append(comp)

        logger.info('cog.identity.candidates_detected', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: list[IdentityComponent]) -> list[IdentityComponent]:
        """Validate candidates and advance lifecycle where appropriate."""
        validated: list[IdentityComponent] = []
        for c in candidates:
            if c.confidence >= 0.3 and len(c.supporting_evidence) > 0:
                # Advance to 'emerging'
                validated.append(IdentityComponent(
                    identifier=c.identifier,
                    identity_statement=c.identity_statement,
                    confidence=c.confidence,
                    stability=c.stability,
                    centrality=c.centrality,
                    influence=c.influence,
                    observer_strength=c.observer_strength,
                    supporting_evidence=c.supporting_evidence,
                    contradictory_evidence=c.contradictory_evidence,
                    supporting_beliefs=c.supporting_beliefs,
                    supporting_values=c.supporting_values,
                    supporting_goals=c.supporting_goals,
                    supporting_narratives=c.supporting_narratives,
                    narrative_identification_score=c.narrative_identification_score,
                    lifecycle_state='emerging',
                    creation_timestamp=c.creation_timestamp,
                    revision_history=c.revision_history,
                ))
            else:
                validated.append(c)
        return validated

    # ------------------------------------------------------------------
    # Phase 3: Metric Computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_metrics(
        components: list[IdentityComponent],
        evidence: list[dict[str, str]],
    ) -> dict[str, IdentityComponent]:
        """Compute confidence, stability, centrality, and influence."""
        scored: dict[str, IdentityComponent] = {}
        ev_count = max(len(evidence), 1)

        for comp in components:
            # Confidence: evidence density + cross-references
            evidence_ratio = len(comp.supporting_evidence) / ev_count
            cross_ref = (
                len(comp.supporting_beliefs)
                + len(comp.supporting_values)
                + len(comp.supporting_goals)
                + len(comp.supporting_narratives)
            )
            confidence = min(1.0, 0.3 + evidence_ratio * 0.4 + cross_ref * 0.05)

            # Stability: based on evidence count (more evidence → more stable)
            stability = min(1.0, len(comp.supporting_evidence) * 0.15)

            # Centrality: number of cross-references / total possible
            max_refs = 4  # beliefs, values, goals, narratives
            centrality = cross_ref / max_refs if max_refs > 0 else 0.0

            # Influence: weighted combination of centrality and confidence
            influence = centrality * 0.6 + confidence * 0.4

            scored[comp.identifier] = IdentityComponent(
                identifier=comp.identifier,
                identity_statement=comp.identity_statement,
                confidence=confidence,
                stability=stability,
                centrality=centrality,
                influence=influence,
                observer_strength=comp.observer_strength,
                supporting_evidence=comp.supporting_evidence,
                contradictory_evidence=comp.contradictory_evidence,
                supporting_beliefs=comp.supporting_beliefs,
                supporting_values=comp.supporting_values,
                supporting_goals=comp.supporting_goals,
                supporting_narratives=comp.supporting_narratives,
                narrative_identification_score=comp.narrative_identification_score,
                lifecycle_state=comp.lifecycle_state,
                creation_timestamp=comp.creation_timestamp,
                revision_history=comp.revision_history,
            )

        logger.info('cog.identity.metrics_computed', count=len(scored))
        return scored

    # ------------------------------------------------------------------
    # Phase 4: Graph Construction
    # ------------------------------------------------------------------

    def _build_graph(self, components: dict[str, IdentityComponent]) -> IdentityGraph:
        """Build relational edges between identity components."""
        edges: list[dict[str, str]] = []
        comp_list = list(components.values())

        for i, a in enumerate(comp_list):
            for b in comp_list[i + 1:]:
                edge = self._compute_edge(a, b)
                if edge is not None:
                    edges.append(edge)

        return IdentityGraph(
            components=components,
            edges=tuple(edges),
            observer_self=self._observer,
        )

    @staticmethod
    def _compute_edge(
        a: IdentityComponent,
        b: IdentityComponent,
    ) -> dict[str, str] | None:
        """Compute a single edge between two components, or None."""
        shared_beliefs = set(a.supporting_beliefs) & set(b.supporting_beliefs)
        shared_values = set(a.supporting_values) & set(b.supporting_values)
        shared_goals = set(a.supporting_goals) & set(b.supporting_goals)

        strength = (
            len(shared_beliefs) * 0.4
            + len(shared_values) * 0.3
            + len(shared_goals) * 0.3
        )

        if strength == 0:
            return None

        # Determine edge type
        contradictory = set(a.contradictory_evidence) & set(b.supporting_evidence)
        if contradictory:
            edge_type = 'contradiction'
        elif shared_values:
            edge_type = 'value_support'
        elif shared_goals:
            edge_type = 'goal_alignment'
        else:
            edge_type = 'belief_support'

        return {
            'source': a.identifier,
            'target': b.identifier,
            'edge_type': edge_type,
            'strength': str(round(strength, 4)),
        }

    # ------------------------------------------------------------------
    # Phase 5: Coherence Estimation
    # ------------------------------------------------------------------

    def _estimate_coherence(
        self,
        components: dict[str, IdentityComponent],
        beliefs: list[str] | None,
        values: list[str] | None,
        goals: list[str] | None,
    ) -> float:
        """Estimate overall coherence across cognitive subsystems."""
        return self._coherence_estimator.estimate(
            components, beliefs, values, goals,
        )

    # ------------------------------------------------------------------
    # Phase 6: Observer Update
    # ------------------------------------------------------------------

    def _update_observer(self, evidence: list[dict[str, str]]) -> ObserverSelf:
        """Update the observer-self based on meta-cognitive evidence."""
        meta_count = sum(
            1 for ev in evidence
            if ev.get('category', '') in ('meta_cognitive_report', 'identity_statement')
        )
        total = max(len(evidence), 1)
        meta_ratio = meta_count / total

        # Grow observer capacity based on meta-cognitive evidence
        new_episodes = self._observer.observation_episodes + meta_count
        avg_duration = (
            self._observer.average_episode_duration_s
            if self._observer.observation_episodes > 0
            else 30.0
        )

        confidence = min(1.0, self._observer.confidence + meta_ratio * 0.1)
        stability = min(1.0, self._observer.stability + meta_count * 0.02)
        de_id = min(1.0, self._observer.de_identification_level + meta_ratio * 0.05)

        self._observer = ObserverSelf(
            confidence=confidence,
            stability=stability,
            observation_episodes=new_episodes,
            average_episode_duration_s=avg_duration,
            de_identification_level=de_id,
        )

        logger.info(
            'cog.identity.observer_updated',
            episodes=new_episodes,
            de_identification=de_id,
        )
        return self._observer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_identity_relevant(text: str, category: str) -> bool:
        """Determine if evidence text/category is identity-relevant."""
        if category in ('identity_statement', 'self_report', 'narrative_report'):
            return True
        identity_keywords = (
            'i am', 'i always', 'i never', 'i believe', 'i value',
            'my goal', 'i think of myself', 'that is just how i',
            'i see myself', 'my identity', 'who i am',
        )
        text_lower = text.lower()
        return any(kw in text_lower for kw in identity_keywords)
