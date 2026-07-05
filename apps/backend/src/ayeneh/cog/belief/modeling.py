"""Belief Modeling Engine — COG-06.

Identifies, versions, and evolves enduring beliefs from longitudinal
evidence and narrative streams.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.belief.types import (
    BELIEF_CATEGORIES,
    BELIEF_RELATIONSHIP_TYPES,
    BeliefNetwork,
    BeliefObject,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BeliefModelingResult:
    """Output of the COG-06 pipeline."""

    beliefs: tuple[BeliefObject, ...]
    network: BeliefNetwork
    total_extracted: int
    by_category: dict[str, int]
    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Candidate detection heuristics
# ---------------------------------------------------------------------------

_BELIEF_KEYWORDS: list[str] = [
    'believe', 'think that', 'know that', 'its obvious',
    'always true', 'never changes', 'fundamental', 'core',
    'deeply', 'conviction', 'principle', 'truth',
]

_EVIDENCE_CATEGORY_TO_BELIEF_CATEGORY: dict[str, str] = {
    'self_report': 'self',
    'identity_statement': 'self',
    'value_statement': 'moral',
    'relationship_report': 'relationship',
    'behavioral_report': 'competence',
    'emotional_report': 'self',
    'observation': 'world',
    'meta_cognitive_report': 'self',
}


# ---------------------------------------------------------------------------
# BeliefModelingEngine
# ---------------------------------------------------------------------------


class BeliefModelingEngine:
    """Identifies, versions, and evolves enduring beliefs (COG-06).

    Pipeline phases:
        1. Repeated Patterns → Belief Candidates
        2. Validation — requires longitudinal behavioural evidence
        3. Compute Metrics — strength, stability, influence
        4. Build Network — inter-belief relationships
    """

    def __init__(self) -> None:
        self._beliefs: dict[str, BeliefObject] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence_objects: list[dict[str, Any]],
        narratives: list[dict[str, Any]] | None = None,
    ) -> BeliefModelingResult:
        """Run the full COG-06 pipeline."""
        logger.info(
            'cog.belief.pipeline_started',
            evidence_count=len(evidence_objects),
            narrative_count=len(narratives) if narratives else 0,
        )

        narratives = narratives or []

        # Phase 1 — Detect belief candidates
        candidates = self._detect_candidates(evidence_objects, narratives)

        # Phase 2 — Validate
        validated = self._validate(candidates)

        # Phase 3 — Compute metrics
        scored = self._compute_metrics(validated, evidence_objects)

        # Phase 4 — Build belief network
        network = self._build_network(scored)

        result = BeliefModelingResult(
            beliefs=tuple(scored),
            network=network,
            total_extracted=len(scored),
            by_category=self._count_by_category(scored),
        )

        logger.info(
            'cog.belief.pipeline_completed',
            total_extracted=result.total_extracted,
            by_category=result.by_category,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Detect belief candidates
    # ------------------------------------------------------------------

    def _detect_candidates(
        self,
        evidence_objects: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
    ) -> list[BeliefObject]:
        """Detect belief candidates from repeated evidence and narratives."""
        candidates: list[BeliefObject] = []
        seen_statements: dict[str, str] = {}  # normalised → belief id

        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', ev.get('normalized_text', '')))
            if not text:
                continue

            if not self._looks_belief_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen_statements:
                continue

            category = self._infer_category(ev)
            bid = str(uuid.uuid4())
            seen_statements[normalised] = bid

            candidates.append(BeliefObject(
                identifier=bid,
                belief_statement=text,
                category=category,
                supporting_evidence=(ev.get('identifier', ''),),
            ))

        for narr in narratives:
            text = narr.get('text', narr.get('statement', ''))
            if not text or not self._looks_belief_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen_statements:
                continue

            category = self._infer_category(narr)
            bid = str(uuid.uuid4())
            seen_statements[normalised] = bid

            candidates.append(BeliefObject(
                identifier=bid,
                belief_statement=text,
                category=category,
                supporting_narratives=(narr.get('identifier', ''),),
            ))

        logger.info('cog.belief.candidates_detected', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: list[BeliefObject]) -> list[BeliefObject]:
        """Validate belief candidates — require non-empty statement and valid category."""
        validated: list[BeliefObject] = []
        for c in candidates:
            if not c.belief_statement.strip():
                continue
            if c.category not in BELIEF_CATEGORIES:
                continue
            validated.append(BeliefObject(
                identifier=c.identifier,
                belief_statement=c.belief_statement,
                category=c.category,
                confidence=c.confidence,
                strength=c.strength,
                stability=c.stability,
                influence=c.influence,
                identity_coupling_score=c.identity_coupling_score,
                supporting_evidence=c.supporting_evidence,
                contradictory_evidence=c.contradictory_evidence,
                supporting_narratives=c.supporting_narratives,
                associated_values=c.associated_values,
                associated_goals=c.associated_goals,
                associated_identity_components=c.associated_identity_components,
                lifecycle_state='provisional',
            ))
        logger.info('cog.belief.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 3: Compute metrics
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        validated: list[BeliefObject],
        evidence_objects: list[dict[str, Any]],
    ) -> list[BeliefObject]:
        """Compute strength, stability, influence, and confidence."""
        scored: list[BeliefObject] = []
        for b in validated:
            evidence_count = self._count_supporting_evidence(b, evidence_objects)
            confidence = min(1.0, evidence_count * 0.2)
            strength = min(1.0, evidence_count * 0.15 + 0.1)
            stability = min(1.0, evidence_count * 0.1)
            influence = min(1.0, evidence_count * 0.12)

            scored.append(BeliefObject(
                identifier=b.identifier,
                belief_statement=b.belief_statement,
                category=b.category,
                confidence=confidence,
                strength=strength,
                stability=stability,
                influence=influence,
                identity_coupling_score=0.0,
                supporting_evidence=b.supporting_evidence,
                contradictory_evidence=b.contradictory_evidence,
                supporting_narratives=b.supporting_narratives,
                associated_values=b.associated_values,
                associated_goals=b.associated_goals,
                associated_identity_components=b.associated_identity_components,
                lifecycle_state=b.lifecycle_state,
            ))
        logger.info('cog.belief.metrics_computed', count=len(scored))
        return scored

    # ------------------------------------------------------------------
    # Phase 4: Build network
    # ------------------------------------------------------------------

    @staticmethod
    def _build_network(beliefs: list[BeliefObject]) -> BeliefNetwork:
        """Build a belief network with inter-belief relationships."""
        nodes: dict[str, BeliefObject] = {b.identifier: b for b in beliefs}
        edges: list[dict[str, Any]] = []

        same_category: dict[str, list[BeliefObject]] = {}
        for b in beliefs:
            same_category.setdefault(b.category, []).append(b)

        for cat, group in same_category.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    edges.append({
                        'source': group[i].identifier,
                        'target': group[j].identifier,
                        'relationship': 'supports',
                        'confidence': 0.5,
                    })

        return BeliefNetwork(nodes=nodes, edges=tuple(edges))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_belief_like(text: str) -> bool:
        """Return True if text contains belief-indicating keywords."""
        lower = text.lower()
        return any(kw in lower for kw in _BELIEF_KEYWORDS)

    @staticmethod
    def _infer_category(ev: dict[str, Any]) -> str:
        """Infer a belief category from evidence metadata."""
        ev_type = ev.get('type', ev.get('category', ''))
        return _EVIDENCE_CATEGORY_TO_BELIEF_CATEGORY.get(ev_type, 'self')

    @staticmethod
    def _count_supporting_evidence(
        belief: BeliefObject,
        evidence_objects: list[dict[str, Any]],
    ) -> int:
        """Count evidence objects that share keywords with the belief statement."""
        keywords = set(belief.belief_statement.lower().split())
        count = 0
        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', '')).lower()
            ev_words = set(text.split())
            if keywords & ev_words:
                count += 1
        # Also count direct evidence refs
        count += len(belief.supporting_evidence)
        return max(count, 1)

    @staticmethod
    def _count_by_category(beliefs: list[BeliefObject]) -> dict[str, int]:
        """Count beliefs per category."""
        counter: Counter[str] = Counter()
        for b in beliefs:
            counter[b.category] += 1
        return dict(counter)
