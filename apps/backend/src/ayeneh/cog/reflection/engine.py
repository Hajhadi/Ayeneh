"""Reflection Engine — COG-12.

Generates descriptive, evidence-based observations about cognitive structures.
Pipeline: Evidence → Patterns → Relationships → Longitudinal Analysis →
Candidates → Validation → Reflection.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.cog.reflection.awakening import AwakeningDynamics, AwakeningProgress
from ayeneh.cog.reflection.blind_spot import BlindSpotDetector
from ayeneh.cog.reflection.types import (
    GRANULARITY_LEVELS,
    LIFECYCLE_STATES,
    REFLECTION_SCOPES,
    BlindSpot,
    InsightObject,
    ReflectionObject,
    ReflectionResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Reflection Engine
# ---------------------------------------------------------------------------


class ReflectionEngine:
    """Generates descriptive, evidence-based observations about cognitive structures (COG-12).

    Pipeline:
        1. Relationship Analysis — cross-reference evidence, patterns, narratives, beliefs
        2. Longitudinal Analysis — detect temporal trends across evidence
        3. Candidate Generation — propose reflection candidates from analysis
        4. Validation — filter and refine candidates
        5. Blind Spot Detection — identify structures absent from awareness
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._reflections: dict[str, ReflectionObject] = {}
        self._insights: dict[str, InsightObject] = {}
        self._blind_spot_detector = BlindSpotDetector()
        self._awakening_dynamics = AwakeningDynamics()
        self._ai_router = ai_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]] | None = None,
        narratives: list[dict[str, Any]] | None = None,
        beliefs: list[dict[str, Any]] | None = None,
        identity: list[dict[str, Any]] | None = None,
    ) -> ReflectionResult:
        """Run the full COG-12 pipeline.

        Parameters
        ----------
        evidence:
            List of evidence dicts with ``'text'``, ``'id'``, and optional
            ``'category'`` keys.
        patterns:
            List of pattern dicts with ``'id'``, ``'description'``, and
            optional ``'type'`` keys.
        narratives:
            List of narrative dicts with ``'id'``, ``'text'``, and optional
            ``'theme'`` keys.
        beliefs:
            List of belief dicts with ``'id'``, ``'statement'``, and optional
            ``'confidence'`` keys.
        identity:
            List of identity dicts with ``'id'``, ``'statement'``, and optional
            ``'domain'`` keys.
        """
        logger.info('cog.reflection.pipeline_started', evidence_count=len(evidence))

        patterns = patterns or []
        narratives = narratives or []
        beliefs = beliefs or []
        identity = identity or []

        # Phase 1 — Relationship Analysis
        relationships = self._analyze_relationships(evidence, patterns, narratives, beliefs)

        # Phase 2 — Longitudinal Analysis
        longitudinal = self._longitudinal_analysis(evidence, patterns)

        # Phase 3 — Candidate Generation (try LLM first if available)
        llm_candidates = self._try_llm_reflection_generation(relationships, longitudinal)
        if llm_candidates:
            candidates = llm_candidates
        else:
            candidates = self._generate_candidates(relationships, longitudinal)

        # Phase 4 — Validation
        validated = self._validate(candidates)

        # Phase 5 — Blind Spot Detection
        blind_spots = self._blind_spot_detector.detect(evidence, patterns, identity)

        # Store reflections
        for ref in validated.values():
            self._reflections[ref.identifier] = ref

        result = ReflectionResult(
            reflections=validated,
            blind_spots=blind_spots,
            total_extracted=len(validated),
        )

        logger.info(
            'cog.reflection.pipeline_completed',
            total_extracted=result.total_extracted,
            blind_spots_found=len(blind_spots),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Relationship Analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_relationships(
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Cross-reference evidence, patterns, narratives, and beliefs."""
        relationships: list[dict[str, Any]] = []

        # Group evidence by category
        evidence_by_cat: dict[str, list[dict[str, Any]]] = {}
        for ev in evidence:
            cat = ev.get('category', 'general')
            evidence_by_cat.setdefault(cat, []).append(ev)

        # Find evidence-pattern overlaps
        for pattern in patterns:
            pattern_id = pattern.get('id', '')
            pattern_desc = pattern.get('description', '')
            linked_evidence = [
                ev.get('id', '') for ev in evidence
                if _text_overlap(ev.get('text', ''), pattern_desc)
            ]
            if linked_evidence:
                relationships.append({
                    'type': 'evidence_pattern',
                    'pattern_id': pattern_id,
                    'evidence_ids': tuple(linked_evidence),
                    'strength': min(1.0, len(linked_evidence) * 0.2),
                })

        # Find evidence-narrative overlaps
        for narrative in narratives:
            narr_id = narrative.get('id', '')
            narr_text = narrative.get('text', '')
            linked_evidence = [
                ev.get('id', '') for ev in evidence
                if _text_overlap(ev.get('text', ''), narr_text)
            ]
            if linked_evidence:
                relationships.append({
                    'type': 'evidence_narrative',
                    'narrative_id': narr_id,
                    'evidence_ids': tuple(linked_evidence),
                    'strength': min(1.0, len(linked_evidence) * 0.2),
                })

        # Find evidence-belief overlaps
        for belief in beliefs:
            belief_id = belief.get('id', '')
            belief_stmt = belief.get('statement', '')
            linked_evidence = [
                ev.get('id', '') for ev in evidence
                if _text_overlap(ev.get('text', ''), belief_stmt)
            ]
            if linked_evidence:
                relationships.append({
                    'type': 'evidence_belief',
                    'belief_id': belief_id,
                    'evidence_ids': tuple(linked_evidence),
                    'strength': min(1.0, len(linked_evidence) * 0.2),
                })

        logger.info('cog.reflection.relationships_analyzed', count=len(relationships))
        return relationships

    # ------------------------------------------------------------------
    # Phase 2: Longitudinal Analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _longitudinal_analysis(
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Detect temporal trends across evidence and patterns."""
        total_evidence = len(evidence)
        total_patterns = len(patterns)

        # Compute category distribution
        category_counts: dict[str, int] = {}
        for ev in evidence:
            cat = ev.get('category', 'general')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Determine temporal coverage
        if total_evidence >= 10:
            temporal_coverage = 'extensive'
        elif total_evidence >= 5:
            temporal_coverage = 'moderate'
        elif total_evidence >= 2:
            temporal_coverage = 'limited'
        else:
            temporal_coverage = 'minimal'

        # Compute breadth: ratio of distinct categories
        unique_categories = len(category_counts)
        breadth = min(1.0, unique_categories * 0.25)

        # Compute depth: evidence per pattern
        depth = total_evidence / max(1, total_patterns)

        return {
            'temporal_coverage': temporal_coverage,
            'breadth': breadth,
            'depth': depth,
            'total_evidence': total_evidence,
            'total_patterns': total_patterns,
            'category_counts': category_counts,
        }

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _try_llm_reflection_generation(
        self,
        relationships: list[dict[str, Any]],
        longitudinal: dict[str, Any],
    ) -> dict[str, ReflectionObject] | None:
        """Attempt LLM-based reflection generation. Returns None on failure."""
        if not self._ai_router:
            return None
        try:
            import asyncio
            import uuid as _uuid
            from ayeneh.ai_router.types import AITask, AITaskType

            rel_descriptions = []
            for rel in relationships[:10]:
                rel_type = rel.get('type', 'unknown')
                strength = rel.get('strength', 0.0)
                rel_descriptions.append(
                    f"- type: {rel_type}, strength: {strength:.2f}, "
                    f"evidence_ids: {rel.get('evidence_ids', ())}"
                )

            prompt = (
                "Generate cognitive reflection statements based on the following "
                "relationships and longitudinal analysis.\n\n"
                "Relationships:\n"
                + ("\n".join(rel_descriptions) if rel_descriptions else "(none)")
                + f"\n\nLongitudinal coverage: {longitudinal.get('temporal_coverage', 'minimal')}"
                + f"\nBreadth: {longitudinal.get('breadth', 0.0):.2f}"
                + f"\nDepth: {longitudinal.get('depth', 0.0):.2f}"
                + "\n\nFor each reflection, provide:\n"
                "- statement: a descriptive observation\n"
                "- scope: one of project, identity, life_trajectory\n"
                "- confidence: 0.0-1.0\n\n"
                "Respond as a JSON list of objects with keys: statement, scope, confidence."
            )
            messages = [
                {"role": "system", "content": "You are a cognitive reflection assistant."},
                {"role": "user", "content": prompt},
            ]
            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=prompt,
                max_tokens=1024,
                temperature=0.3,
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                return None

            import json
            start = content.find('[')
            end = content.rfind(']') + 1
            if start == -1 or end <= 0:
                return None
            items = json.loads(content[start:end])
            candidates: dict[str, ReflectionObject] = {}
            for item in items:
                statement = item.get('statement', '')
                scope = item.get('scope', 'project')
                confidence = float(item.get('confidence', 0.5))
                if not statement or scope not in REFLECTION_SCOPES:
                    continue
                ref = ReflectionObject(
                    identifier=str(_uuid.uuid4()),
                    reflection_statement=statement,
                    scope=scope,
                    temporal_coverage=longitudinal.get('temporal_coverage', ''),
                    confidence=min(confidence, 1.0),
                    granularity=_infer_granularity(longitudinal),
                )
                candidates[ref.identifier] = ref
            return candidates if candidates else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Phase 3: Candidate Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_candidates(
        relationships: list[dict[str, Any]],
        longitudinal: dict[str, Any],
    ) -> dict[str, ReflectionObject]:
        """Propose reflection candidates from relationship and longitudinal analysis."""
        candidates: dict[str, ReflectionObject] = {}

        # Generate reflections from evidence-pattern relationships
        for rel in relationships:
            if rel['type'] == 'evidence_pattern':
                ref = ReflectionObject(
                    identifier=str(uuid.uuid4()),
                    reflection_statement=_build_reflection_statement(rel),
                    scope=_infer_scope(rel),
                    temporal_coverage=longitudinal.get('temporal_coverage', ''),
                    confidence=rel.get('strength', 0.0),
                    supporting_evidence=rel.get('evidence_ids', ()),
                    supporting_patterns=(rel.get('pattern_id', ''),),
                    granularity=_infer_granularity(longitudinal),
                )
                candidates[ref.identifier] = ref

        # Generate reflections from evidence-narrative relationships
        for rel in relationships:
            if rel['type'] == 'evidence_narrative':
                ref = ReflectionObject(
                    identifier=str(uuid.uuid4()),
                    reflection_statement=_build_narrative_reflection(rel),
                    scope=_infer_scope(rel),
                    temporal_coverage=longitudinal.get('temporal_coverage', ''),
                    confidence=rel.get('strength', 0.0),
                    supporting_evidence=rel.get('evidence_ids', ()),
                    supporting_narratives=(rel.get('narrative_id', ''),),
                    granularity=_infer_granularity(longitudinal),
                )
                candidates[ref.identifier] = ref

        # Generate reflections from evidence-belief relationships
        for rel in relationships:
            if rel['type'] == 'evidence_belief':
                ref = ReflectionObject(
                    identifier=str(uuid.uuid4()),
                    reflection_statement=_build_belief_reflection(rel),
                    scope=_infer_scope(rel),
                    temporal_coverage=longitudinal.get('temporal_coverage', ''),
                    confidence=rel.get('strength', 0.0),
                    supporting_evidence=rel.get('evidence_ids', ()),
                    supporting_beliefs=(rel.get('belief_id', ''),),
                    granularity=_infer_granularity(longitudinal),
                )
                candidates[ref.identifier] = ref

        logger.info('cog.reflection.candidates_generated', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 4: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(candidates: dict[str, ReflectionObject]) -> dict[str, ReflectionObject]:
        """Validate and filter candidate reflections."""
        validated: dict[str, ReflectionObject] = {}

        for ref in candidates.values():
            # Must have at least one supporting reference
            has_support = (
                len(ref.supporting_evidence) > 0
                or len(ref.supporting_patterns) > 0
                or len(ref.supporting_narratives) > 0
                or len(ref.supporting_beliefs) > 0
            )
            if not has_support:
                continue

            # Determine lifecycle state based on confidence and support
            support_count = (
                len(ref.supporting_evidence)
                + len(ref.supporting_patterns)
                + len(ref.supporting_narratives)
                + len(ref.supporting_beliefs)
            )

            if ref.confidence >= 0.5 and support_count >= 3:
                state = 'validated'
            elif ref.confidence >= 0.3 and support_count >= 2:
                state = 'provisional'
            else:
                state = 'candidate'

            # Advance lifecycle
            validated[ref.identifier] = ReflectionObject(
                identifier=ref.identifier,
                reflection_statement=ref.reflection_statement,
                scope=ref.scope,
                temporal_coverage=ref.temporal_coverage,
                confidence=ref.confidence,
                supporting_evidence=ref.supporting_evidence,
                supporting_patterns=ref.supporting_patterns,
                supporting_narratives=ref.supporting_narratives,
                supporting_beliefs=ref.supporting_beliefs,
                contradictory_evidence=ref.contradictory_evidence,
                granularity=ref.granularity,
                lifecycle_state=state,
                creation_timestamp=ref.creation_timestamp,
            )

        logger.info('cog.reflection.validated', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 5: Blind Spot Detection (delegated)
    # ------------------------------------------------------------------

    def _detect_blind_spots(
        self,
        evidence: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[BlindSpot]:
        """Detect cognitive structures absent from awareness."""
        return self._blind_spot_detector.detect(evidence, patterns, identity)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _text_overlap(text_a: str, text_b: str) -> bool:
    """Check if two texts share meaningful word overlap."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    # Remove common stop words
    stop_words = {'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be',
                  'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                  'will', 'would', 'could', 'should', 'may', 'might', 'shall',
                  'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                  'from', 'it', 'this', 'that', 'and', 'or', 'but', 'not', 'my'}
    meaningful_a = words_a - stop_words
    meaningful_b = words_b - stop_words
    if not meaningful_a or not meaningful_b:
        return False
    overlap = meaningful_a & meaningful_b
    return len(overlap) >= 1


def _build_reflection_statement(rel: dict[str, Any]) -> str:
    """Build a reflection statement from an evidence-pattern relationship."""
    pattern_id = rel.get('pattern_id', 'unknown')
    evidence_count = len(rel.get('evidence_ids', ()))
    return (
        f"Pattern {pattern_id} is supported by {evidence_count} evidence "
        f"point(s), suggesting a recurring cognitive structure."
    )


def _build_narrative_reflection(rel: dict[str, Any]) -> str:
    """Build a reflection statement from an evidence-narrative relationship."""
    narr_id = rel.get('narrative_id', 'unknown')
    evidence_count = len(rel.get('evidence_ids', ()))
    return (
        f"Narrative {narr_id} is reinforced by {evidence_count} evidence "
        f"point(s), indicating an active narrative framework."
    )


def _build_belief_reflection(rel: dict[str, Any]) -> str:
    """Build a reflection statement from an evidence-belief relationship."""
    belief_id = rel.get('belief_id', 'unknown')
    evidence_count = len(rel.get('evidence_ids', ()))
    return (
        f"Belief {belief_id} is supported by {evidence_count} evidence "
        f"point(s), suggesting this belief is actively maintained."
    )


def _infer_scope(rel: dict[str, Any]) -> str:
    """Infer the scope of a reflection from its relationship type."""
    scope_map: dict[str, str] = {
        'evidence_pattern': 'project',
        'evidence_narrative': 'identity',
        'evidence_belief': 'life_trajectory',
    }
    return scope_map.get(rel.get('type', ''), 'project')


def _infer_granularity(longitudinal: dict[str, Any]) -> str:
    """Infer granularity from longitudinal analysis."""
    coverage = longitudinal.get('temporal_coverage', 'minimal')
    mapping: dict[str, str] = {
        'extensive': 'project',
        'moderate': 'weekly',
        'limited': 'session',
        'minimal': 'micro',
    }
    return mapping.get(coverage, 'session')
