"""Value Modeling Engine — COG-07.

Identifies enduring principles and priorities from longitudinal
evidence and belief streams.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.value.authenticity import AuthenticityEstimator
from ayeneh.cog.value.types import (
    LIFECYCLE_STATES,
    VALUE_CATEGORIES,
    ValueObject,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValueModelingResult:
    """Output of the COG-07 pipeline."""

    values: tuple[ValueObject, ...]
    total_extracted: int
    by_category: dict[str, int]
    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Candidate detection heuristics
# ---------------------------------------------------------------------------

_VALUE_KEYWORDS: list[str] = [
    'value', 'important', 'matter', 'care about', 'principle',
    'priority', 'fundamental', 'essential', 'meaningful',
    'what counts', 'guide', 'compass', 'worth',
]

_EVIDENCE_CATEGORY_TO_VALUE_CATEGORY: dict[str, str] = {
    'self_report': 'authenticity',
    'identity_statement': 'growth',
    'value_statement': 'justice',
    'relationship_report': 'relationship',
    'behavioral_report': 'achievement',
    'emotional_report': 'authenticity',
    'observation': 'knowledge',
    'meta_cognitive_report': 'growth',
}


# ---------------------------------------------------------------------------
# ValueModelingEngine
# ---------------------------------------------------------------------------


class ValueModelingEngine:
    """Identifies enduring principles and priorities (COG-07).

    Pipeline phases:
        1. Repeated Choices → Value Candidates
        2. Validation
        3. Compute Metrics — stability, priority, influence
        4. Authenticity Estimation — declared vs observed
    """

    def __init__(self) -> None:
        self._values: dict[str, ValueObject] = {}
        self._authenticity = AuthenticityEstimator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence_objects: list[dict[str, Any]],
        beliefs: list[dict[str, Any]] | None = None,
    ) -> ValueModelingResult:
        """Run the full COG-07 pipeline."""
        logger.info(
            'cog.value.pipeline_started',
            evidence_count=len(evidence_objects),
            belief_count=len(beliefs) if beliefs else 0,
        )

        beliefs = beliefs or []

        # Phase 1 — Detect value candidates
        candidates = self._detect_candidates(evidence_objects, beliefs)

        # Phase 2 — Validate
        validated = self._validate(candidates)

        # Phase 3 — Compute metrics
        scored = self._compute_metrics(validated, evidence_objects)

        result = ValueModelingResult(
            values=tuple(scored),
            total_extracted=len(scored),
            by_category=self._count_by_category(scored),
        )

        logger.info(
            'cog.value.pipeline_completed',
            total_extracted=result.total_extracted,
            by_category=result.by_category,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Detect value candidates
    # ------------------------------------------------------------------

    def _detect_candidates(
        self,
        evidence_objects: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> list[ValueObject]:
        """Detect value candidates from repeated evidence and beliefs."""
        candidates: list[ValueObject] = []
        seen: dict[str, str] = {}

        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', ev.get('normalized_text', '')))
            if not text or not self._looks_value_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen:
                continue

            category = self._infer_category(ev)
            vid = str(uuid.uuid4())
            seen[normalised] = vid

            candidates.append(ValueObject(
                identifier=vid,
                value_statement=text,
                category=category,
                supporting_evidence=(ev.get('identifier', ''),),
            ))

        for belief in beliefs:
            text = belief.get('statement', belief.get('text', ''))
            if not text or not self._looks_value_like(text):
                continue

            normalised = text.lower().strip()
            if normalised in seen:
                continue

            category = self._infer_category(belief)
            vid = str(uuid.uuid4())
            seen[normalised] = vid

            candidates.append(ValueObject(
                identifier=vid,
                value_statement=text,
                category=category,
                associated_beliefs=(belief.get('identifier', ''),),
            ))

        logger.info('cog.value.candidates_detected', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: list[ValueObject]) -> list[ValueObject]:
        """Validate value candidates."""
        validated: list[ValueObject] = []
        for v in candidates:
            if not v.value_statement.strip():
                continue
            if v.category not in VALUE_CATEGORIES:
                continue
            validated.append(ValueObject(
                identifier=v.identifier,
                value_statement=v.value_statement,
                category=v.category,
                confidence=v.confidence,
                stability=v.stability,
                priority=v.priority,
                influence=v.influence,
                supporting_evidence=v.supporting_evidence,
                behavioural_evidence=v.behavioural_evidence,
                contradictory_evidence=v.contradictory_evidence,
                associated_beliefs=v.associated_beliefs,
                associated_goals=v.associated_goals,
                associated_narratives=v.associated_narratives,
                associated_identity_components=v.associated_identity_components,
                declared_vs_observed=v.declared_vs_observed,
                lifecycle_state='provisional',
            ))
        logger.info('cog.value.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 3: Compute metrics
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        validated: list[ValueObject],
        evidence_objects: list[dict[str, Any]],
    ) -> list[ValueObject]:
        """Compute stability, priority, influence, and confidence."""
        scored: list[ValueObject] = []
        for v in validated:
            evidence_count = self._count_supporting_evidence(v, evidence_objects)
            confidence = min(1.0, evidence_count * 0.2)
            stability = min(1.0, evidence_count * 0.15 + 0.1)
            priority = min(1.0, evidence_count * 0.18)
            influence = min(1.0, evidence_count * 0.12)

            scored.append(ValueObject(
                identifier=v.identifier,
                value_statement=v.value_statement,
                category=v.category,
                confidence=confidence,
                stability=stability,
                priority=priority,
                influence=influence,
                supporting_evidence=v.supporting_evidence,
                behavioural_evidence=v.behavioural_evidence,
                contradictory_evidence=v.contradictory_evidence,
                associated_beliefs=v.associated_beliefs,
                associated_goals=v.associated_goals,
                associated_narratives=v.associated_narratives,
                associated_identity_components=v.associated_identity_components,
                declared_vs_observed=v.declared_vs_observed,
                lifecycle_state=v.lifecycle_state,
            ))
        logger.info('cog.value.metrics_computed', count=len(scored))
        return scored

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_value_like(text: str) -> bool:
        """Return True if text contains value-indicating keywords."""
        lower = text.lower()
        return any(kw in lower for kw in _VALUE_KEYWORDS)

    @staticmethod
    def _infer_category(ev: dict[str, Any]) -> str:
        """Infer a value category from evidence metadata."""
        ev_type = ev.get('type', ev.get('category', ''))
        return _EVIDENCE_CATEGORY_TO_VALUE_CATEGORY.get(ev_type, 'growth')

    @staticmethod
    def _count_supporting_evidence(
        value: ValueObject,
        evidence_objects: list[dict[str, Any]],
    ) -> int:
        """Count evidence objects that share keywords with the value statement."""
        keywords = set(value.value_statement.lower().split())
        count = 0
        for ev in evidence_objects:
            text = ev.get('text', ev.get('original_text', '')).lower()
            ev_words = set(text.split())
            if keywords & ev_words:
                count += 1
        count += len(value.supporting_evidence)
        return max(count, 1)

    @staticmethod
    def _count_by_category(values: list[ValueObject]) -> dict[str, int]:
        """Count values per category."""
        counter: Counter[str] = Counter()
        for v in values:
            counter[v.category] += 1
        return dict(counter)
