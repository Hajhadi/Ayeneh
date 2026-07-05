"""MEM-07 Ranking engine.

Implements the full ranking pipeline: FeatureExtraction → RelevanceEstimation
→ ImportanceEstimation → ContextMatching → EvidenceWeighting → ConflictDetection
→ CompositeRanking → WorkingMemorySelection.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.ranking.types import (
    ConflictRecord,
    DimensionScores,
    RankingContext,
    RankingDimension,
    RankingObject,
    RankingPipelineStage,
    TaskProfile,
    TASK_PROFILE_WEIGHTS,
    WorkingMemorySelection,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Feature extraction
# ---------------------------------------------------------------------------

def extract_features(memory: MemoryObject, context: RankingContext) -> DimensionScores:
    """Extract raw feature signals from a memory and the current context."""
    scores: dict[str, float] = {}
    raw: dict[str, Any] = {}

    # Recency — exponential decay based on age in hours
    age_hours = (datetime.now(UTC) - memory.last_updated).total_seconds() / 3600
    recency = max(0.0, 1.0 - min(age_hours / 168.0, 1.0))  # 1-week half-life
    scores[RankingDimension.CURRENT_RELEVANCE.value] = recency
    raw['age_hours'] = age_hours

    # Importance — from memory's own score
    scores[RankingDimension.LONG_TERM_IMPORTANCE.value] = memory.importance_score
    raw['importance_score'] = memory.importance_score

    # Confidence
    scores[RankingDimension.UNCERTAINTY.value] = 1.0 - memory.confidence
    raw['confidence'] = memory.confidence

    # Behavioral influence — count of associated cognitive objects
    behavioral = min(1.0, len(memory.associated_cognitive_objects) / 5.0)
    scores[RankingDimension.BEHAVIORAL_INFLUENCE.value] = behavioral
    raw['cognitive_objects_count'] = len(memory.associated_cognitive_objects)

    # Identity influence — based on episodic associations
    identity = min(1.0, len(memory.associated_episodes) / 5.0)
    scores[RankingDimension.IDENTITY_INFLUENCE.value] = identity
    raw['episode_count'] = len(memory.associated_episodes)

    # Goal influence — overlap with active goals
    if context.current_goals:
        overlap = len(set(memory.associated_projects) & set(context.current_goals))
        scores[RankingDimension.GOAL_INFLUENCE.value] = min(1.0, overlap / max(len(context.current_goals), 1))
    else:
        scores[RankingDimension.GOAL_INFLUENCE.value] = 0.0

    # Value influence — overlap with identity components (proxy for values)
    if context.identity_components:
        val_overlap = len(set(memory.associated_cognitive_objects) & set(context.identity_components))
        scores[RankingDimension.VALUE_INFLUENCE.value] = min(1.0, val_overlap / max(len(context.identity_components), 1))
    else:
        scores[RankingDimension.VALUE_INFLUENCE.value] = 0.0

    # Semantic similarity — placeholder heuristic using memory type match
    scores[RankingDimension.SEMANTIC_SIMILARITY.value] = 0.5
    raw['semantic_placeholder'] = True

    # Evidence quality
    scores[RankingDimension.EVIDENCE_QUALITY.value] = min(1.0, len(memory.supporting_evidence) / 3.0)
    raw['evidence_count'] = len(memory.supporting_evidence)

    # Graph centrality — placeholder
    scores[RankingDimension.GRAPH_CENTRALITY.value] = 0.5

    # Context compatibility — placeholder
    scores[RankingDimension.CONTEXT_COMPATIBILITY.value] = 0.5

    # Novelty — inverse of importance (new things are novel)
    scores[RankingDimension.NOVELTY.value] = max(0.0, 1.0 - memory.importance_score)

    return DimensionScores(memory_id=memory.identifier, scores=scores, raw_features=raw)


# ---------------------------------------------------------------------------
# Stage 2: Relevance estimation
# ---------------------------------------------------------------------------

def estimate_relevance(
    dim_scores: DimensionScores,
    context: RankingContext,
) -> float:
    """Estimate how relevant a memory is to the current context."""
    base = dim_scores.score(RankingDimension.CURRENT_RELEVANCE)
    context_bonus = dim_scores.score(RankingDimension.CONTEXT_COMPATIBILITY) * 0.3
    semantic_bonus = dim_scores.score(RankingDimension.SEMANTIC_SIMILARITY) * 0.2
    return min(1.0, base + context_bonus + semantic_bonus)


# ---------------------------------------------------------------------------
# Stage 3: Importance estimation
# ---------------------------------------------------------------------------

def estimate_importance(
    dim_scores: DimensionScores,
    memory: MemoryObject,
) -> float:
    """Estimate long-term importance of a memory."""
    base = dim_scores.score(RankingDimension.LONG_TERM_IMPORTANCE)
    behavioral = dim_scores.score(RankingDimension.BEHAVIORAL_INFLUENCE) * 0.2
    identity = dim_scores.score(RankingDimension.IDENTITY_INFLUENCE) * 0.2
    consolidation_bonus = 0.1 if memory.lifecycle_status in ('consolidated_memory', 'longitudinal_memory') else 0.0
    return min(1.0, base + behavioral + identity + consolidation_bonus)


# ---------------------------------------------------------------------------
# Stage 4: Context matching
# ---------------------------------------------------------------------------

def match_context(
    dim_scores: DimensionScores,
    context: RankingContext,
) -> float:
    """Score how well a memory matches the current context."""
    goal = dim_scores.score(RankingDimension.GOAL_INFLUENCE)
    compat = dim_scores.score(RankingDimension.CONTEXT_COMPATIBILITY)
    return min(1.0, goal * 0.5 + compat * 0.5)


# ---------------------------------------------------------------------------
# Stage 5: Evidence weighting
# ---------------------------------------------------------------------------

def weight_evidence(
    dim_scores: DimensionScores,
    memory: MemoryObject,
) -> float:
    """Weight a memory by its evidence quality and confidence."""
    eq = dim_scores.score(RankingDimension.EVIDENCE_QUALITY)
    unc = dim_scores.score(RankingDimension.UNCERTAINTY)
    conf = memory.confidence
    return min(1.0, eq * 0.4 + conf * 0.4 + (1.0 - unc) * 0.2)


# ---------------------------------------------------------------------------
# Stage 6: Conflict detection
# ---------------------------------------------------------------------------

def detect_conflicts(
    ranked: list[tuple[MemoryObject, float]],
) -> list[ConflictRecord]:
    """Detect pairwise conflicts among ranked memories."""
    conflicts: list[ConflictRecord] = []
    for i, (mem_a, _) in enumerate(ranked):
        for mem_b, _ in ranked[i + 1:]:
            # Simple heuristic: conflicting if one supports and another contradicts
            a_evidence = set(mem_a.supporting_evidence)
            b_evidence = set(mem_b.supporting_evidence)
            common = a_evidence & b_evidence
            if common and mem_a.memory_type != mem_b.memory_type:
                conflicts.append(
                    ConflictRecord(
                        memory_a=mem_a.identifier,
                        memory_b=mem_b.identifier,
                        conflict_type='evidence_overlap',
                        severity=len(common) / max(len(a_evidence | b_evidence), 1),
                        explanation=f'{len(common)} shared evidence items',
                    )
                )
    return conflicts


# ---------------------------------------------------------------------------
# Stage 7: Composite ranking
# ---------------------------------------------------------------------------

def composite_rank(
    memory: MemoryObject,
    dim_scores: DimensionScores,
    relevance: float,
    importance: float,
    context_match: float,
    evidence_weight: float,
    task_profile: TaskProfile = TaskProfile.DEBUGGING,
) -> RankingObject:
    """Compute the composite ranking score using task-specific weights."""
    weights = TASK_PROFILE_WEIGHTS.get(task_profile, TASK_PROFILE_WEIGHTS[TaskProfile.DEBUGGING])

    weighted_sum = 0.0
    for dim_name, weight in weights.items():
        weighted_sum += dim_scores.scores.get(dim_name, 0.0) * weight

    # Blend component scores
    overall = (
        weighted_sum * 0.5
        + relevance * 0.2
        + importance * 0.15
        + context_match * 0.1
        + evidence_weight * 0.05
    )
    overall = min(1.0, max(0.0, overall))

    explanation_parts = [
        f'relevance={relevance:.2f}',
        f'importance={importance:.2f}',
        f'context={context_match:.2f}',
        f'evidence={evidence_weight:.2f}',
        f'weighted={weighted_sum:.2f}',
    ]

    return RankingObject(
        ranking_identifier=f'rank_{memory.identifier}_{int(datetime.now(UTC).timestamp())}',
        target_memory=memory.identifier,
        overall_score=overall,
        relevance_score=relevance,
        importance_score=importance,
        confidence_score=memory.confidence,
        centrality_score=dim_scores.score(RankingDimension.GRAPH_CENTRALITY),
        recency_score=dim_scores.score(RankingDimension.CURRENT_RELEVANCE),
        behavioral_impact_score=dim_scores.score(RankingDimension.BEHAVIORAL_INFLUENCE),
        identity_impact_score=dim_scores.score(RankingDimension.IDENTITY_INFLUENCE),
        evidence_quality_score=dim_scores.score(RankingDimension.EVIDENCE_QUALITY),
        ranking_explanation='; '.join(explanation_parts),
    )


# ---------------------------------------------------------------------------
# Stage 8: Working memory selection
# ---------------------------------------------------------------------------

def select_working_memory(
    rankings: list[RankingObject],
    capacity: int = 20,
) -> WorkingMemorySelection:
    """Select top-ranked memories to populate working memory."""
    sorted_rankings = sorted(rankings, key=lambda r: r.overall_score, reverse=True)
    selected = sorted_rankings[:capacity]
    selected_ids = tuple(r.target_memory for r in selected)

    return WorkingMemorySelection(
        selected_memories=selected_ids,
        rankings=tuple(selected),
        selection_reasoning=f'Selected top {len(selected)} of {len(rankings)} by overall_score',
        capacity_used=len(selected),
        capacity_max=capacity,
    )


# ---------------------------------------------------------------------------
# Full pipeline orchestrator
# ---------------------------------------------------------------------------

class RankingEngine:
    """Orchestrates the full MEM-07 ranking pipeline."""

    def __init__(self, default_capacity: int = 20) -> None:
        self.default_capacity = default_capacity

    def rank(
        self,
        memories: list[MemoryObject],
        context: RankingContext | None = None,
    ) -> WorkingMemorySelection:
        """Run the full ranking pipeline over a set of retrieved memories."""
        ctx = context or RankingContext()
        logger.info('ranking_pipeline.start', memory_count=len(memories))

        # 1. Feature extraction
        scored: list[tuple[MemoryObject, DimensionScores]] = []
        for mem in memories:
            dims = extract_features(mem, ctx)
            scored.append((mem, dims))

        # 2-5. Per-memory scoring
        ranked_pairs: list[tuple[MemoryObject, float]] = []
        rankings: list[RankingObject] = []
        for mem, dims in scored:
            relevance = estimate_relevance(dims, ctx)
            importance = estimate_importance(dims, mem)
            context_m = match_context(dims, ctx)
            evidence_w = weight_evidence(dims, mem)
            rank_obj = composite_rank(mem, dims, relevance, importance, context_m, evidence_w, ctx.task_profile)
            rankings.append(rank_obj)
            ranked_pairs.append((mem, rank_obj.overall_score))

        # 6. Conflict detection
        conflicts = detect_conflicts(ranked_pairs)
        if conflicts:
            logger.info('ranking_pipeline.conflicts', count=len(conflicts))
            # Reduce scores of conflicting memories slightly
            conflict_ids = set()
            for c in conflicts:
                conflict_ids.add(c.memory_a)
                conflict_ids.add(c.memory_b)
            rankings = [
                _apply_conflict_penalty(r, conflict_ids) for r in rankings
            ]

        # 7-8. Working memory selection
        selection = select_working_memory(rankings, self.default_capacity)
        logger.info(
            'ranking_pipeline.complete',
            selected=len(selection.selected_memories),
            total=len(memories),
        )
        return selection


def _apply_conflict_penalty(rank: RankingObject, conflict_ids: set[str]) -> RankingObject:
    """Apply a small penalty to memories involved in conflicts."""
    if rank.target_memory not in conflict_ids:
        return rank
    new_score = max(0.0, rank.overall_score * 0.9)
    return RankingObject(
        ranking_identifier=rank.ranking_identifier,
        target_memory=rank.target_memory,
        overall_score=new_score,
        relevance_score=rank.relevance_score,
        importance_score=rank.importance_score,
        confidence_score=rank.confidence_score,
        centrality_score=rank.centrality_score,
        recency_score=rank.recency_score,
        behavioral_impact_score=rank.behavioral_impact_score,
        identity_impact_score=rank.identity_impact_score,
        evidence_quality_score=rank.evidence_quality_score,
        ranking_explanation=rank.ranking_explanation + '; conflict_penalty',
        timestamp=rank.timestamp,
        version=rank.version,
    )
