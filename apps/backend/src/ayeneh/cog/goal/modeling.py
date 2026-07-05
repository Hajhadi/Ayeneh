"""Goal Modeling Engine — COG-08.

Identifies, models, and updates intentional structures from
evidence, values, and beliefs.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.goal.planning import PlanningStructure
from ayeneh.cog.goal.types import (
    GOAL_CATEGORIES,
    GoalObject,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoalModelingResult:
    """Output of the COG-08 pipeline."""

    goals: tuple[GoalObject, ...]
    network: dict[str, Any]
    total_extracted: int
    by_category: dict[str, int]
    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Candidate detection heuristics
# ---------------------------------------------------------------------------

_GOAL_KEYWORDS: list[str] = [
    'want to', 'need to', 'plan to', 'goal', 'aim',
    'intend', 'working toward', 'strive', 'objective',
    'target', 'deadline', 'project',
]

_EVIDENCE_CATEGORY_TO_GOAL_CATEGORY: dict[str, str] = {
    'self_report': 'personal_growth',
    'identity_statement': 'personal_growth',
    'value_statement': 'personal_growth',
    'relationship_report': 'relationship',
    'behavioral_report': 'project',
    'emotional_report': 'personal_growth',
    'observation': 'learning',
    'meta_cognitive_report': 'learning',
}


# ---------------------------------------------------------------------------
# GoalModelingEngine
# ---------------------------------------------------------------------------


class GoalModelingEngine:
    """Identifies, models, and updates intentional structures (COG-08).

    Pipeline phases:
        1. Preferences → Repeated Intention → Goal Candidates
        2. Validation
        3. Compute Metrics — priority, commitment, persistence
        4. Build Network — dependencies and hierarchy
    """

    def __init__(self) -> None:
        self._goals: dict[str, GoalObject] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence_objects: list[dict[str, Any]],
        values: list[dict[str, Any]] | None = None,
        beliefs: list[dict[str, Any]] | None = None,
    ) -> GoalModelingResult:
        """Run the full COG-08 pipeline."""
        logger.info(
            'cog.goal.pipeline_started',
            evidence_count=len(evidence_objects),
            value_count=len(values) if values else 0,
            belief_count=len(beliefs) if beliefs else 0,
        )

        values = values or []
        beliefs = beliefs or []

        # Phase 1 — Detect goal candidates
        candidates = self._detect_candidates(evidence_objects, values, beliefs)

        # Phase 2 — Validate
        validated = self._validate(candidates)

        # Phase 3 — Compute metrics
        scored = self._compute_metrics(validated, evidence_objects)

        # Phase 4 — Build network
        network = self._build_network(scored)

        result = GoalModelingResult(
            goals=tuple(scored),
            network=network,
            total_extracted=len(scored),
            by_category=self._count_by_category(scored),
        )

        logger.info(
            'cog.goal.pipeline_completed',
            total_extracted=result.total_extracted,
            by_category=result.by_category,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Detect goal candidates
    # ------------------------------------------------------------------

    def _detect_candidates(
        self,
        evidence_objects: list[dict[str, Any]],
        values: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> list[GoalObject]:
        """Detect goal candidates from repeated intentions."""
        candidates: list[GoalObject] = []
        seen: dict[str, str] = {}

        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', ev.get('normalized_text', '')))
            if not text or not self._looks_goal_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen:
                continue

            category = self._infer_category(ev)
            gid = str(uuid.uuid4())
            seen[normalised] = gid

            candidates.append(GoalObject(
                identifier=gid,
                goal_statement=text,
                category=category,
                supporting_evidence=(ev.get('identifier', ''),),
            ))

        for val in values:
            text = val.get('statement', val.get('text', ''))
            if not text or not self._looks_goal_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen:
                continue

            category = self._infer_category(val)
            gid = str(uuid.uuid4())
            seen[normalised] = gid

            candidates.append(GoalObject(
                identifier=gid,
                goal_statement=text,
                category=category,
                associated_values=(val.get('identifier', ''),),
            ))

        for belief in beliefs:
            text = belief.get('statement', belief.get('text', ''))
            if not text or not self._looks_goal_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen:
                continue

            category = self._infer_category(belief)
            gid = str(uuid.uuid4())
            seen[normalised] = gid

            candidates.append(GoalObject(
                identifier=gid,
                goal_statement=text,
                category=category,
                associated_beliefs=(belief.get('identifier', ''),),
            ))

        logger.info('cog.goal.candidates_detected', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: list[GoalObject]) -> list[GoalObject]:
        """Validate goal candidates."""
        validated: list[GoalObject] = []
        for g in candidates:
            if not g.goal_statement.strip():
                continue
            if g.category not in GOAL_CATEGORIES:
                continue
            validated.append(GoalObject(
                identifier=g.identifier,
                goal_statement=g.goal_statement,
                category=g.category,
                confidence=g.confidence,
                priority=g.priority,
                commitment_strength=g.commitment_strength,
                progress=g.progress,
                persistence=g.persistence,
                flexibility=g.flexibility,
                supporting_evidence=g.supporting_evidence,
                behavioural_evidence=g.behavioural_evidence,
                associated_values=g.associated_values,
                associated_beliefs=g.associated_beliefs,
                associated_narratives=g.associated_narratives,
                dependencies=g.dependencies,
                milestones=g.milestones,
                lifecycle_state='provisional',
            ))
        logger.info('cog.goal.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 3: Compute metrics
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        validated: list[GoalObject],
        evidence_objects: list[dict[str, Any]],
    ) -> list[GoalObject]:
        """Compute priority, commitment, persistence, and confidence."""
        scored: list[GoalObject] = []
        for g in validated:
            evidence_count = self._count_supporting_evidence(g, evidence_objects)
            confidence = min(1.0, evidence_count * 0.2)
            priority = min(1.0, evidence_count * 0.18)
            commitment = min(1.0, evidence_count * 0.15 + 0.1)
            persistence = min(1.0, evidence_count * 0.1)
            flexibility = 0.5  # default moderate flexibility

            scored.append(GoalObject(
                identifier=g.identifier,
                goal_statement=g.goal_statement,
                category=g.category,
                confidence=confidence,
                priority=priority,
                commitment_strength=commitment,
                progress=g.progress,
                persistence=persistence,
                flexibility=flexibility,
                supporting_evidence=g.supporting_evidence,
                behavioural_evidence=g.behavioural_evidence,
                associated_values=g.associated_values,
                associated_beliefs=g.associated_beliefs,
                associated_narratives=g.associated_narratives,
                dependencies=g.dependencies,
                milestones=g.milestones,
                lifecycle_state=g.lifecycle_state,
            ))
        logger.info('cog.goal.metrics_computed', count=len(scored))
        return scored

    # ------------------------------------------------------------------
    # Phase 4: Build network
    # ------------------------------------------------------------------

    @staticmethod
    def _build_network(goals: list[GoalObject]) -> dict[str, Any]:
        """Build a goal network with dependencies and shared categories."""
        nodes = {g.identifier: g.goal_statement for g in goals}
        edges: list[dict[str, Any]] = []

        # Direct dependency edges
        for g in goals:
            for dep_id in g.dependencies:
                if dep_id in nodes:
                    edges.append({
                        'source': dep_id,
                        'target': g.identifier,
                        'relationship': 'depends_on',
                    })

        # Same-category clustering
        same_category: dict[str, list[str]] = {}
        for g in goals:
            same_category.setdefault(g.category, []).append(g.identifier)

        for cat, ids in same_category.items():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    edges.append({
                        'source': ids[i],
                        'target': ids[j],
                        'relationship': 'supports',
                    })

        return {'nodes': nodes, 'edges': edges}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_goal_like(text: str) -> bool:
        """Return True if text contains goal-indicating keywords."""
        lower = text.lower()
        return any(kw in lower for kw in _GOAL_KEYWORDS)

    @staticmethod
    def _infer_category(ev: dict[str, Any]) -> str:
        """Infer a goal category from evidence metadata."""
        ev_type = ev.get('type', ev.get('category', ''))
        return _EVIDENCE_CATEGORY_TO_GOAL_CATEGORY.get(ev_type, 'personal_growth')

    @staticmethod
    def _count_supporting_evidence(
        goal: GoalObject,
        evidence_objects: list[dict[str, Any]],
    ) -> int:
        """Count evidence objects that share keywords with the goal statement."""
        keywords = set(goal.goal_statement.lower().split())
        count = 0
        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', '')).lower()
            ev_words = set(text.split())
            if keywords & ev_words:
                count += 1
        count += len(goal.supporting_evidence)
        return max(count, 1)

    @staticmethod
    def _count_by_category(goals: list[GoalObject]) -> dict[str, int]:
        """Count goals per category."""
        counter: Counter[str] = Counter()
        for g in goals:
            counter[g.category] += 1
        return dict(counter)
