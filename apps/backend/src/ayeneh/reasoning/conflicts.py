"""Conflict detection — identifies disagreements across cognitive sources."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.reasoning.types import Conflict, Evidence, EvidenceSource

logger = structlog.get_logger(__name__)


class ConflictDetector:
    """Detects conflicts between evidence items from different sources."""

    SIMILARITY_THRESHOLD = 0.7
    CONTRADICTION_KEYWORDS = [
        ("not", "is"), ("never", "always"), ("avoid", "pursue"),
        ("increase", "decrease"), ("improve", "worsen"),
        ("start", "stop"), ("begin", "end"),
    ]

    def detect(self, evidence: list[Evidence]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        by_source: dict[str, list[Evidence]] = {}
        for e in evidence:
            by_source.setdefault(e.source_type, []).append(e)

        for source_type, items in by_source.items():
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    conflict = self._check_pair(items[i], items[j], source_type)
                    if conflict:
                        conflicts.append(conflict)

        for source_a, items_a in by_source.items():
            for source_b, items_b in by_source.items():
                if source_a >= source_b:
                    continue
                for a in items_a:
                    for b in items_b:
                        conflict = self._check_cross_source(a, b)
                        if conflict:
                            conflicts.append(conflict)

        logger.info("conflicts_detected", count=len(conflicts))
        return conflicts

    def _check_pair(self, a: Evidence, b: Evidence, source_type: str) -> Conflict | None:
        sim = self._word_overlap(a.content, b.content)
        if sim < 0.3:
            return None
        if self._has_negation_shift(a.content, b.content):
            return Conflict(
                conflict_type="contradiction",
                description=f"Conflicting statements from {source_type}: '{a.content[:100]}' vs '{b.content[:100]}'",
                evidence_a=a.id, evidence_b=b.id,
                source_a=source_type, source_b=source_type,
                severity=min(1.0, 1.0 - sim + 0.3),
            )
        return None

    def _check_cross_source(self, a: Evidence, b: Evidence) -> Conflict | None:
        sim = self._word_overlap(a.content, b.content)
        if sim < 0.3:
            return None
        if self._has_negation_shift(a.content, b.content):
            return Conflict(
                conflict_type="cross_source_contradiction",
                description=f"Contradiction between {a.source_type} and {b.source_type}: '{a.content[:80]}' vs '{b.content[:80]}'",
                evidence_a=a.id, evidence_b=b.id,
                source_a=a.source_type, source_b=b.source_type,
                severity=min(1.0, 1.0 - sim + 0.4),
            )
        return None

    @staticmethod
    def _word_overlap(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    @staticmethod
    def _has_negation_shift(a: str, b: str) -> bool:
        negations = {"not", "never", "no", "don't", "doesn't", "didn't", "won't", "can't", "stop"}
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        neg_a = bool(words_a & negations)
        neg_b = bool(words_b & negations)
        return neg_a != neg_b
