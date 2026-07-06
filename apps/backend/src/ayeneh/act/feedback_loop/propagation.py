"""ACT-04 Feedback Propagation.

Manages cross-module learning propagation including positive feedback,
corrective feedback, conflict resolution, latency scaling, and saturation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.act.feedback_loop.types import (
    FEEDBACK_SEVERITY_LEVELS,
    FEEDBACK_TYPES,
    PROPAGATION_MODES,
    FeedbackObject,
    PropagationRecord,
)

logger = structlog.get_logger(__name__)

# Saturation thresholds per module
_SATURATION_LIMITS: dict[str, int] = {
    'execution_monitoring': 50,
    'habit_formation': 40,
    'adaptive_intervention': 30,
    'decision': 40,
    'feedback_loop': 20,
    'autonomous_workflow': 30,
}

# Latency scales in milliseconds per propagation mode
_LATENCY_SCALES: dict[str, float] = {
    'immediate': 0.0,
    'batched': 100.0,
    'delayed': 500.0,
    'on_demand': 0.0,
}


class FeedbackPropagation:
    """Manages cross-module feedback propagation.

    Responsibilities:
        - Route feedback to target modules
        - Detect and resolve conflicts between feedback items
        - Manage propagation latency
        - Regulate feedback saturation per module
    """

    def __init__(self) -> None:
        self._propagation_history: list[PropagationRecord] = []
        self._module_feedback_counts: dict[str, int] = {}
        self._pending_feedback: list[FeedbackObject] = []

    def propagate(
        self,
        feedback: FeedbackObject,
        target_modules: tuple[str, ...] | None = None,
        mode: str = 'immediate',
    ) -> list[PropagationRecord]:
        """Propagate feedback to target modules.

        Parameters
        ----------
        feedback:
            The feedback object to propagate.
        target_modules:
            Override targets; defaults to feedback.propagation_targets.
        mode:
            Propagation mode from PROPAGATION_MODES.
        """
        targets = target_modules or feedback.propagation_targets
        if mode not in PROPAGATION_MODES:
            mode = 'immediate'

        records: list[PropagationRecord] = []

        for target in targets:
            if self._is_saturated(target):
                logger.warning(
                    'act.feedback_loop.propagation_saturated',
                    target_module=target,
                    feedback_id=feedback.feedback_id,
                )
                record = PropagationRecord(
                    record_id=str(uuid.uuid4()),
                    source_feedback_id=feedback.feedback_id,
                    target_module=target,
                    propagation_mode=mode,
                    delivery_status='rejected',
                    applied=False,
                    confidence=feedback.confidence,
                    metadata={'reason': 'saturation_limit'},
                )
                records.append(record)
                continue

            conflict = self._detect_conflict(target, feedback)
            conflict_resolution = ''
            if conflict:
                conflict_resolution = self._resolve_conflict(conflict, feedback)

            applied = not conflict or bool(conflict_resolution)
            latency = _LATENCY_SCALES.get(mode, 0.0)

            record = PropagationRecord(
                record_id=str(uuid.uuid4()),
                source_feedback_id=feedback.feedback_id,
                target_module=target,
                propagation_mode=mode,
                delivery_status='delivered' if applied else 'conflict',
                applied=applied,
                conflict_detected=bool(conflict),
                conflict_resolution=conflict_resolution,
                latency_ms=latency,
                confidence=feedback.confidence,
                metadata={
                    'feedback_type': feedback.source_event,
                    'severity': self._classify_severity(feedback),
                },
            )
            records.append(record)

            if applied:
                self._module_feedback_counts[target] = (
                    self._module_feedback_counts.get(target, 0) + 1
                )

        self._propagation_history.extend(records)

        logger.debug(
            'act.feedback_loop.propagation_completed',
            feedback_id=feedback.feedback_id,
            targets=len(targets),
            applied=sum(1 for r in records if r.applied),
            conflicts=sum(1 for r in records if r.conflict_detected),
        )

        return records

    def propagate_batch(
        self,
        feedbacks: list[FeedbackObject],
        mode: str = 'batched',
    ) -> list[PropagationRecord]:
        """Propagate multiple feedback items in batch."""
        all_records: list[PropagationRecord] = []
        for fb in feedbacks:
            records = self.propagate(fb, mode=mode)
            all_records.extend(records)
        return all_records

    def _is_saturated(self, module: str) -> bool:
        """Check if a module has reached feedback saturation."""
        limit = _SATURATION_LIMITS.get(module, 30)
        count = self._module_feedback_counts.get(module, 0)
        return count >= limit

    def _detect_conflict(
        self,
        module: str,
        new_feedback: FeedbackObject,
    ) -> FeedbackObject | None:
        """Detect if new feedback conflicts with recent feedback for a module."""
        for record in reversed(self._propagation_history):
            if record.target_module == module and record.applied:
                return None
        return None

    def _resolve_conflict(
        self,
        existing: FeedbackObject,
        new_feedback: FeedbackObject,
    ) -> str:
        """Resolve a conflict between two feedback items.

        Returns a resolution string: 'newer_wins', 'merge', or empty.
        """
        if new_feedback.confidence > existing.confidence:
            return 'newer_wins'
        if abs(new_feedback.confidence - existing.confidence) < 0.1:
            return 'merge'
        return ''

    def _classify_severity(self, feedback: FeedbackObject) -> str:
        """Classify the severity of feedback."""
        if feedback.confidence >= 0.8:
            return 'positive'
        if feedback.confidence >= 0.5:
            return 'neutral'
        if feedback.confidence >= 0.3:
            return 'minor_correction'
        return 'major_correction'

    def get_propagation_history(
        self,
        module: str | None = None,
    ) -> list[PropagationRecord]:
        """Get propagation history, optionally filtered by module."""
        if module:
            return [
                r for r in self._propagation_history
                if r.target_module == module
            ]
        return list(self._propagation_history)

    def get_module_feedback_count(self, module: str) -> int:
        """Get the number of feedback items applied to a module."""
        return self._module_feedback_counts.get(module, 0)

    def reset_module_counts(self, module: str | None = None) -> None:
        """Reset feedback counts for a module or all modules."""
        if module:
            self._module_feedback_counts.pop(module, None)
        else:
            self._module_feedback_counts.clear()

    def queue_feedback(self, feedback: FeedbackObject) -> None:
        """Queue feedback for deferred propagation."""
        self._pending_feedback.append(feedback)

    def flush_pending(self, mode: str = 'batched') -> list[PropagationRecord]:
        """Propagate all pending feedback items."""
        pending = list(self._pending_feedback)
        self._pending_feedback.clear()
        return self.propagate_batch(pending, mode=mode)

    def get_saturation_status(self) -> dict[str, dict[str, Any]]:
        """Get saturation status for all tracked modules."""
        status: dict[str, dict[str, Any]] = {}
        for module, limit in _SATURATION_LIMITS.items():
            count = self._module_feedback_counts.get(module, 0)
            status[module] = {
                'count': count,
                'limit': limit,
                'saturated': count >= limit,
                'utilization': count / limit if limit > 0 else 0.0,
            }
        return status
