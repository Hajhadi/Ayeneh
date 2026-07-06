"""SELF-02 Identity Continuity Engine.

7-phase pipeline for constructing and maintaining an IdentityObject:

1. HistoricalSelfModel — retrieve or create a historical identity baseline
2. CurrentSelfModel — build or retrieve the current self-model
3. ContinuityAnalysis — analyze continuity between historical and current identity
4. ConsistencyEvaluation — evaluate consistency across identity dimensions
5. IdentityRevision — determine if identity needs revision
6. HistoricalPreservation — preserve identity history for lineage tracking
7. UpdatedIdentityGraph — assemble and return the updated IdentityObject
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.self_arch.identity_continuity.types import (
    IdentityConfidence,
    IdentityObject,
    STABLE_IDENTITY_COMPONENTS,
)

logger = structlog.get_logger(__name__)

# Default identity characteristics
_DEFAULT_PRINCIPLES: tuple[str, ...] = (
    'evidence_first_reasoning',
    'transparency',
    'explainability',
    'respect_for_uncertainty',
    'ethical_governance',
)

_DEFAULT_STABLE: tuple[str, ...] = (
    'evidence_first_reasoning',
    'transparency',
    'explainability',
    'respect_for_uncertainty',
    'ethical_governance',
)

_DEFAULT_ADAPTIVE: tuple[str, ...] = (
    'communication_style',
    'problem_solving_approach',
    'tool_selection_strategy',
    'response_depth_calibration',
)

_DEFAULT_EVIDENCE: tuple[str, ...] = (
    'pipeline_architecture_consistency',
    'module_interaction_patterns',
    'consistent_value_alignment_across_turns',
)

_DEFAULT_REVIEW_POINTS: tuple[str, ...] = (
    'after_major_architecture_change',
    'after_new_module_integration',
    'periodic_quarterly_review',
)


class IdentityContinuityEngine:
    """Constructs and maintains an IdentityObject through a 7-phase pipeline (SELF-02)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._revision_count: int = 0
        self._current_identity: IdentityObject | None = None
        self._identity_lineage: list[dict[str, Any]] = []

    @property
    def current_identity(self) -> IdentityObject | None:
        """Return the current identity object."""
        return self._current_identity

    @property
    def revision_count(self) -> int:
        """Return the number of revisions made."""
        return self._revision_count

    def build(
        self,
        core_principles: tuple[str, ...] | None = None,
        stable_characteristics: tuple[str, ...] | None = None,
        adaptive_characteristics: tuple[str, ...] | None = None,
        prior_identity: IdentityObject | None = None,
    ) -> IdentityObject:
        """Run the full 7-phase identity continuity pipeline."""
        logger.info('self02_pipeline_start')

        # Phase 1 — HistoricalSelfModel
        historical = self._phase_historical_self_model(prior_identity)

        # Phase 2 — CurrentSelfModel
        current = self._phase_current_self_model(
            core_principles, stable_characteristics, adaptive_characteristics,
        )

        # Phase 3 — ContinuityAnalysis
        continuity_score, continuity_evidence = self._phase_continuity_analysis(
            historical, current,
        )

        # Phase 4 — ConsistencyEvaluation
        consistency_score, consistency_evidence = self._phase_consistency_evaluation(
            current,
        )

        # Phase 5 — IdentityRevision
        revision_needed, revision_description = self._phase_identity_revision(
            continuity_score, consistency_score,
        )

        # Phase 6 — HistoricalPreservation
        self._phase_historical_preservation(current, revision_description)

        # Phase 7 — UpdatedIdentityGraph
        identity = self._phase_updated_identity_graph(
            current, continuity_score, consistency_score,
            continuity_evidence, consistency_evidence,
        )

        self._current_identity = identity
        logger.info(
            'self02_pipeline_end',
            identity_id=identity.identity_id,
            confidence=identity.confidence,
        )
        return identity

    # ------------------------------------------------------------------
    # Phase 1 — HistoricalSelfModel
    # ------------------------------------------------------------------

    def _phase_historical_self_model(
        self, prior_identity: IdentityObject | None,
    ) -> dict[str, Any]:
        """Retrieve or create a historical identity baseline."""
        if prior_identity is not None:
            logger.debug(
                'phase_1_historical_self_model',
                prior_id=prior_identity.identity_id,
                prior_version=prior_identity.identity_version,
            )
            return {
                'identity_id': prior_identity.identity_id,
                'version': prior_identity.identity_version,
                'principles': prior_identity.core_principles,
                'stable': prior_identity.stable_characteristics,
                'adaptive': prior_identity.adaptive_characteristics,
                'confidence': prior_identity.confidence,
                'exists': True,
            }

        logger.debug('phase_1_historical_self_model', exists=False)
        return {
            'identity_id': '',
            'version': '',
            'principles': (),
            'stable': (),
            'adaptive': (),
            'confidence': 0.0,
            'exists': False,
        }

    # ------------------------------------------------------------------
    # Phase 2 — CurrentSelfModel
    # ------------------------------------------------------------------

    def _phase_current_self_model(
        self,
        core_principles: tuple[str, ...] | None,
        stable_characteristics: tuple[str, ...] | None,
        adaptive_characteristics: tuple[str, ...] | None,
    ) -> dict[str, Any]:
        """Build or retrieve the current self-model."""
        principles = core_principles if core_principles is not None else _DEFAULT_PRINCIPLES
        stable = stable_characteristics if stable_characteristics is not None else _DEFAULT_STABLE
        adaptive = adaptive_characteristics if adaptive_characteristics is not None else _DEFAULT_ADAPTIVE

        logger.debug(
            'phase_2_current_self_model',
            principle_count=len(principles),
            stable_count=len(stable),
            adaptive_count=len(adaptive),
        )
        return {
            'principles': principles,
            'stable': stable,
            'adaptive': adaptive,
        }

    # ------------------------------------------------------------------
    # Phase 3 — ContinuityAnalysis
    # ------------------------------------------------------------------

    def _phase_continuity_analysis(
        self,
        historical: dict[str, Any],
        current: dict[str, Any],
    ) -> tuple[float, tuple[str, ...]]:
        """Analyze continuity between historical and current identity."""
        if not historical.get('exists', False):
            # First-time identity — full continuity with defaults
            return 1.0, ('initial_identity_creation',)

        old_principles = set(historical.get('principles', ()))
        new_principles = set(current.get('principles', ()))
        old_stable = set(historical.get('stable', ()))
        new_stable = set(current.get('stable', ()))

        evidence: list[str] = []

        # Principle continuity
        if old_principles:
            principle_overlap = len(old_principles & new_principles) / max(
                len(old_principles | new_principles), 1,
            )
        else:
            principle_overlap = 1.0

        # Stable characteristic continuity
        if old_stable:
            stable_overlap = len(old_stable & new_stable) / max(
                len(old_stable | new_stable), 1,
            )
        else:
            stable_overlap = 1.0

        overall = (principle_overlap + stable_overlap) / 2.0

        if principle_overlap > 0.8:
            evidence.append('high_principle_continuity')
        elif principle_overlap > 0.5:
            evidence.append('moderate_principle_continuity')
        else:
            evidence.append('low_principle_continuity')

        if stable_overlap > 0.8:
            evidence.append('high_stable_characteristic_continuity')
        else:
            evidence.append('moderate_stable_characteristic_continuity')

        logger.debug(
            'phase_3_continuity_analysis',
            score=overall,
            evidence_count=len(evidence),
        )
        return round(overall, 4), tuple(evidence)

    # ------------------------------------------------------------------
    # Phase 4 — ConsistencyEvaluation
    # ------------------------------------------------------------------

    def _phase_consistency_evaluation(
        self, current: dict[str, Any],
    ) -> tuple[float, tuple[str, ...]]:
        """Evaluate consistency across identity dimensions."""
        evidence: list[str] = []
        scores: list[float] = []

        principles = current.get('principles', ())
        stable = current.get('stable', ())

        # Check if stable characteristics are a subset of or overlap with principles
        principle_set = set(principles)
        stable_set = set(stable)

        if principle_set and stable_set:
            overlap = len(principle_set & stable_set)
            consistency = overlap / max(len(stable_set), 1)
            scores.append(consistency)
            if consistency > 0.8:
                evidence.append('principle_stable_alignment_high')
            else:
                evidence.append('principle_stable_alignment_moderate')
        else:
            scores.append(0.5)
            evidence.append('insufficient_data_for_alignment_check')

        # Check for all stable components present
        all_present = all(
            comp in stable_set for comp in STABLE_IDENTITY_COMPONENTS
        )
        scores.append(1.0 if all_present else 0.5)
        evidence.append(
            'all_stable_components_present' if all_present
            else 'some_stable_components_missing'
        )

        overall = sum(scores) / max(len(scores), 1)

        logger.debug(
            'phase_4_consistency_evaluation',
            score=overall,
            evidence_count=len(evidence),
        )
        return round(overall, 4), tuple(evidence)

    # ------------------------------------------------------------------
    # Phase 5 — IdentityRevision
    # ------------------------------------------------------------------

    def _phase_identity_revision(
        self,
        continuity_score: float,
        consistency_score: float,
    ) -> tuple[bool, str]:
        """Determine if identity needs revision."""
        # Revision needed if either score drops below threshold
        threshold = 0.5
        needs_revision = continuity_score < threshold or consistency_score < threshold

        if needs_revision:
            description = (
                f'Revision triggered: continuity={continuity_score:.2f}, '
                f'consistency={consistency_score:.2f}'
            )
            self._revision_count += 1
        else:
            description = (
                f'No revision needed: continuity={continuity_score:.2f}, '
                f'consistency={consistency_score:.2f}'
            )

        logger.debug(
            'phase_5_identity_revision',
            needs_revision=needs_revision,
            revision_count=self._revision_count,
        )
        return needs_revision, description

    # ------------------------------------------------------------------
    # Phase 6 — HistoricalPreservation
    # ------------------------------------------------------------------

    def _phase_historical_preservation(
        self,
        current: dict[str, Any],
        revision_description: str,
    ) -> None:
        """Preserve identity history for lineage tracking."""
        entry = {
            'timestamp': datetime.now(UTC).isoformat(),
            'principles': current.get('principles', ()),
            'stable': current.get('stable', ()),
            'adaptive': current.get('adaptive', ()),
            'revision_description': revision_description,
            'revision_number': self._revision_count,
        }
        self._identity_lineage.append(entry)

        logger.debug(
            'phase_6_historical_preservation',
            lineage_length=len(self._identity_lineage),
        )

    # ------------------------------------------------------------------
    # Phase 7 — UpdatedIdentityGraph
    # ------------------------------------------------------------------

    def _phase_updated_identity_graph(
        self,
        current: dict[str, Any],
        continuity_score: float,
        consistency_score: float,
        continuity_evidence: tuple[str, ...],
        consistency_evidence: tuple[str, ...],
    ) -> IdentityObject:
        """Assemble and return the updated IdentityObject."""
        overall_confidence = round(
            (continuity_score + consistency_score) / 2.0, 4,
        )

        version = f'1.0.{self._revision_count + 1}'

        revision_entry = {
            'version': version,
            'timestamp': datetime.now(UTC).isoformat(),
            'change_description': f'Identity update at revision {self._revision_count + 1}',
            'change_type': 'continuity_update',
            'confidence_before': continuity_score,
            'confidence_after': overall_confidence,
        }

        explainability = {
            'reasoning_chain': [
                f'Continuity score: {continuity_score:.2f}',
                f'Consistency score: {consistency_score:.2f}',
                f'Core principles: {len(current.get("principles", ()))}',
                f'Stable characteristics: {len(current.get("stable", ()))}',
                f'Adaptive characteristics: {len(current.get("adaptive", ()))}',
            ],
            'evidence_summary': (
                f'Identity maintained with continuity={continuity_score:.2f} '
                f'and consistency={consistency_score:.2f}'
            ),
            'uncertainty_disclosures': [
                f'Overall confidence: {overall_confidence:.2f}',
            ],
        }

        identity = IdentityObject(
            identity_id=str(uuid.uuid4()),
            identity_version=version,
            core_principles=current.get('principles', ()),
            stable_characteristics=current.get('stable', ()),
            adaptive_characteristics=current.get('adaptive', ()),
            historical_lineage=tuple(self._identity_lineage[-10:]),
            revision_history=(revision_entry,),
            confidence=overall_confidence,
            supporting_evidence=continuity_evidence + consistency_evidence,
            known_tensions=(),
            future_review_points=_DEFAULT_REVIEW_POINTS,
            explainability_metadata=explainability,
        )

        logger.debug(
            'phase_7_updated_identity_graph',
            identity_id=identity.identity_id,
            confidence=identity.confidence,
        )
        return identity
