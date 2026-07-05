"""MEM-07 Ranking diversity module.

Ensures the working-memory selection contains diverse memories rather than
redundant clusters, using a Maximal Marginal Relevance (MMR) inspired
approach.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ayeneh.memo.ranking.types import RankingObject


@dataclass(frozen=True)
class DiversityConfig:
    """Configuration for diversity re-ranking."""

    lambda_param: float = 0.7  # balance between relevance (1.0) and diversity (0.0)
    max_cluster_size: int = 3  # max memories from the same "cluster"


def _cluster_key(ranking: RankingObject) -> str:
    """Derive a simple cluster key from ranking explanation signals."""
    if ranking.identity_impact_score > 0.5:
        return 'identity'
    if ranking.behavioral_impact_score > 0.5:
        return 'behavioral'
    if ranking.evidence_quality_score > 0.5:
        return 'evidence'
    if ranking.relevance_score > 0.5:
        return 'relevance'
    return 'general'


def _diversity_penalty(
    candidate: RankingObject,
    selected: Sequence[RankingObject],
    cluster_counts: dict[str, int],
    max_cluster: int,
) -> float:
    """Compute a diversity-based penalty for adding a candidate to the selection."""
    key = _cluster_key(candidate)
    count = cluster_counts.get(key, 0)

    # Penalize if cluster is already large
    cluster_penalty = 0.0
    if count >= max_cluster:
        cluster_penalty = 0.3 * (count - max_cluster + 1)

    # Penalize for similarity to already-selected (simple: same cluster overlap)
    similarity_penalty = 0.0
    for sel in selected:
        if _cluster_key(sel) == key:
            similarity_penalty += 0.1

    return cluster_penalty + similarity_penalty


def diversify_selection(
    rankings: list[RankingObject],
    target_size: int = 20,
    config: DiversityConfig | None = None,
) -> list[RankingObject]:
    """Re-rank using MMR-inspired diversification.

    Takes pre-scored rankings and returns a diversified subset of
    *target_size* memories, balancing relevance and diversity.
    """
    cfg = config or DiversityConfig()
    sorted_rankings = sorted(rankings, key=lambda r: r.overall_score, reverse=True)

    if len(sorted_rankings) <= target_size:
        return list(sorted_rankings)

    selected: list[RankingObject] = []
    remaining = list(sorted_rankings)
    cluster_counts: dict[str, int] = {}

    while len(selected) < target_size and remaining:
        best_idx = 0
        best_score = -1.0

        for i, candidate in enumerate(remaining):
            # MMR score: lambda * relevance - (1 - lambda) * diversity_penalty
            div_penalty = _diversity_penalty(
                candidate, selected, cluster_counts, cfg.max_cluster_size,
            )
            mmr = cfg.lambda_param * candidate.overall_score - (1.0 - cfg.lambda_param) * div_penalty

            if mmr > best_score:
                best_score = mmr
                best_idx = i

        chosen = remaining.pop(best_idx)
        selected.append(chosen)
        key = _cluster_key(chosen)
        cluster_counts[key] = cluster_counts.get(key, 0) + 1

    return selected
