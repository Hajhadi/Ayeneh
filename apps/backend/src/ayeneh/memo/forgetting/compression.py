"""MEM-08 Compression strategies.

Implements the five compression types: Redundancy, Conversation, Episode,
Semantic, and Graph compression.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.forgetting.types import (
    CompressionObject,
    CompressionType,
    ResolutionLevel,
    RESOLUTION_ORDER,
)


@dataclass(frozen=True)
class CompressionPlan:
    """Describes how a memory will be compressed."""

    memory_id: str
    strategy: CompressionType
    source_resolution: ResolutionLevel
    target_resolution: ResolutionLevel
    preserve_evidence: bool = True
    merge_with: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


def compress_redundancy(
    memories: list[MemoryObject],
) -> list[CompressionPlan]:
    """Plan redundancy compression — merge near-duplicate memories."""
    plans: list[CompressionPlan] = []
    seen: set[str] = set()

    for mem in memories:
        if mem.identifier in seen:
            continue
        for other in memories:
            if other.identifier == mem.identifier or other.identifier in seen:
                continue
            evidence_overlap = (
                len(set(mem.supporting_evidence) & set(other.supporting_evidence))
                / max(len(set(mem.supporting_evidence) | set(other.supporting_evidence)), 1)
            )
            if evidence_overlap > 0.9:
                plans.append(
                    CompressionPlan(
                        memory_id=mem.identifier,
                        strategy=CompressionType.REDUNDANCY,
                        source_resolution=ResolutionLevel.EPISODE,
                        target_resolution=ResolutionLevel.EVIDENCE,
                        merge_with=(other.identifier,),
                    )
                )
                seen.add(other.identifier)
                break
    return plans


def compress_conversation(
    memories: list[MemoryObject],
) -> list[CompressionPlan]:
    """Plan conversation compression — summarize raw conversation memories."""
    plans: list[CompressionPlan] = []
    for mem in memories:
        if mem.temporal_scope == 'momentary' and mem.memory_type == 'episodic':
            plans.append(
                CompressionPlan(
                    memory_id=mem.identifier,
                    strategy=CompressionType.CONVERSATION,
                    source_resolution=ResolutionLevel.RAW_CONVERSATION,
                    target_resolution=ResolutionLevel.EPISODE_SUMMARY,
                )
            )
    return plans


def compress_episode(
    memories: list[MemoryObject],
) -> list[CompressionPlan]:
    """Plan episode compression — collapse old episodes into summaries."""
    plans: list[CompressionPlan] = []
    now = datetime.now(UTC)
    for mem in memories:
        age_days = (now - mem.last_updated).total_seconds() / 86400
        if age_days > 30 and mem.memory_type == 'episodic':
            plans.append(
                CompressionPlan(
                    memory_id=mem.identifier,
                    strategy=CompressionType.EPISODE,
                    source_resolution=ResolutionLevel.EPISODE,
                    target_resolution=ResolutionLevel.EPISODE_SUMMARY,
                )
            )
    return plans


def compress_semantic(
    memories: list[MemoryObject],
) -> list[CompressionPlan]:
    """Plan semantic compression — generalize specific memories."""
    plans: list[CompressionPlan] = []
    for mem in memories:
        if mem.memory_type == 'semantic_personal' and mem.importance_score < 0.3:
            plans.append(
                CompressionPlan(
                    memory_id=mem.identifier,
                    strategy=CompressionType.SEMANTIC,
                    source_resolution=ResolutionLevel.EPISODE_SUMMARY,
                    target_resolution=ResolutionLevel.LONGITUDINAL_TRAJECTORY,
                )
            )
    return plans


def compress_graph(
    memories: list[MemoryObject],
) -> list[CompressionPlan]:
    """Plan graph compression — prune weak graph connections."""
    plans: list[CompressionPlan] = []
    for mem in memories:
        if len(mem.associated_cognitive_objects) > 10 and mem.confidence < 0.3:
            plans.append(
                CompressionPlan(
                    memory_id=mem.identifier,
                    strategy=CompressionType.GRAPH,
                    source_resolution=ResolutionLevel.EPISODE_SUMMARY,
                    target_resolution=ResolutionLevel.IDENTITY_LEVEL_UNDERSTANDING,
                )
            )
    return plans


STRATEGY_FUNCTIONS = {
    CompressionType.REDUNDANCY: compress_redundancy,
    CompressionType.CONVERSATION: compress_conversation,
    CompressionType.EPISODE: compress_episode,
    CompressionType.SEMANTIC: compress_semantic,
    CompressionType.GRAPH: compress_graph,
}


def plan_compression(
    memories: list[MemoryObject],
    strategies: list[CompressionType] | None = None,
) -> list[CompressionPlan]:
    """Run all (or selected) compression strategies and return combined plans."""
    if strategies is None:
        strategies = list(CompressionType)

    all_plans: list[CompressionPlan] = []
    for strat in strategies:
        fn = STRATEGY_FUNCTIONS.get(strat)
        if fn is not None:
            all_plans.extend(fn(memories))

    return all_plans
