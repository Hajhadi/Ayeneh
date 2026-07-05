"""MEM-08 Forgetting / Compression engine.

Implements the pipeline: ExistingMemories → UsageAnalysis → ImportanceAnalysis
→ RedundancyDetection → CompressionCandidate → EvidencePreservation
→ KnowledgeCompression → GraphUpdate → RetrievalOptimization.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.forgetting.types import (
    AdaptiveForgettingTier,
    CompressionCandidate,
    CompressionObject,
    CompressionType,
    ForgettingPipelineStage,
    ForgettingResult,
    RedundancyPair,
    ResolutionLevel,
    RESOLUTION_ORDER,
    TIER_THRESHOLDS,
    UsageRecord,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Usage analysis
# ---------------------------------------------------------------------------

def analyse_usage(memory: MemoryObject) -> UsageRecord:
    """Compute usage statistics for a memory."""
    access_count = len(memory.associated_conversations) + len(memory.associated_episodes)
    age_days = (datetime.now(UTC) - memory.last_updated).total_seconds() / 86400

    # Frequency score: combination of access count and recency
    recency_factor = max(0.0, 1.0 - min(age_days / 90.0, 1.0))
    access_factor = min(1.0, access_count / 10.0)
    frequency_score = recency_factor * 0.6 + access_factor * 0.4

    return UsageRecord(
        memory_id=memory.identifier,
        access_count=access_count,
        last_accessed=memory.last_updated,
        access_frequency_score=frequency_score,
        context_diversity=len(memory.associated_projects),
    )


def classify_tier(frequency_score: float) -> AdaptiveForgettingTier:
    """Classify a memory into an adaptive-forgetting tier."""
    for tier, (low, high) in TIER_THRESHOLDS.items():
        if low <= frequency_score <= high:
            return tier
    return AdaptiveForgettingTier.HISTORICAL_ONLY


# ---------------------------------------------------------------------------
# Stage 2: Importance analysis
# ---------------------------------------------------------------------------

def analyse_importance(memory: MemoryObject) -> float:
    """Compute a composite importance score."""
    base = memory.importance_score
    confidence_boost = memory.confidence * 0.2
    lifecycle_boost = {
        'level_0_ephemeral': 0.0,
        'level_1_candidate': 0.0,
        'level_2_probable': 0.05,
        'level_3_stable': 0.1,
        'level_4_core': 0.2,
    }.get(memory.lifecycle_status, 0.0)
    return min(1.0, base + confidence_boost + lifecycle_boost)


# ---------------------------------------------------------------------------
# Stage 3: Redundancy detection
# ---------------------------------------------------------------------------

def detect_redundancy(
    memories: list[MemoryObject],
    similarity_threshold: float = 0.8,
) -> list[RedundancyPair]:
    """Detect pairs of memories that are redundant.

    Uses a simple heuristic based on supporting evidence overlap and type
    similarity. A production system would use embedding similarity.
    """
    pairs: list[RedundancyPair] = []
    for i, mem_a in enumerate(memories):
        for mem_b in memories[i + 1:]:
            evidence_a = set(mem_a.supporting_evidence)
            evidence_b = set(mem_b.supporting_evidence)
            if not evidence_a or not evidence_b:
                continue
            overlap = len(evidence_a & evidence_b) / max(len(evidence_a | evidence_b), 1)
            type_match = 1.0 if mem_a.memory_type == mem_b.memory_type else 0.0
            similarity = overlap * 0.7 + type_match * 0.3

            if similarity >= similarity_threshold:
                pairs.append(
                    RedundancyPair(
                        memory_a=mem_a.identifier,
                        memory_b=mem_b.identifier,
                        similarity=similarity,
                        recommended_action='merge' if overlap > 0.9 else 'compress',
                    )
                )
    return pairs


# ---------------------------------------------------------------------------
# Stage 4: Compression candidate generation
# ---------------------------------------------------------------------------

def generate_candidates(
    memories: list[MemoryObject],
    usage_records: dict[str, UsageRecord],
    redundancy_pairs: list[RedundancyPair],
) -> list[CompressionCandidate]:
    """Generate compression candidates based on usage, importance, and redundancy."""
    candidates: list[CompressionCandidate] = []
    redundant_ids = set()
    for pair in redundancy_pairs:
        redundant_ids.add(pair.memory_a)
        redundant_ids.add(pair.memory_b)

    for mem in memories:
        usage = usage_records.get(mem.identifier)
        if usage is None:
            continue

        tier = classify_tier(usage.access_frequency_score)
        importance = analyse_importance(mem)

        # Only flag memories that are dormant or lower and low-importance
        if tier in (AdaptiveForgettingTier.DORMANT, AdaptiveForgettingTier.ARCHIVED, AdaptiveForgettingTier.HISTORICAL_ONLY):
            if importance < 0.5:
                candidates.append(
                    CompressionCandidate(
                        memory_id=mem.identifier,
                        compression_type=CompressionType.EPISODE,
                        priority=1.0 - importance,
                        rationale=f'Tier={tier.value}, importance={importance:.2f}',
                    )
                )
        elif mem.identifier in redundant_ids:
            candidates.append(
                CompressionCandidate(
                    memory_id=mem.identifier,
                    compression_type=CompressionType.REDUNDANCY,
                    priority=0.5,
                    rationale='Redundancy detected',
                )
            )

    return sorted(candidates, key=lambda c: c.priority, reverse=True)


# ---------------------------------------------------------------------------
# Stage 5: Evidence preservation
# ---------------------------------------------------------------------------

def preserve_evidence(memory: MemoryObject) -> dict[str, Any]:
    """Extract evidence that must survive compression."""
    return {
        'memory_id': memory.identifier,
        'evidence_ids': list(memory.supporting_evidence),
        'confidence': memory.confidence,
        'importance': memory.importance_score,
        'lifecycle': memory.lifecycle_status,
    }


# ---------------------------------------------------------------------------
# Stage 6: Knowledge compression
# ---------------------------------------------------------------------------

def compress_memory(
    memory: MemoryObject,
    candidate: CompressionCandidate,
    preserved_evidence: dict[str, Any],
) -> CompressionObject:
    """Produce a compression record for a memory."""
    # Calculate information reduced — higher for lower-resolution targets
    source_idx = RESOLUTION_ORDER.index(candidate.current_resolution) if candidate.current_resolution in RESOLUTION_ORDER else 0
    target_idx = RESOLUTION_ORDER.index(candidate.target_resolution) if candidate.target_resolution in RESOLUTION_ORDER else len(RESOLUTION_ORDER) - 1
    total_levels = len(RESOLUTION_ORDER) - 1
    info_reduced = (target_idx - source_idx) / total_levels if total_levels > 0 else 0.0
    info_reduced = max(0.0, min(1.0, info_reduced))

    return CompressionObject(
        compression_identifier=f'compress_{memory.identifier}_{int(datetime.now(UTC).timestamp())}',
        affected_memory_objects=(memory.identifier,),
        compression_strategy=candidate.compression_type,
        reason=candidate.rationale,
        supporting_evidence=tuple(preserved_evidence.get('evidence_ids', [])),
        knowledge_preserved=f'Confidence={preserved_evidence.get("confidence", 0):.2f}; Importance={preserved_evidence.get("importance", 0):.2f}',
        information_reduced=info_reduced,
        recoverability_status='recoverable',
        explainability_metadata={'candidate_priority': candidate.priority},
    )


# ---------------------------------------------------------------------------
# Full pipeline orchestrator
# ---------------------------------------------------------------------------

class ForgettingEngine:
    """Orchestrates the full MEM-08 forgetting / compression pipeline."""

    def __init__(self, redundancy_threshold: float = 0.8) -> None:
        self.redundancy_threshold = redundancy_threshold

    def run(
        self,
        memories: list[MemoryObject],
        max_compressions: int = 50,
    ) -> ForgettingResult:
        """Execute the full forgetting pipeline."""
        logger.info('forgetting_pipeline.start', memory_count=len(memories))

        # 1. Usage analysis
        usage_records: dict[str, UsageRecord] = {}
        for mem in memories:
            usage_records[mem.identifier] = analyse_usage(mem)

        # 2. (Importance is analysed per-candidate in generate_candidates)

        # 3. Redundancy detection
        redundancy_pairs = detect_redundancy(memories, self.redundancy_threshold)

        # 4. Generate compression candidates
        candidates = generate_candidates(memories, usage_records, redundancy_pairs)
        candidates = candidates[:max_compressions]

        # 5-6. Preserve evidence and compress
        compressions: list[CompressionObject] = []
        for cand in candidates:
            mem = next((m for m in memories if m.identifier == cand.memory_id), None)
            if mem is None:
                continue
            evidence = preserve_evidence(mem)
            compression = compress_memory(mem, cand, evidence)
            compressions.append(compression)

        total_info_reduced = sum(c.information_reduced for c in compressions)

        logger.info(
            'forgetting_pipeline.complete',
            compressions=len(compressions),
            info_reduced=total_info_reduced,
        )

        return ForgettingResult(
            compression_identifier=f'batch_{int(datetime.now(UTC).timestamp())}',
            compressions_applied=tuple(compressions),
            memories_affected=len(compressions),
            information_reduced=total_info_reduced,
            recoverable=True,
        )
