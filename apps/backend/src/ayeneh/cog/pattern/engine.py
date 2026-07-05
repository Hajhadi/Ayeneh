"""Behavioral Pattern Engine — COG-11.

Discovers stable recurring cognitive/behavioral regularities from evidence,
decisions, and behaviors. Detects sequences, patterns, behavioral loops,
fractal structures, and meta-patterns.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.pattern.detection import (
    FractalDetector,
    LoopDetector,
    RecursiveDetector,
)
from ayeneh.cog.pattern.types import (
    BehavioralLoop,
    MetaPattern,
    PatternObject,
    PatternResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Behavioral Pattern Engine
# ---------------------------------------------------------------------------


class BehavioralPatternEngine:
    """Discovers stable recurring cognitive/behavioral regularities (COG-11).

    Pipeline:
        1. Sequence Detection — identify repeated behavioral sequences
        2. Pattern Extraction — extract candidate patterns from sequences
        3. Validation — filter and validate candidate patterns
        4. Loop Detection — detect closed behavioral/cognitive loops
        5. Meta-Pattern Detection — find cross-domain meta-patterns
    """

    def __init__(self) -> None:
        self._patterns: dict[str, PatternObject] = {}
        self._loops: dict[str, BehavioralLoop] = {}
        self._loop_detector = LoopDetector()
        self._fractal_detector = FractalDetector()
        self._recursive_detector = RecursiveDetector()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[dict[str, str]],
        decisions: list[dict[str, str]] | None = None,
        behaviors: list[dict[str, str]] | None = None,
    ) -> PatternResult:
        """Run the full COG-11 pipeline.

        Parameters
        ----------
        evidence:
            List of evidence dicts with ``'text'``, ``'id'``, and optional
            ``'category'`` keys.
        decisions:
            List of decision dicts with ``'text'`` and ``'id'`` keys.
        behaviors:
            List of behavior dicts with ``'text'`` and ``'id'`` keys.
        """
        logger.info('cog.pattern.pipeline_started', evidence_count=len(evidence))

        decisions = decisions or []
        behaviors = behaviors or []

        # Phase 1 — Sequence Detection
        sequences = self._detect_sequences(evidence, decisions, behaviors)

        # Phase 2 — Pattern Extraction
        candidates = self._extract_patterns(sequences)

        # Phase 3 — Validation
        validated = self._validate(candidates)

        # Phase 4 — Loop Detection
        loops = self._detect_loops(validated)

        # Phase 5 — Meta-Pattern Detection
        meta = self._detect_meta_patterns(validated)

        # Store patterns
        for p in validated.values():
            self._patterns[p.identifier] = p
        for loop in loops.values():
            self._loops[loop.loop_id] = loop

        lifecycle_summary: dict[str, int] = {}
        for p in validated.values():
            lifecycle_summary[p.lifecycle_state] = (
                lifecycle_summary.get(p.lifecycle_state, 0) + 1
            )

        result = PatternResult(
            patterns=validated,
            loops=loops,
            meta_patterns=meta,
            total_extracted=len(validated),
            lifecycle_summary=lifecycle_summary,
        )

        logger.info(
            'cog.pattern.pipeline_completed',
            total_extracted=result.total_extracted,
            loops_found=len(loops),
            meta_patterns_found=len(meta),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Sequence Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_sequences(
        evidence: list[dict[str, str]],
        decisions: list[dict[str, str]],
        behaviors: list[dict[str, str]],
    ) -> list[list[dict[str, str]]]:
        """Detect repeated sequences across evidence, decisions, behaviors."""
        all_items = evidence + decisions + behaviors

        # Group by category
        category_groups: dict[str, list[dict[str, str]]] = {}
        for item in all_items:
            cat = item.get('category', 'general')
            category_groups.setdefault(cat, []).append(item)

        # Sequences are groups with 2+ items
        sequences = [
            items for items in category_groups.values() if len(items) >= 2
        ]

        logger.info('cog.pattern.sequences_detected', count=len(sequences))
        return sequences

    # ------------------------------------------------------------------
    # Phase 2: Pattern Extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_patterns(
        sequences: list[list[dict[str, str]]],
    ) -> dict[str, PatternObject]:
        """Extract candidate patterns from sequences."""
        patterns: dict[str, PatternObject] = {}

        for seq in sequences:
            if not seq:
                continue

            # Determine pattern type from category
            category = seq[0].get('category', 'general')
            pattern_type = BehavioralPatternEngine._infer_pattern_type(category)

            # Build description from text samples
            texts = [item.get('text', '') for item in seq[:3]]
            description = f"Recurring pattern ({pattern_type}): {'; '.join(t for t in texts if t)}"

            # Build supporting references
            evidence_ids = tuple(
                item.get('id', '') for item in seq if item.get('id')
            )
            contexts = tuple(
                item.get('category', '') for item in seq if item.get('category')
            )

            # Compute consistency: ratio of items with same category
            total = len(seq)
            same_cat = sum(
                1 for item in seq if item.get('category', 'general') == category
            )
            consistency = same_cat / total if total > 0 else 0.0

            comp = PatternObject(
                identifier=str(uuid.uuid4()),
                pattern_description=description,
                pattern_type=pattern_type,
                frequency=total,
                consistency=consistency,
                confidence=min(1.0, total * 0.15),
                stability=min(1.0, consistency * 0.8),
                influence=consistency * 0.5,
                contexts=contexts,
                supporting_evidence=evidence_ids,
                lifecycle_state='candidate',
            )
            patterns[comp.identifier] = comp

        logger.info('cog.pattern.candidates_extracted', count=len(patterns))
        return patterns

    # ------------------------------------------------------------------
    # Phase 3: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: dict[str, PatternObject]) -> dict[str, PatternObject]:
        """Validate and filter candidate patterns."""
        validated: dict[str, PatternObject] = {}

        for comp in candidates.values():
            # Minimum frequency threshold
            if comp.frequency < 2:
                continue

            # Advance lifecycle
            if comp.confidence >= 0.3 and comp.consistency >= 0.5:
                state = 'validated'
            elif comp.confidence >= 0.2:
                state = 'emerging'
            else:
                state = 'candidate'

            validated[comp.identifier] = PatternObject(
                identifier=comp.identifier,
                pattern_description=comp.pattern_description,
                pattern_type=comp.pattern_type,
                frequency=comp.frequency,
                consistency=comp.consistency,
                confidence=comp.confidence,
                stability=comp.stability,
                influence=comp.influence,
                trigger_conditions=comp.trigger_conditions,
                termination_conditions=comp.termination_conditions,
                contexts=comp.contexts,
                supporting_behaviors=comp.supporting_behaviors,
                supporting_decisions=comp.supporting_decisions,
                supporting_evidence=comp.supporting_evidence,
                associated_narratives=comp.associated_narratives,
                associated_beliefs=comp.associated_beliefs,
                associated_values=comp.associated_values,
                associated_goals=comp.associated_goals,
                lifecycle_state=state,
                creation_timestamp=comp.creation_timestamp,
            )

        logger.info('cog.pattern.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 4: Loop Detection
    # ------------------------------------------------------------------

    def _detect_loops(
        self, patterns: dict[str, PatternObject],
    ) -> dict[str, BehavioralLoop]:
        """Detect closed behavioral/cognitive loops from patterns."""
        pattern_list = list(patterns.values())
        loops = self._loop_detector.detect_behavioral_loops(pattern_list)
        cognitive_loops = self._loop_detector.detect_cognitive_loops(pattern_list)

        all_loops = loops + cognitive_loops
        loop_map = {loop.loop_id: loop for loop in all_loops}

        logger.info('cog.pattern.loops_detected', count=len(loop_map))
        return loop_map

    # ------------------------------------------------------------------
    # Phase 5: Meta-Pattern Detection
    # ------------------------------------------------------------------

    def _detect_meta_patterns(
        self, patterns: dict[str, PatternObject],
    ) -> dict[str, MetaPattern]:
        """Detect cross-domain meta-patterns."""
        pattern_list = list(patterns.values())
        meta_patterns: dict[str, MetaPattern] = {}

        # Group patterns by type
        type_groups: dict[str, list[PatternObject]] = {}
        for p in pattern_list:
            type_groups.setdefault(p.pattern_type, []).append(p)

        # Create meta-patterns for types with 2+ patterns
        for ptype, group in type_groups.items():
            if len(group) < 2:
                continue

            pattern_ids = tuple(p.identifier for p in group)
            avg_confidence = sum(p.confidence for p in group) / len(group)

            # Compute cross-domain similarity
            similarity = self._fractal_detector.compute_cross_scale_similarity(
                group[0], group[1] if len(group) > 1 else group[0],
            )

            meta = MetaPattern(
                pattern_id=str(uuid.uuid4()),
                description=f"Meta-pattern across {len(group)} {ptype} patterns",
                domain_patterns=pattern_ids,
                confidence=avg_confidence,
                similarity_score=similarity,
            )
            meta_patterns[meta.pattern_id] = meta

        logger.info('cog.pattern.meta_patterns_detected', count=len(meta_patterns))
        return meta_patterns

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_pattern_type(category: str) -> str:
        """Infer pattern type from evidence category."""
        type_map: dict[str, str] = {
            'behavioral_report': 'behavioral_loop',
            'self_report': 'cognitive_loop',
            'decision_report': 'behavioral_loop',
            'narrative_report': 'cognitive_loop',
            'meta_cognitive_report': 'recursive',
            'identity_statement': 'cognitive_loop',
        }
        return type_map.get(category, 'behavioral_loop')
