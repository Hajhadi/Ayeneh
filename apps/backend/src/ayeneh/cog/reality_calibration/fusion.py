"""Cognitive Fusion Detection for COG-15 Reality Calibration.

Detects the degree to which thoughts, narratives, and beliefs become
fused with identity and lost as observable mental events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# FusionResult
# ---------------------------------------------------------------------------

OBJECT_TYPES: list[str] = [
    'thought', 'narrative', 'belief', 'prediction', 'emotion', 'identity',
]


@dataclass(frozen=True)
class FusionResult:
    """Degree of cognitive fusion for a single object.

    Fusion is the loss of perspective — when a mental event is experienced
    as literal reality rather than a cognitive process.
    """

    object_id: str
    object_type: str  # thought|narrative|belief|prediction|emotion|identity
    fusion_level: float = 0.0  # 0.0=fully observed, 1.0=fully fused
    evidence: tuple[str, ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# CognitiveFusionDetector
# ---------------------------------------------------------------------------

class CognitiveFusionDetector:
    """Detects fusion between identity and cognitive content (beliefs, narratives)."""

    def detect(
        self,
        identity: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> list[FusionResult]:
        """Detect cognitive fusion in identity-linked content.

        Returns a list of FusionResult objects, one per fused entity.
        """
        results: list[FusionResult] = []

        for item in identity:
            fusion_level = self._compute_identity_fusion(item)
            if fusion_level > 0.0:
                results.append(FusionResult(
                    object_id=item.get('identifier', ''),
                    object_type='identity',
                    fusion_level=fusion_level,
                    evidence=self._extract_evidence_refs(item),
                ))

        for item in narratives:
            fusion_level = self._compute_narrative_fusion(item)
            if fusion_level > 0.0:
                results.append(FusionResult(
                    object_id=item.get('identifier', ''),
                    object_type='narrative',
                    fusion_level=fusion_level,
                    evidence=self._extract_evidence_refs(item),
                ))

        for item in beliefs:
            fusion_level = self._compute_belief_fusion(item)
            if fusion_level > 0.0:
                results.append(FusionResult(
                    object_id=item.get('identifier', ''),
                    object_type='belief',
                    fusion_level=fusion_level,
                    evidence=self._extract_evidence_refs(item),
                ))

        logger.info('cog.reality_calibration.fusion_detected', count=len(results))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_identity_fusion(item: dict[str, Any]) -> float:
        """Higher confidence + high centrality → more fusion."""
        confidence = item.get('confidence', 0.0)
        centrality = item.get('centrality', 0.0)
        identification = item.get('narrative_identification_score', 0.0)
        return min(1.0, (confidence * 0.4 + centrality * 0.3 + identification * 0.3))

    @staticmethod
    def _compute_narrative_fusion(item: dict[str, Any]) -> float:
        influence = item.get('influence_score', 0.0)
        confidence = item.get('confidence', 0.0)
        core_assumptions = len(item.get('core_assumptions', ()))
        assumption_factor = min(1.0, core_assumptions * 0.2)
        return min(1.0, (influence * 0.4 + confidence * 0.3 + assumption_factor * 0.3))

    @staticmethod
    def _compute_belief_fusion(item: dict[str, Any]) -> float:
        strength = item.get('strength', 0.0)
        identity_coupling = item.get('identity_coupling_score', 0.0)
        influence = item.get('influence', 0.0)
        return min(1.0, (strength * 0.3 + identity_coupling * 0.4 + influence * 0.3))

    @staticmethod
    def _extract_evidence_refs(item: dict[str, Any]) -> tuple[str, ...]:
        refs: list[str] = []
        for key in ('supporting_evidence', 'contradictory_evidence', 'evidence'):
            refs.extend(item.get(key, ()))
        return tuple(refs)


# ---------------------------------------------------------------------------
# NarrativeFusionDetector
# ---------------------------------------------------------------------------

class NarrativeFusionDetector:
    """Detects fusion between narratives and observed reality."""

    def detect(
        self,
        narratives: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> list[FusionResult]:
        """Detect narrative-level fusion based on evidence support.

        Returns FusionResult for each narrative that shows signs of fusion.
        """
        results: list[FusionResult] = []
        evidence_ids = {e.get('identifier', '') for e in evidence}

        for narr in narratives:
            fusion_level = self._compute_fusion(narr, evidence_ids)
            if fusion_level > 0.0:
                results.append(FusionResult(
                    object_id=narr.get('identifier', ''),
                    object_type='narrative',
                    fusion_level=fusion_level,
                    evidence=self._extract_evidence_refs(narr),
                ))

        logger.info('cog.reality_calibration.narrative_fusion_detected', count=len(results))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_fusion(
        narr: dict[str, Any],
        evidence_ids: set[str],
    ) -> float:
        """Narrative with high influence but low evidence grounding → fused."""
        influence = narr.get('influence_score', 0.0)
        confidence = narr.get('confidence', 0.0)

        supporting = narr.get('supporting_evidence', ())
        contradictory = narr.get('contradictory_evidence', ())
        supported_count = sum(1 for e in supporting if e in evidence_ids)
        contradicted_count = sum(1 for e in contradictory if e in evidence_ids)

        total_evidence = supported_count + contradicted_count
        if total_evidence == 0:
            evidence_ratio = 0.0
        else:
            evidence_ratio = supported_count / total_evidence

        # High influence + low evidence grounding → high fusion
        return min(1.0, influence * 0.5 + confidence * 0.2 + (1.0 - evidence_ratio) * 0.3)

    @staticmethod
    def _extract_evidence_refs(item: dict[str, Any]) -> tuple[str, ...]:
        refs: list[str] = []
        for key in ('supporting_evidence', 'contradictory_evidence', 'evidence'):
            refs.extend(item.get(key, ()))
        return tuple(refs)
