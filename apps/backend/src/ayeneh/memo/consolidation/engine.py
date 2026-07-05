"""Consolidation engine (MEM-05).

Ten-phase pipeline:
1. WorkingMemory
2. CandidateMemories
3. EvidenceAggregation
4. CrossEpisodeValidation
5. ConflictAnalysis
6. ConsolidationDecision
7. LongTermMemoryUpdate
8. KnowledgeGraphUpdate
9. TrajectoryUpdate
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import (
    CONSOLIDATION_LEVELS,
    CONSOLIDATION_LEVEL_VALUES,
    make_version_record,
)
from ayeneh.memo.consolidation.types import (
    CONSOLIDATION_CRITERIA,
    CONSOLIDATION_DECISIONS,
    CONSOLIDATION_LEVEL_HIERARCHY,
    CONSOLIDATION_LEVEL_HIERARCHY_VALUES,
    ConsolidationCriteriaResult,
    ConsolidationObject,
    ConsolidationPipelineResult,
    EvidenceAggregation,
    make_consolidation_version,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
DEFAULT_MIN_EVIDENCE_COUNT: int = 2
DEFAULT_MIN_EPISODES_FOR_CROSS_VALIDATION: int = 2


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ConsolidationEngine:
    """Ten-phase consolidation pipeline.

    Evaluates working memory candidates for promotion to long-term storage,
    aggregating evidence, validating across episodes, and resolving conflicts.
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        min_evidence_count: int = DEFAULT_MIN_EVIDENCE_COUNT,
        min_episodes_for_cross_validation: int = DEFAULT_MIN_EPISODES_FOR_CROSS_VALIDATION,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._min_evidence_count = min_evidence_count
        self._min_episodes = min_episodes_for_cross_validation
        self._consolidation_history: list[ConsolidationObject] = []
        self._long_term_store: dict[str, dict[str, Any]] = {}
        self._knowledge_graph: dict[str, list[str]] = {}
        self._trajectories: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        working_memory_items: list[dict[str, Any]],
        *,
        episodes: list[dict[str, Any]] | None = None,
        conversations: list[dict[str, Any]] | None = None,
    ) -> ConsolidationPipelineResult:
        """Run the full 10-phase consolidation pipeline."""
        result = ConsolidationPipelineResult()

        if not working_memory_items:
            return result

        # Phase 1: WorkingMemory — captured as working_memory_items param

        # Phase 2: CandidateMemories
        candidates = self._extract_candidates(working_memory_items)
        logger.debug('phase_2_candidates_extracted', count=len(candidates))

        # Phase 3: EvidenceAggregation
        evidence_results = self._aggregate_evidence(candidates, episodes, conversations)
        logger.debug('phase_3_evidence_aggregated', count=len(evidence_results))

        # Phase 4: CrossEpisodeValidation
        cross_validated = self._cross_episode_validate(evidence_results, episodes)
        logger.debug('phase_4_cross_validated', count=len(cross_validated))

        # Phase 5: ConflictAnalysis
        conflict_free = self._analyze_conflicts(cross_validated)
        logger.debug('phase_5_conflicts_analyzed', count=len(conflict_free))

        # Phase 6: ConsolidationDecision
        decisions = self._make_decisions(conflict_free)
        logger.debug('phase_6_decisions_made', count=len(decisions))

        # Phase 7: LongTermMemoryUpdate
        promoted = self._update_long_term_memory(decisions)

        # Phase 8: KnowledgeGraphUpdate
        self._update_knowledge_graph(promoted)

        # Phase 9: TrajectoryUpdate
        self._update_trajectories(promoted)

        # Compute summary counts
        processed_count = len(working_memory_items)
        promoted_count = len(promoted)
        rejected_count = sum(1 for d in decisions if d.is_rejected)
        deferred_count = sum(
            1 for d in decisions if not d.is_promoted and not d.is_rejected
        )
        consolidated_objects = tuple(promoted)
        affected_cognitive_objects = tuple(
            obj_id
            for d in promoted
            for obj_id in d.affected_cognitive_objects
        )

        return ConsolidationPipelineResult(
            processed_count=processed_count,
            promoted_count=promoted_count,
            rejected_count=rejected_count,
            deferred_count=deferred_count,
            consolidated_objects=consolidated_objects,
            affected_cognitive_objects=affected_cognitive_objects,
        )

    def evaluate_criteria(
        self,
        memory_id: str,
        evidence: list[dict[str, Any]],
        episodes: list[dict[str, Any]] | None = None,
    ) -> ConsolidationCriteriaResult:
        """Evaluate consolidation criteria for a single memory candidate."""
        met: list[str] = []
        failed: list[str] = []

        # Check each criterion
        for criterion in CONSOLIDATION_CRITERIA:
            if self._check_criterion(criterion, evidence, episodes):
                met.append(criterion)
            else:
                failed.append(criterion)

        # Calculate overall score
        total = len(met) + len(failed)
        overall_score = len(met) / total if total > 0 else 0.0

        # Determine recommendation
        if overall_score >= 0.7 and len(evidence) >= self._min_evidence_count:
            recommendation = 'promote'
        elif overall_score <= 0.3:
            recommendation = 'reject'
        else:
            recommendation = 'defer'

        # Build evidence aggregation
        evidence_agg = self._build_evidence_aggregation(memory_id, evidence)

        return ConsolidationCriteriaResult(
            memory_id=memory_id,
            criteria_met=tuple(met),
            criteria_failed=tuple(failed),
            overall_score=overall_score,
            recommendation=recommendation,
            evidence_aggregation=evidence_agg,
        )

    def get_consolidation_history(self) -> list[ConsolidationObject]:
        """Return the history of consolidation decisions."""
        return list(self._consolidation_history)

    def get_long_term_store(self) -> dict[str, dict[str, Any]]:
        """Return the current long-term memory store."""
        return dict(self._long_term_store)

    # ------------------------------------------------------------------
    # Phase 2: CandidateMemories
    # ------------------------------------------------------------------

    def _extract_candidates(
        self,
        working_memory_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract consolidation candidates from working memory items."""
        candidates = []
        for item in working_memory_items:
            # Only consider items with sufficient activation
            if item.get('activation_score', 0.0) >= self._confidence_threshold:
                candidates.append(item)
        return candidates

    # ------------------------------------------------------------------
    # Phase 3: EvidenceAggregation
    # ------------------------------------------------------------------

    def _aggregate_evidence(
        self,
        candidates: list[dict[str, Any]],
        episodes: list[dict[str, Any]] | None,
        conversations: list[dict[str, Any]] | None,
    ) -> list[ConsolidationCriteriaResult]:
        """Aggregate evidence for each candidate."""
        episodes = episodes or []
        conversations = conversations or []

        results: list[ConsolidationCriteriaResult] = []
        for candidate in candidates:
            mem_id = candidate.get('id', candidate.get('identifier', ''))
            evidence = candidate.get('evidence', [])
            supporting_episodes = candidate.get('supporting_episodes', [])

            # Find matching episodes
            episode_evidence = [
                ep for ep in episodes
                if ep.get('id', '') in supporting_episodes
            ]

            all_evidence = evidence + [
                {'source': 'episode', 'content': ep.get('summary', '')}
                for ep in episode_evidence
            ]

            result = self.evaluate_criteria(mem_id, all_evidence, episodes)
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Phase 4: CrossEpisodeValidation
    # ------------------------------------------------------------------

    def _cross_episode_validate(
        self,
        candidates: list[ConsolidationCriteriaResult],
        episodes: list[dict[str, Any]] | None,
    ) -> list[ConsolidationCriteriaResult]:
        """Validate candidates across multiple episodes."""
        episodes = episodes or []
        validated: list[ConsolidationCriteriaResult] = []

        for candidate in candidates:
            # Check for cross-episode recurrence
            episode_count = 0
            for ep in episodes:
                if candidate.memory_id in str(ep):
                    episode_count += 1

            if episode_count >= self._min_episodes:
                # Boost the score for cross-episode recurrence
                new_score = min(1.0, candidate.overall_score + 0.15)
                validated_result = ConsolidationCriteriaResult(
                    memory_id=candidate.memory_id,
                    criteria_met=candidate.criteria_met + ('cross_episode_recurrence',),
                    criteria_failed=candidate.criteria_failed,
                    overall_score=new_score,
                    recommendation=candidate.recommendation,
                    evidence_aggregation=candidate.evidence_aggregation,
                )
                validated.append(validated_result)
            else:
                validated.append(candidate)

        return validated

    # ------------------------------------------------------------------
    # Phase 5: ConflictAnalysis
    # ------------------------------------------------------------------

    def _analyze_conflicts(
        self,
        candidates: list[ConsolidationCriteriaResult],
    ) -> list[ConsolidationCriteriaResult]:
        """Analyze and resolve conflicts between candidates."""
        if not candidates:
            return candidates

        # Simple conflict detection: if two candidates have the same memory_id
        # but different recommendations, keep the one with higher score
        seen: dict[str, ConsolidationCriteriaResult] = {}
        resolved: list[ConsolidationCriteriaResult] = []

        for candidate in candidates:
            existing = seen.get(candidate.memory_id)
            if existing is None:
                seen[candidate.memory_id] = candidate
                resolved.append(candidate)
            elif candidate.overall_score > existing.overall_score:
                # Replace with higher-scored version
                resolved = [c for c in resolved if c.memory_id != candidate.memory_id]
                resolved.append(candidate)
                seen[candidate.memory_id] = candidate

        return resolved

    # ------------------------------------------------------------------
    # Phase 6: ConsolidationDecision
    # ------------------------------------------------------------------

    def _make_decisions(
        self,
        candidates: list[ConsolidationCriteriaResult],
    ) -> list[ConsolidationObject]:
        """Make consolidation decisions for each candidate."""
        decisions: list[ConsolidationObject] = []

        for candidate in candidates:
            if candidate.recommendation == 'promote':
                decision = ConsolidationObject(
                    identifier=f"cons_{uuid.uuid4().hex[:12]}",
                    target_memory=candidate.memory_id,
                    evidence_summary=f"Met {len(candidate.criteria_met)}/{len(candidate.criteria_met) + len(candidate.criteria_failed)} criteria",
                    confidence_before=candidate.overall_score,
                    confidence_after=min(1.0, candidate.overall_score + 0.2),
                    reason_for_promotion=f"Score {candidate.overall_score:.2f} exceeds threshold",
                )
            elif candidate.recommendation == 'reject':
                decision = ConsolidationObject(
                    identifier=f"cons_{uuid.uuid4().hex[:12]}",
                    target_memory=candidate.memory_id,
                    evidence_summary=f"Met only {len(candidate.criteria_met)}/{len(candidate.criteria_met) + len(candidate.criteria_failed)} criteria",
                    confidence_before=candidate.overall_score,
                    confidence_after=candidate.overall_score * 0.5,
                    reason_for_rejection=f"Score {candidate.overall_score:.2f} below threshold",
                )
            else:
                # Defer
                decision = ConsolidationObject(
                    identifier=f"cons_{uuid.uuid4().hex[:12]}",
                    target_memory=candidate.memory_id,
                    evidence_summary="Insufficient evidence for decision",
                    confidence_before=candidate.overall_score,
                    confidence_after=candidate.overall_score,
                )

            decisions.append(decision)

        return decisions

    # ------------------------------------------------------------------
    # Phase 7: LongTermMemoryUpdate
    # ------------------------------------------------------------------

    def _update_long_term_memory(
        self,
        decisions: list[ConsolidationObject],
    ) -> list[ConsolidationObject]:
        """Update long-term memory store with promoted items."""
        promoted: list[ConsolidationObject] = []

        for decision in decisions:
            if decision.is_promoted:
                self._long_term_store[decision.target_memory] = {
                    'consolidation_id': decision.identifier,
                    'confidence': decision.confidence_after,
                    'evidence_summary': decision.evidence_summary,
                    'timestamp': decision.timestamp.isoformat(),
                }
                promoted.append(decision)
                self._consolidation_history.append(decision)

                logger.info(
                    'memory_consolidated',
                    memory_id=decision.target_memory,
                    confidence=decision.confidence_after,
                )

        return promoted

    # ------------------------------------------------------------------
    # Phase 8: KnowledgeGraphUpdate
    # ------------------------------------------------------------------

    def _update_knowledge_graph(
        self,
        promoted: list[ConsolidationObject],
    ) -> None:
        """Update the knowledge graph with consolidated memories."""
        for decision in promoted:
            mem_id = decision.target_memory
            if mem_id not in self._knowledge_graph:
                self._knowledge_graph[mem_id] = []

            # Add links to affected cognitive objects
            for obj_id in decision.affected_cognitive_objects:
                if obj_id not in self._knowledge_graph[mem_id]:
                    self._knowledge_graph[mem_id].append(obj_id)

    # ------------------------------------------------------------------
    # Phase 9: TrajectoryUpdate
    # ------------------------------------------------------------------

    def _update_trajectories(
        self,
        promoted: list[ConsolidationObject],
    ) -> None:
        """Update developmental trajectories with consolidated memories."""
        for decision in promoted:
            mem_id = decision.target_memory
            if mem_id not in self._trajectories:
                self._trajectories[mem_id] = []
            self._trajectories[mem_id].append(decision.identifier)

    # ------------------------------------------------------------------
    # Criterion checking
    # ------------------------------------------------------------------

    def _check_criterion(
        self,
        criterion: str,
        evidence: list[dict[str, Any]],
        episodes: list[dict[str, Any]] | None,
    ) -> bool:
        """Check if a specific consolidation criterion is met."""
        episodes = episodes or []

        if criterion == 'repeated_observation':
            return len(evidence) >= 2
        elif criterion == 'behavioral_confirmation':
            return any(
                e.get('source') == 'behavior' or e.get('evidence_type') == 'behavior'
                for e in evidence
            )
        elif criterion == 'cross_context_consistency':
            sources = set(e.get('source', '') for e in evidence)
            return len(sources) >= 2
        elif criterion == 'cross_episode_recurrence':
            return len(episodes) >= self._min_episodes
        elif criterion == 'identity_relevance':
            return any(
                'identity' in str(e).lower() for e in evidence
            )
        elif criterion == 'goal_relevance':
            return any(
                'goal' in str(e).lower() for e in evidence
            )
        elif criterion == 'value_relevance':
            return any(
                'value' in str(e).lower() for e in evidence
            )
        elif criterion == 'longitudinal_persistence':
            return len(evidence) >= 3
        elif criterion == 'high_quality_evidence':
            return any(
                e.get('confidence', 0.0) >= 0.7 for e in evidence
            )
        return False

    def _build_evidence_aggregation(
        self,
        memory_id: str,
        evidence: list[dict[str, Any]],
    ) -> EvidenceAggregation:
        """Build an EvidenceAggregation from a list of evidence dicts."""
        total = len(evidence)
        supporting = sum(
            1 for e in evidence
            if e.get('supports', True) is True
        )
        contradicting = total - supporting

        confidences = [e.get('confidence', 0.5) for e in evidence]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return EvidenceAggregation(
            aggregation_id=f"ea_{uuid.uuid4().hex[:12]}",
            evidence_ids=tuple(e.get('id', f"e_{i}") for i, e in enumerate(evidence)),
            total_evidence_count=total,
            supporting_count=supporting,
            contradicting_count=contradicting,
            aggregated_confidence=avg_confidence,
            quality_score=avg_confidence,
            diversity_score=min(1.0, len(set(e.get('source', '') for e in evidence)) / 3.0),
        )
