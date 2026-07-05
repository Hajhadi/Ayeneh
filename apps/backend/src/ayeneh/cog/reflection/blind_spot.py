"""Blind Spot Detector — COG-12 support module.

Detects cognitive structures that influence behavior but remain absent from
the user's explicit awareness. Uses behavioral consistency, narrative recurrence,
cross-context appearance, and lack of explicit recognition as signals.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.cog.reflection.types import BlindSpot

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Blind Spot Detector
# ---------------------------------------------------------------------------


class BlindSpotDetector:
    """Detects recurring cognitive structures absent from explicit awareness.

    A blind spot exists when:
    1. A behavioral pattern is consistent across contexts
    2. The pattern recurs in narratives
    3. The pattern appears across multiple contexts
    4. The user has not explicitly recognized or articulated it
    """

    def detect(
        self,
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[BlindSpot]:
        """Detect recurring structures influencing behavior absent from explicit awareness.

        Parameters
        ----------
        evidence:
            List of evidence dicts with ``'text'``, ``'id'``, and optional
            ``'category'`` keys.
        patterns:
            List of pattern dicts with ``'id'``, ``'description'``, and
            ``'frequency'`` keys.
        identity:
            List of identity dicts with ``'id'``, ``'statement'``, and
            optional ``'domain'`` keys.
        """
        logger.info('cog.reflection.blind_spot_detection_started')

        blind_spots: list[BlindSpot] = []

        # Extract behavioral evidence (non-self-report)
        behavioral_evidence = [
            ev for ev in evidence
            if ev.get('category', '') in ('behavioral_report', 'decision_report')
        ]

        # Extract self-reports for recognition comparison
        self_reports = [
            ev for ev in evidence
            if ev.get('category', '') in ('self_report', 'identity_statement')
        ]

        # Extract identity statements for recognition
        identity_statements = {
            stmt.get('statement', '').lower()
            for stmt in identity
            if stmt.get('statement')
        }

        # Group behavioral evidence by implied theme
        theme_groups = _group_by_theme(behavioral_evidence)

        for theme, group in theme_groups.items():
            if len(group) < 2:
                continue

            # Check behavioral consistency
            behavioral_consistency = _compute_consistency(group)

            # Check narrative recurrence
            narrative_recurrence = _compute_narrative_recurrence(
                theme, self_reports,
            )

            # Check cross-context appearance
            cross_context = _compute_cross_context(group)

            # Check lack of explicit recognition
            recognition_score = _compute_lack_of_recognition(
                theme, identity_statements,
            )

            # A blind spot requires: high behavioral consistency + low recognition
            if behavioral_consistency >= 0.3 and recognition_score >= 0.5:
                impact = _estimate_impact(
                    behavioral_consistency, narrative_recurrence,
                    cross_context, recognition_score,
                )
                evidence_ids = tuple(ev.get('id', '') for ev in group)

                bs = BlindSpot(
                    identifier=str(uuid.uuid4()),
                    description=f"Unrecognized behavioral theme: {theme}",
                    estimated_impact=impact,
                    evidence=evidence_ids,
                    behavioral_consistency=behavioral_consistency,
                    narrative_recurrence=narrative_recurrence,
                    cross_context_appearance=cross_context,
                    lack_of_explicit_recognition=recognition_score,
                )
                blind_spots.append(bs)

        logger.info(
            'cog.reflection.blind_spots_detected',
            count=len(blind_spots),
        )
        return blind_spots


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _group_by_theme(
    evidence: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group behavioral evidence by inferred thematic similarity."""
    groups: dict[str, list[dict[str, Any]]] = {}

    for ev in evidence:
        text = ev.get('text', '').lower()
        words = set(text.split())
        stop_words = {
            'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'it', 'this', 'that', 'and',
            'or', 'but', 'not', 'my', 'me', 'we', 'our',
        }
        meaningful = words - stop_words

        # Use first meaningful word as theme key (simple heuristic)
        if meaningful:
            theme = sorted(meaningful)[0]
        else:
            theme = 'general'

        groups.setdefault(theme, []).append(ev)

    return groups


def _compute_consistency(group: list[dict[str, Any]]) -> float:
    """Compute behavioral consistency within a group of evidence."""
    if len(group) < 2:
        return 0.0

    # Consistency based on category agreement
    categories = [ev.get('category', 'general') for ev in group]
    if not categories:
        return 0.0

    from collections import Counter
    cat_counts = Counter(categories)
    most_common_count = cat_counts.most_common(1)[0][1]
    return most_common_count / len(categories)


def _compute_narrative_recurrence(
    theme: str,
    self_reports: list[dict[str, Any]],
) -> float:
    """Check how often the theme appears in self-reports."""
    if not self_reports:
        return 0.0

    theme_words = set(theme.lower().split())
    matches = 0
    for report in self_reports:
        report_words = set(report.get('text', '').lower().split())
        if theme_words & report_words:
            matches += 1

    return min(1.0, matches / len(self_reports))


def _compute_cross_context(group: list[dict[str, Any]]) -> float:
    """Compute how many distinct contexts the behavior appears in."""
    contexts = {ev.get('category', 'general') for ev in group}
    # Normalize: 1 context = 0.0, 2 = 0.5, 3+ = 1.0
    if len(contexts) <= 1:
        return 0.0
    elif len(contexts) == 2:
        return 0.5
    return 1.0


def _compute_lack_of_recognition(
    theme: str,
    identity_statements: set[str],
) -> float:
    """Compute how absent the theme is from explicit identity statements."""
    if not identity_statements:
        return 1.0  # No identity statements = no recognition

    theme_words = set(theme.lower().split())
    for stmt in identity_statements:
        stmt_words = set(stmt.split())
        if theme_words & stmt_words:
            return 0.3  # Partial recognition

    return 1.0  # No recognition at all


def _estimate_impact(
    behavioral_consistency: float,
    narrative_recurrence: float,
    cross_context: float,
    recognition_lack: float,
) -> float:
    """Estimate the impact of a blind spot."""
    # Weighted combination
    return min(1.0, (
        behavioral_consistency * 0.3
        + narrative_recurrence * 0.2
        + cross_context * 0.2
        + recognition_lack * 0.3
    ))
