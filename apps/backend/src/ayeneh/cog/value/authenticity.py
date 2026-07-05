"""Authenticity Estimator — COG-07 support.

Distinguishes declared values (self-report) from observed values
(behavioural evidence) and estimates alignment.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AuthenticityEstimator:
    """Estimates alignment between declared and observed values.

    Classification thresholds:
        alignment > 0.7  → 'aligned'
        alignment < 0.3  → 'misaligned'
        otherwise        → 'partial'
    """

    def estimate(
        self,
        value: Any,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Estimate alignment between declared and observed values.

        Parameters
        ----------
        value:
            A value-like object (dict or dataclass) with a ``value_statement``
            attribute or key.
        evidence:
            List of evidence dicts, each with a ``type`` field.

        Returns
        -------
        dict with keys: declared_count, behavioural_count, alignment_score,
        classification.
        """
        value_text = self._get_value_text(value).lower()

        declared_evidence = [
            e for e in evidence if e.get('type') == 'self_report'
        ]
        behavioural_evidence = [
            e for e in evidence if e.get('type') == 'behavioral_report'
        ]

        alignment = self._compute_alignment(
            value_text, declared_evidence, behavioural_evidence,
        )

        if alignment > 0.7:
            classification = 'aligned'
        elif alignment < 0.3:
            classification = 'misaligned'
        else:
            classification = 'partial'

        logger.info(
            'cog.value.authenticity_estimated',
            alignment_score=round(alignment, 3),
            classification=classification,
        )

        return {
            'declared_count': len(declared_evidence),
            'behavioural_count': len(behavioural_evidence),
            'alignment_score': alignment,
            'classification': classification,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _get_value_text(value: Any) -> str:
        """Extract the value statement from an object or dict."""
        if isinstance(value, dict):
            return value.get('value_statement', value.get('statement', ''))
        return getattr(value, 'value_statement', getattr(value, 'statement', ''))

    @staticmethod
    def _compute_alignment(
        value_text: str,
        declared_evidence: list[dict[str, Any]],
        behavioural_evidence: list[dict[str, Any]],
    ) -> float:
        """Compute alignment score between declared and observed evidence.

        If both declared and behavioural evidence exist and share keywords
        with the value statement, alignment is high.  Absence of either
        type reduces the score.
        """
        value_words = set(value_text.split())

        def _overlap(evidence: list[dict[str, Any]]) -> float:
            if not evidence:
                return 0.0
            hits = 0
            for e in evidence:
                text = e.get('text', e.get('original_text', '')).lower()
                ev_words = set(text.split())
                if value_words & ev_words:
                    hits += 1
            return hits / len(evidence) if evidence else 0.0

        declared_overlap = _overlap(declared_evidence)
        behavioural_overlap = _overlap(behavioural_evidence)

        if not declared_evidence and not behavioural_evidence:
            return 0.5  # no evidence → neutral

        if not declared_evidence:
            return behavioural_overlap * 0.4

        if not behavioural_evidence:
            return declared_overlap * 0.5

        return (declared_overlap + behavioural_overlap) / 2.0
