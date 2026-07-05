"""DLG-04 Reflection Trigger Detector.

Detects reflection opportunities from context signals:
- Behavioral pattern detection
- Narrative repetition detection
- Identity contradiction detection
- Reality distortion detection
- Developmental transition detection
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dlg.reflection.types import DetectedPattern

logger = structlog.get_logger(__name__)


class ReflectionTriggerDetector:
    """Detects reflection opportunities from cognitive context signals."""

    def detect(self, context: dict[str, Any] | None = None) -> list[DetectedPattern]:
        """Run all detection heuristics and return discovered patterns."""
        ctx = context or {}
        patterns: list[DetectedPattern] = []
        patterns.extend(self._detect_behavioral_patterns(ctx))
        patterns.extend(self._detect_narrative_repetition(ctx))
        patterns.extend(self._detect_identity_contradictions(ctx))
        patterns.extend(self._detect_reality_distortion(ctx))
        patterns.extend(self._detect_developmental_transitions(ctx))
        logger.debug('trigger_detection_complete', count=len(patterns))
        return patterns

    # ------------------------------------------------------------------
    # Behavioral pattern detection
    # ------------------------------------------------------------------

    def _detect_behavioral_patterns(self, ctx: dict[str, Any]) -> list[DetectedPattern]:
        patterns: list[DetectedPattern] = []
        behaviors = ctx.get('behavioral_patterns', [])
        if isinstance(behaviors, list):
            for b in behaviors:
                freq = b.get('frequency', 0) if isinstance(b, dict) else 0
                if freq >= 3:
                    patterns.append(DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='recurring_behavioral_pattern',
                        description=f"Behavior repeated {freq} times: {b.get('description', '')}",
                        frequency=freq,
                        strength=min(1.0, freq / 10.0),
                        evidence_count=freq,
                    ))
        return patterns

    # ------------------------------------------------------------------
    # Narrative repetition detection
    # ------------------------------------------------------------------

    def _detect_narrative_repetition(self, ctx: dict[str, Any]) -> list[DetectedPattern]:
        patterns: list[DetectedPattern] = []
        narratives = ctx.get('narratives', [])
        seen: dict[str, int] = {}
        if isinstance(narratives, list):
            for n in narratives:
                text = n.get('text', '') if isinstance(n, dict) else str(n)
                key = text[:50].lower()
                seen[key] = seen.get(key, 0) + 1
            for key, count in seen.items():
                if count >= 2:
                    patterns.append(DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='repeated_narrative',
                        description=f"Narrative repeated {count} times: '{key}...'",
                        frequency=count,
                        strength=min(1.0, count / 5.0),
                        evidence_count=count,
                    ))
        return patterns

    # ------------------------------------------------------------------
    # Identity contradiction detection
    # ------------------------------------------------------------------

    def _detect_identity_contradictions(self, ctx: dict[str, Any]) -> list[DetectedPattern]:
        patterns: list[DetectedPattern] = []
        identity_signals = ctx.get('identity_signals', [])
        if isinstance(identity_signals, list) and len(identity_signals) >= 2:
            types_seen = set()
            for sig in identity_signals:
                sig_type = sig.get('type', '') if isinstance(sig, dict) else ''
                if sig_type and sig_type in types_seen:
                    patterns.append(DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='identity_contradiction',
                        description=f"Contradictory identity signal: {sig_type}",
                        strength=0.7,
                        evidence_count=2,
                    ))
                    break
                types_seen.add(sig_type)
        return patterns

    # ------------------------------------------------------------------
    # Reality distortion detection
    # ------------------------------------------------------------------

    def _detect_reality_distortion(self, ctx: dict[str, Any]) -> list[DetectedPattern]:
        patterns: list[DetectedPattern] = []
        distortions = ctx.get('reality_distortions', [])
        if isinstance(distortions, list):
            for d in distortions:
                severity = d.get('severity', 0.0) if isinstance(d, dict) else 0.0
                if severity >= 0.5:
                    patterns.append(DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='reality_distortion',
                        description=f"Reality distortion detected: {d.get('description', '')}",
                        strength=severity,
                        evidence_count=1,
                    ))
        return patterns

    # ------------------------------------------------------------------
    # Developmental transition detection
    # ------------------------------------------------------------------

    def _detect_developmental_transitions(
        self, ctx: dict[str, Any],
    ) -> list[DetectedPattern]:
        patterns: list[DetectedPattern] = []
        transitions = ctx.get('developmental_signals', [])
        if isinstance(transitions, list):
            for t in transitions:
                if isinstance(t, dict) and t.get('is_transition', False):
                    patterns.append(DetectedPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='major_developmental_transition',
                        description=f"Developmental transition: {t.get('description', '')}",
                        strength=t.get('strength', 0.6),
                        evidence_count=1,
                    ))
        return patterns
