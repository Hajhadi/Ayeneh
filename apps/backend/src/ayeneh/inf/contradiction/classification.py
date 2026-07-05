"""INF-04 Conflict Classifier.

Classifies conflicts between cognitive objects by severity, category,
scope, and estimated impact.
"""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.inf.contradiction.types import (
    CONTRADICTION_CATEGORIES,
    CONTRADICTION_SEVERITY_LEVELS,
    ConflictClassification,
)

logger = structlog.get_logger(__name__)

# Severity thresholds (score → level)
_SEVERITY_THRESHOLDS: list[tuple[float, str]] = [
    (0.8, 'critical'),
    (0.6, 'major'),
    (0.4, 'moderate'),
    (0.2, 'minor'),
    (0.0, 'negligible'),
]


class ConflictClassifier:
    """Classifies a conflict between two cognitive objects."""

    def classify(self, obj_a: Any, obj_b: Any) -> dict[str, Any]:
        """Return a full classification dict for the conflict between two objects."""
        severity = self._compute_severity(obj_a, obj_b)
        category = self._determine_category(obj_a, obj_b)
        scope = self._determine_scope(obj_a, obj_b)
        identity_impact = self._estimate_identity_impact(obj_a, obj_b)
        behavioral_impact = self._estimate_behavioral_impact(obj_a, obj_b)
        severity_label = self._severity_to_label(severity)

        classification = ConflictClassification(
            category=category,
            severity=severity_label,
            scope=scope,
            identity_impact=identity_impact,
            behavioral_impact=behavioral_impact,
        )
        logger.debug(
            'conflict_classified',
            category=category,
            severity=severity_label,
            scope=scope,
        )
        return {
            'classification': classification,
            'category': category,
            'severity': severity,
            'severity_label': severity_label,
            'scope': scope,
            'identity_impact': identity_impact,
            'behavioral_impact': behavioral_impact,
        }

    # ------------------------------------------------------------------
    # Severity
    # ------------------------------------------------------------------

    def _compute_severity(self, obj_a: Any, obj_b: Any) -> float:
        score = 0.0
        conf_a = getattr(obj_a, 'confidence', 0.0)
        conf_b = getattr(obj_b, 'confidence', 0.0)
        score += abs(conf_a - conf_b) * 0.3

        type_a = getattr(obj_a, 'inference_type', '') or getattr(obj_a, 'conflict_type', '')
        type_b = getattr(obj_b, 'inference_type', '') or getattr(obj_b, 'conflict_type', '')
        if type_a == type_b and type_a:
            score += 0.2

        evid_a = getattr(obj_a, 'supporting_evidence', ()) or ()
        evid_b = getattr(obj_b, 'supporting_evidence', ()) or ()
        total = len(evid_a) + len(evid_b)
        if total > 0:
            balance = abs(len(evid_a) - len(evid_b)) / total
            score += balance * 0.2

        if type_a in ('identity', 'belief'):
            score += 0.2
        elif type_a in ('goal', 'planning'):
            score += 0.1

        if getattr(obj_a, 'current_status', '') == 'validated' and getattr(obj_b, 'current_status', '') == 'validated':
            score += 0.1

        return min(1.0, max(0.0, score))

    def _severity_to_label(self, severity: float) -> str:
        for threshold, label in _SEVERITY_THRESHOLDS:
            if severity >= threshold:
                return label
        return 'negligible'

    # ------------------------------------------------------------------
    # Category
    # ------------------------------------------------------------------

    def _determine_category(self, obj_a: Any, obj_b: Any) -> str:
        type_a = getattr(obj_a, 'inference_type', '') or ''
        type_b = getattr(obj_b, 'inference_type', '') or ''
        for t in (type_a, type_b):
            if t in CONTRADICTION_CATEGORIES:
                return t
        attrs_a = set(getattr(obj_a, '__dict__', {}).keys())
        attrs_b = set(getattr(obj_b, '__dict__', {}).keys())
        common = attrs_a & attrs_b
        if 'belief' in str(common):
            return 'belief'
        if 'narrative' in str(common):
            return 'narrative'
        return 'behavior'

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------

    def _determine_scope(self, obj_a: Any, obj_b: Any) -> str:
        type_a = getattr(obj_a, 'inference_type', '') or getattr(obj_a, 'conflict_type', '')
        type_b = getattr(obj_b, 'inference_type', '') or getattr(obj_b, 'conflict_type', '')
        global_types = {'identity', 'belief', 'narrative', 'meta_cognitive'}
        if type_a in global_types or type_b in global_types:
            return 'global'
        return 'local'

    # ------------------------------------------------------------------
    # Impact estimates
    # ------------------------------------------------------------------

    def _estimate_identity_impact(self, obj_a: Any, obj_b: Any) -> float:
        type_a = getattr(obj_a, 'inference_type', '') or getattr(obj_a, 'conflict_type', '')
        type_b = getattr(obj_b, 'inference_type', '') or getattr(obj_b, 'conflict_type', '')
        if type_a == 'identity' or type_b == 'identity':
            return 1.0
        if type_a == 'belief' or type_b == 'belief':
            return 0.6
        return 0.2

    def _estimate_behavioral_impact(self, obj_a: Any, obj_b: Any) -> float:
        type_a = getattr(obj_a, 'inference_type', '') or getattr(obj_a, 'conflict_type', '')
        type_b = getattr(obj_b, 'inference_type', '') or getattr(obj_b, 'conflict_type', '')
        if type_a == 'behavior' or type_b == 'behavior':
            return 1.0
        if type_a in ('goal', 'planning') or type_b in ('goal', 'planning'):
            return 0.7
        return 0.3
