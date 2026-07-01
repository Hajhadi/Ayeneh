"""Memory evolution service — domain model, persistence, lineage, audit, and algorithms.

Phase 1: CRUD for evolution records, lineage tracking, history, metrics.
Phase 2: Semantic merge, contradiction detection, strengthening, weakening,
         confidence evolution, importance evolution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain enums
# ---------------------------------------------------------------------------

class EvolutionType(StrEnum):
    CREATED = "created"
    SUPERSEDED = "superseded"
    MERGED = "merged"
    CONFIDENCE_UPDATED = "confidence_updated"
    IMPORTANCE_UPDATED = "importance_updated"
    STATUS_CHANGED = "status_changed"
    CONTRADICTION_LINKED = "contradiction_linked"


class EvolutionReason(StrEnum):
    USER_CORRECTION = "user_correction"
    CONTRADICTION = "contradiction"
    DEDUPLICATION = "deduplication"
    MERGE = "merge"
    AGING = "aging"
    REINFORCEMENT = "reinforcement"
    EXPIRATION = "expiration"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class EvolutionConfig:
    merge_similarity_threshold: float = 0.80
    contradiction_similarity_threshold: float = 0.60
    strengthen_boost: float = 0.05
    strengthen_max_confidence: float = 1.0
    weaken_factor: float = 0.03
    weaken_min_confidence: float = 0.05
    stale_days_threshold: int = 90
    importance_boost: float = 0.03
    importance_decay_factor: float = 0.95
    importance_max: float = 1.0
    importance_min: float = 0.0


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------

@dataclass
class MemoryEvolutionRecord:
    id: uuid.UUID
    memory_id: uuid.UUID
    user_id: uuid.UUID
    evolution_type: str
    reason: str
    old_content: str | None = None
    new_content: str | None = None
    old_confidence: float | None = None
    new_confidence: float | None = None
    old_importance: float | None = None
    new_importance: float | None = None
    source_memory_ids: list[uuid.UUID] = field(default_factory=list)
    detail: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MemoryLineage:
    id: uuid.UUID
    ancestor_id: uuid.UUID
    descendant_id: uuid.UUID
    relation: str
    depth: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EvolutionSnapshot:
    """Lightweight snapshot of a memory for algorithm processing."""

    id: uuid.UUID
    user_id: uuid.UUID
    content: str
    memory_type: str
    confidence: float
    importance: float
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class EvolutionResult:
    """Outcome of an evolution batch run."""

    merges: int = 0
    contradictions: int = 0
    strengthened: int = 0
    weakened: int = 0
    confidence_updates: int = 0
    importance_updates: int = 0
    duration_ms: float = 0.0


@dataclass
class MemoryEvolutionMetrics:
    total_records: int = 0
    records_by_type: dict[str, int] = field(default_factory=dict)
    records_by_reason: dict[str, int] = field(default_factory=dict)
    unique_memories_evolved: int = 0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MemoryEvolutionService:
    """Single owner of all memory evolution domain logic and persistence.

    Provides:
    - CRUD for evolution records (Phase 1)
    - Lineage tracking (Phase 1)
    - History retrieval and metrics (Phase 1)
    - Semantic merge (Phase 2)
    - Contradiction detection (Phase 2)
    - Strengthening (Phase 2)
    - Weakening (Phase 2)
    - Confidence evolution (Phase 2)
    - Importance evolution (Phase 2)
    """

    def __init__(self, uow_factory: Any, config: EvolutionConfig | None = None) -> None:
        self._uow_factory = uow_factory
        self._config = config or EvolutionConfig()

    # ══════════════════════════════════════════════════════════════════════
    # Phase 2 — Evolution algorithms
    # ══════════════════════════════════════════════════════════════════════

    async def run_consolidation(self, user_id: str) -> EvolutionResult:
        """Run the full consolidation pipeline for a user.

        Executes: merge → contradiction → strengthen → weaken → importance.
        Each step is idempotent.
        """
        result = EvolutionResult()
        start = datetime.now(UTC)

        snapshots = await self._load_active_snapshots(user_id)

        merges = await self._run_merge(snapshots, user_id)
        result.merges = merges

        contradictions = await self._run_contradiction_detection(snapshots, user_id)
        result.contradictions = contradictions

        strengthened = await self._run_strengthening(snapshots, user_id)
        result.strengthened = strengthened

        weakened = await self._run_weakening(snapshots, user_id)
        result.weakened = weakened

        imp_updates = await self._run_importance_evolution(snapshots, user_id)
        result.importance_updates = imp_updates

        elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
        result.duration_ms = round(elapsed, 2)

        logger.info("consolidation_complete", user_id=user_id, **vars(result))
        return result

    # ── Semantic merge ──

    async def merge_memories(
        self,
        memory_ids: list[str],
        user_id: str,
    ) -> str:
        """Merge two or more memories into one. Preserves provenance and lineage.

        Returns the ID of the merged memory. Idempotent: if all source memories
        are already superseded, returns the merged descendant.
        """
        snapshots = [await self._get_snapshot(mid) for mid in memory_ids]
        snapshots = [s for s in snapshots if s is not None]
        active = [s for s in snapshots if s.status == "active"]

        if len(active) < 2:
            for s in snapshots:
                if s.status == "superseded" and s.id:
                    desc = await self.get_descendants(str(s.id))
                    merged = [d for d in desc if d.relation == "merged_into"]
                    if merged:
                        return str(merged[0].descendant_id)
            raise ValueError("Need at least 2 active memories to merge")

        merged_content = " | ".join(s.content for s in snapshots)
        merged_confidence = max(s.confidence for s in snapshots)
        merged_importance = max(s.importance for s in snapshots)
        merged_id = uuid.uuid4()

        await self._create_merged_memory(merged_id, snapshots[0], merged_content, merged_confidence, merged_importance)

        for snap in snapshots:
            await self._mark_superseded(str(snap.id), str(merged_id))
            await self._record_evolution_event(
                str(snap.id), user_id,
                EvolutionType.MERGED, EvolutionReason.MERGE,
                old_content=snap.content, new_content=merged_content,
                old_confidence=snap.confidence, new_confidence=merged_confidence,
                old_importance=snap.importance, new_importance=merged_importance,
                source_memory_ids=[str(s.id) for s in snapshots],
                detail=f"Merged {len(snapshots)} memories into {merged_id}",
            )
            await self.add_lineage(str(snap.id), str(merged_id), "merged_into")

        logger.info("memories_merged", count=len(snapshots), merged_id=str(merged_id))
        return str(merged_id)

    async def detect_and_merge_similar(self, user_id: str) -> int:
        """Scan active memories for semantic duplicates and merge them.

        Returns the number of merge groups processed. Idempotent.
        """
        snapshots = await self._load_active_snapshots(user_id)
        by_type: dict[str, list[EvolutionSnapshot]] = {}
        for s in snapshots:
            by_type.setdefault(s.memory_type, []).append(s)

        merged_ids: set[str] = set()
        merge_count = 0

        for _mem_type, group in by_type.items():
            for i in range(len(group)):
                if str(group[i].id) in merged_ids:
                    continue
                candidates = [group[i]]
                for j in range(i + 1, len(group)):
                    if str(group[j].id) in merged_ids:
                        continue
                    sim = self._jaccard_similarity(group[i].content, group[j].content)
                    if sim >= self._config.merge_similarity_threshold:
                        candidates.append(group[j])
                        merged_ids.add(str(group[j].id))
                if len(candidates) > 1:
                    ids = [str(c.id) for c in candidates]
                    await self.merge_memories(ids, user_id)
                    merge_count += 1

        return merge_count

    # ── Contradiction detection ──

    async def detect_contradictions(self, user_id: str) -> int:
        """Find pairs of active memories that contradict each other.

        Never deletes either memory. Creates a contradiction lineage link
        and lowers confidence on both. Returns the number of contradictions found.
        """
        snapshots = await self._load_active_snapshots(user_id)
        by_type: dict[str, list[EvolutionSnapshot]] = {}
        for s in snapshots:
            by_type.setdefault(s.memory_type, []).append(s)

        contradiction_count = 0

        for _mem_type, group in by_type.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    sim = self._jaccard_similarity(group[i].content, group[j].content)
                    if sim < self._config.contradiction_similarity_threshold:
                        continue
                    if sim >= self._config.merge_similarity_threshold:
                        continue
                    if self._has_negation_shift(group[i].content, group[j].content):
                        for snap in (group[i], group[j]):
                            await self.weaken_confidence(
                                str(snap.id), user_id,
                                self._config.weaken_factor,
                                reason=EvolutionReason.CONTRADICTION,
                                detail=f"Contradicts {group[j].id if snap.id == group[i].id else group[i].id}",
                            )
                        await self.add_lineage(
                            str(group[i].id), str(group[j].id),
                            "contradicts",
                        )
                        contradiction_count += 1

        return contradiction_count

    # ── Strengthening ──

    async def strengthen_memory(
        self,
        memory_id: str,
        user_id: str,
        boost: float | None = None,
    ) -> MemoryEvolutionRecord:
        """Increase confidence for a memory supported by new evidence.

        Idempotent: repeated calls increase monotonically until ceiling.
        """
        boost = boost or self._config.strengthen_boost
        snap = await self._get_snapshot(memory_id)
        if snap is None or snap.status != "active":
            raise ValueError(f"Memory {memory_id} not found or inactive")

        old_conf = snap.confidence
        new_conf = min(self._config.strengthen_max_confidence, old_conf + boost)
        if new_conf == old_conf:
            return await self._record_evolution_event(
                memory_id, user_id,
                EvolutionType.CONFIDENCE_UPDATED, EvolutionReason.REINFORCEMENT,
                old_confidence=old_conf, new_confidence=new_conf,
                detail="Already at max confidence",
            )

        await self._set_confidence(memory_id, new_conf)
        await self._append_confidence_history(memory_id, new_conf)
        return await self._record_evolution_event(
            memory_id, user_id,
            EvolutionType.CONFIDENCE_UPDATED, EvolutionReason.REINFORCEMENT,
            old_confidence=old_conf, new_confidence=new_conf,
            detail=f"Strengthened by {boost:.3f}",
        )

    async def _run_strengthening(self, snapshots: list[EvolutionSnapshot], user_id: str) -> int:
        """Batch strengthening for recent, frequently-accessed memories."""
        now = datetime.now(UTC)
        count = 0
        for snap in snapshots:
            age_days = self._age_days(snap.created_at, now)
            if age_days <= 30 and snap.confidence < self._config.strengthen_max_confidence:
                old_conf = snap.confidence
                new_conf = min(self._config.strengthen_max_confidence, old_conf + self._config.strengthen_boost)
                if new_conf > old_conf:
                    await self._set_confidence(str(snap.id), new_conf)
                    await self._append_confidence_history(str(snap.id), new_conf)
                    await self._record_evolution_event(
                        str(snap.id), user_id,
                        EvolutionType.CONFIDENCE_UPDATED, EvolutionReason.REINFORCEMENT,
                        old_confidence=old_conf, new_confidence=new_conf,
                        detail="Auto-strengthened recent memory",
                    )
                    count += 1
        return count

    # ── Weakening ──

    async def weaken_confidence(
        self,
        memory_id: str,
        user_id: str,
        factor: float | None = None,
        *,
        reason: str = EvolutionReason.AGING,
        detail: str = "",
    ) -> MemoryEvolutionRecord:
        """Decrease confidence for a memory. Never produces negative confidence.

        Idempotent: confidence floors at configured minimum.
        """
        factor = factor or self._config.weaken_factor
        snap = await self._get_snapshot(memory_id)
        if snap is None or snap.status != "active":
            raise ValueError(f"Memory {memory_id} not found or inactive")

        old_conf = snap.confidence
        new_conf = max(self._config.weaken_min_confidence, old_conf - factor)
        if new_conf == old_conf:
            return await self._record_evolution_event(
                memory_id, user_id,
                EvolutionType.CONFIDENCE_UPDATED, reason,
                old_confidence=old_conf, new_confidence=new_conf,
                detail="Already at min confidence",
            )

        await self._set_confidence(memory_id, new_conf)
        await self._append_confidence_history(memory_id, new_conf)
        return await self._record_evolution_event(
            memory_id, user_id,
            EvolutionType.CONFIDENCE_UPDATED, reason,
            old_confidence=old_conf, new_confidence=new_conf,
            detail=detail or f"Weakened by {factor:.3f}",
        )

    async def _run_weakening(self, snapshots: list[EvolutionSnapshot], user_id: str) -> int:
        """Batch weakening for stale memories past the staleness threshold."""
        now = datetime.now(UTC)
        count = 0
        for snap in snapshots:
            age_days = self._age_days(snap.updated_at, now)
            if age_days > self._config.stale_days_threshold:
                old_conf = snap.confidence
                new_conf = max(self._config.weaken_min_confidence, old_conf - self._config.weaken_factor)
                if new_conf < old_conf:
                    await self._set_confidence(str(snap.id), new_conf)
                    await self._append_confidence_history(str(snap.id), new_conf)
                    await self._record_evolution_event(
                        str(snap.id), user_id,
                        EvolutionType.CONFIDENCE_UPDATED, EvolutionReason.AGING,
                        old_confidence=old_conf, new_confidence=new_conf,
                        detail=f"Stale memory ({age_days:.0f} days)",
                    )
                    count += 1
        return count

    # ── Importance evolution ──

    async def boost_importance(
        self,
        memory_id: str,
        user_id: str,
        boost: float | None = None,
    ) -> MemoryEvolutionRecord:
        """Increase importance when a memory receives behavioral evidence."""
        boost = boost or self._config.importance_boost
        snap = await self._get_snapshot(memory_id)
        if snap is None:
            raise ValueError(f"Memory {memory_id} not found")

        old_imp = snap.importance
        new_imp = min(self._config.importance_max, old_imp + boost)
        await self._set_importance(memory_id, new_imp)
        await self._append_importance_history(memory_id, new_imp)
        return await self._record_evolution_event(
            memory_id, user_id,
            EvolutionType.IMPORTANCE_UPDATED, EvolutionReason.REINFORCEMENT,
            old_importance=old_imp, new_importance=new_imp,
            detail=f"Importance boosted by {boost:.3f}",
        )

    async def decay_importance(
        self,
        memory_id: str,
        user_id: str,
        factor: float | None = None,
    ) -> MemoryEvolutionRecord:
        """Decrease importance for obsolete memories."""
        factor = factor or self._config.importance_decay_factor
        snap = await self._get_snapshot(memory_id)
        if snap is None:
            raise ValueError(f"Memory {memory_id} not found")

        old_imp = snap.importance
        new_imp = max(self._config.importance_min, old_imp * factor)
        await self._set_importance(memory_id, new_imp)
        await self._append_importance_history(memory_id, new_imp)
        return await self._record_evolution_event(
            memory_id, user_id,
            EvolutionType.IMPORTANCE_UPDATED, EvolutionReason.EXPIRATION,
            old_importance=old_imp, new_importance=new_imp,
            detail=f"Importance decayed by factor {factor:.3f}",
        )

    async def _run_importance_evolution(self, snapshots: list[EvolutionSnapshot], user_id: str) -> int:
        """Batch importance adjustment: boost recent, decay old."""
        now = datetime.now(UTC)
        count = 0
        for snap in snapshots:
            age_days = self._age_days(snap.created_at, now)
            old_imp = snap.importance

            if age_days <= 30 and old_imp < self._config.importance_max:
                new_imp = min(self._config.importance_max, old_imp + self._config.importance_boost)
                if new_imp > old_imp:
                    await self._set_importance(str(snap.id), new_imp)
                    await self._append_importance_history(str(snap.id), new_imp)
                    await self._record_evolution_event(
                        str(snap.id), user_id,
                        EvolutionType.IMPORTANCE_UPDATED, EvolutionReason.REINFORCEMENT,
                        old_importance=old_imp, new_importance=new_imp,
                        detail="Auto-boosted recent memory importance",
                    )
                    count += 1

            elif age_days > self._config.stale_days_threshold and old_imp > self._config.importance_min:
                new_imp = max(self._config.importance_min, old_imp * self._config.importance_decay_factor)
                if new_imp < old_imp:
                    await self._set_importance(str(snap.id), new_imp)
                    await self._append_importance_history(str(snap.id), new_imp)
                    await self._record_evolution_event(
                        str(snap.id), user_id,
                        EvolutionType.IMPORTANCE_UPDATED, EvolutionReason.EXPIRATION,
                        old_importance=old_imp, new_importance=new_imp,
                        detail=f"Auto-decayed importance ({age_days:.0f} days old)",
                    )
                    count += 1
        return count

    # ── Confidence evolution (append-only history) ──

    async def evolve_confidence(
        self,
        memory_id: str,
        user_id: str,
        new_confidence: float,
        reason: str = EvolutionReason.MANUAL,
    ) -> MemoryEvolutionRecord:
        """Set a new confidence value. History is append-only.

        Every call creates an evolution record.
        """
        snap = await self._get_snapshot(memory_id)
        if snap is None:
            raise ValueError(f"Memory {memory_id} not found")

        old_conf = snap.confidence
        clamped = max(self._config.weaken_min_confidence, min(self._config.strengthen_max_confidence, new_confidence))
        await self._set_confidence(memory_id, clamped)
        await self._append_confidence_history(memory_id, clamped)
        return await self._record_evolution_event(
            memory_id, user_id,
            EvolutionType.CONFIDENCE_UPDATED, reason,
            old_confidence=old_conf, new_confidence=clamped,
            detail=f"Confidence evolved {old_conf:.3f} → {clamped:.3f}",
        )

    # ══════════════════════════════════════════════════════════════════════
    # Phase 1 — CRUD for evolution records
    # ══════════════════════════════════════════════════════════════════════

    async def record_evolution(
        self,
        memory_id: str,
        user_id: str,
        evolution_type: str,
        reason: str,
        *,
        old_content: str | None = None,
        new_content: str | None = None,
        old_confidence: float | None = None,
        new_confidence: float | None = None,
        old_importance: float | None = None,
        new_importance: float | None = None,
        source_memory_ids: list[str] | None = None,
        detail: str = "",
    ) -> MemoryEvolutionRecord:
        return await self._record_evolution_event(
            memory_id, user_id, evolution_type, reason,
            old_content=old_content, new_content=new_content,
            old_confidence=old_confidence, new_confidence=new_confidence,
            old_importance=old_importance, new_importance=new_importance,
            source_memory_ids=source_memory_ids, detail=detail,
        )

    async def get_evolution_history(
        self, memory_id: str, *, limit: int = 100
    ) -> list[MemoryEvolutionRecord]:
        async with self._uow_factory() as uow:
            models = await uow.memory_evolution_events.list_by_memory(
                uuid.UUID(memory_id), limit=limit
            )
            return [self._model_to_record(m) for m in models]

    async def get_user_evolution_history(
        self, user_id: str, *, limit: int = 100
    ) -> list[MemoryEvolutionRecord]:
        async with self._uow_factory() as uow:
            models = await uow.memory_evolution_events.list_by_user(
                uuid.UUID(user_id), limit=limit
            )
            return [self._model_to_record(m) for m in models]

    async def count_evolutions_by_type(
        self, user_id: str, evolution_type: str
    ) -> int:
        async with self._uow_factory() as uow:
            return await uow.memory_evolution_events.count_by_type(
                uuid.UUID(user_id), evolution_type
            )

    # ── Lineage CRUD ──

    async def add_lineage(
        self,
        ancestor_id: str,
        descendant_id: str,
        relation: str,
        depth: int = 1,
    ) -> MemoryLineage:
        from ayeneh.infrastructure.persistence.models.memory_evolution import MemoryLineageModel

        now = datetime.now(UTC)
        lineage = MemoryLineage(
            id=uuid.uuid4(),
            ancestor_id=uuid.UUID(ancestor_id),
            descendant_id=uuid.UUID(descendant_id),
            relation=relation,
            depth=depth,
            created_at=now,
        )

        async with self._uow_factory() as uow:
            existing = await uow.memory_lineage.find_relation(
                lineage.ancestor_id, lineage.descendant_id
            )
            if existing:
                return MemoryLineage(
                    id=existing.id,
                    ancestor_id=existing.parent_id,
                    descendant_id=existing.child_id,
                    relation=existing.relation,
                    depth=1,
                    created_at=existing.created_at,
                )

            model = MemoryLineageModel(
                id=lineage.id,
                parent_id=lineage.ancestor_id,
                child_id=lineage.descendant_id,
                relation=lineage.relation,
                created_at=now,
            )
            await uow.memory_lineage.create(model)
            await uow.commit()

        return lineage

    async def get_descendants(self, memory_id: str) -> list[MemoryLineage]:
        async with self._uow_factory() as uow:
            models = await uow.memory_lineage.get_children(uuid.UUID(memory_id))
            return [
                MemoryLineage(
                    id=m.id, ancestor_id=m.parent_id, descendant_id=m.child_id,
                    relation=m.relation, depth=1, created_at=m.created_at,
                )
                for m in models
            ]

    async def get_ancestors(self, memory_id: str) -> list[MemoryLineage]:
        async with self._uow_factory() as uow:
            models = await uow.memory_lineage.get_parents(uuid.UUID(memory_id))
            return [
                MemoryLineage(
                    id=m.id, ancestor_id=m.parent_id, descendant_id=m.child_id,
                    relation=m.relation, depth=1, created_at=m.created_at,
                )
                for m in models
            ]

    async def get_full_lineage(self, memory_id: str) -> dict[str, list[MemoryLineage]]:
        return {
            "ancestors": await self.get_ancestors(memory_id),
            "descendants": await self.get_descendants(memory_id),
        }

    # ── Memory model evolution field updates ──

    async def update_evolution_fields(
        self,
        memory_id: str,
        *,
        parent_memory_id: str | None = None,
        evolution_version: int | None = None,
        confidence_history: dict | None = None,
        importance_history: dict | None = None,
    ) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model is None:
                return
            if parent_memory_id is not None:
                model.parent_memory_id = uuid.UUID(parent_memory_id)
            if evolution_version is not None:
                model.evolution_version = evolution_version
            if confidence_history is not None:
                model.confidence_history = confidence_history
            if importance_history is not None:
                model.importance_history = importance_history
            model.last_evolved_at = datetime.now(UTC)
            await uow.memories.update(model)
            await uow.commit()

    # ── Observability ──

    async def get_metrics(self, user_id: str) -> MemoryEvolutionMetrics:
        async with self._uow_factory() as uow:
            all_events = await uow.memory_evolution_events.list_by_user(
                uuid.UUID(user_id), limit=10000
            )
            metrics = MemoryEvolutionMetrics(total_records=len(all_events))
            seen_memory_ids: set[uuid.UUID] = set()
            for e in all_events:
                metrics.records_by_type[e.event_type] = (
                    metrics.records_by_type.get(e.event_type, 0) + 1
                )
                seen_memory_ids.add(e.memory_id)
            metrics.unique_memories_evolved = len(seen_memory_ids)
            return metrics

    # ══════════════════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    @staticmethod
    def _has_negation_shift(a: str, b: str) -> bool:
        negations = {"not", "never", "no", "don't", "doesn't", "didn't", "won't", "can't"}
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        neg_a = bool(words_a & negations)
        neg_b = bool(words_b & negations)
        if neg_a != neg_b:
            shared = (words_a - negations) & (words_b - negations)
            if len(shared) >= 2:
                return True
        return False

    @staticmethod
    def _age_days(dt: datetime, now: datetime) -> float:
        if dt.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        elif dt.tzinfo is None and now.tzinfo is not None:
            dt = dt.replace(tzinfo=UTC)
        return max((now - dt).total_seconds() / 86400, 0)

    async def _load_active_snapshots(self, user_id: str) -> list[EvolutionSnapshot]:
        async with self._uow_factory() as uow:
            from ayeneh.infrastructure.persistence.models.memory import MemoryModel
            from sqlalchemy import select
            stmt = select(MemoryModel).where(
                MemoryModel.user_id == uuid.UUID(user_id),
                MemoryModel.status == "active",
            ).limit(2000)
            result = await uow._session.execute(stmt)
            models = list(result.scalars().all())
            return [
                EvolutionSnapshot(
                    id=m.id, user_id=m.user_id, content=m.content,
                    memory_type=m.type, confidence=m.confidence,
                    importance=getattr(m, "importance", 0.5),
                    status=m.status, created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in models
            ]

    async def _get_snapshot(self, memory_id: str) -> EvolutionSnapshot | None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model is None:
                return None
            return EvolutionSnapshot(
                id=model.id, user_id=model.user_id, content=model.content,
                memory_type=model.type, confidence=model.confidence,
                importance=getattr(model, "importance", 0.5),
                status=model.status, created_at=model.created_at,
                updated_at=model.updated_at,
            )

    async def _set_confidence(self, memory_id: str, value: float) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model:
                model.confidence = value
                model.evolution_version += 1
                model.last_evolved_at = datetime.now(UTC)
                await uow.memories.update(model)
                await uow.commit()

    async def _set_importance(self, memory_id: str, value: float) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model:
                model.evolution_version += 1
                model.last_evolved_at = datetime.now(UTC)
                await uow.memories.update(model)
                await uow.commit()

    async def _append_confidence_history(self, memory_id: str, value: float) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model:
                history = model.confidence_history or {}
                ver = model.evolution_version
                history[f"v{ver}"] = value
                model.confidence_history = history
                await uow.memories.update(model)
                await uow.commit()

    async def _append_importance_history(self, memory_id: str, value: float) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(memory_id))
            if model:
                history = model.importance_history or {}
                ver = model.evolution_version
                history[f"v{ver}"] = value
                model.importance_history = history
                await uow.memories.update(model)
                await uow.commit()

    async def _mark_superseded(self, old_id: str, new_id: str) -> None:
        async with self._uow_factory() as uow:
            model = await uow.memories.get_by_id(uuid.UUID(old_id))
            if model:
                model.status = "superseded"
                model.superseded_by = uuid.UUID(new_id)
                model.updated_at = datetime.now(UTC)
                await uow.memories.update(model)
                await uow.commit()

    async def _create_merged_memory(
        self, new_id: uuid.UUID, template: EvolutionSnapshot,
        content: str, confidence: float, importance: float,
    ) -> None:
        from ayeneh.infrastructure.persistence.models.memory import MemoryModel
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            model = MemoryModel(
                id=new_id, user_id=template.user_id,
                type=template.memory_type, content=content,
                confidence=confidence, source_message_ids=[],
                status="active", created_at=now, updated_at=now,
                importance_history={"initial": importance},
                confidence_history={"initial": confidence},
            )
            await uow.memories.create(model)
            await uow.commit()

    async def _run_merge(self, snapshots: list[EvolutionSnapshot], user_id: str) -> int:
        by_type: dict[str, list[EvolutionSnapshot]] = {}
        for s in snapshots:
            by_type.setdefault(s.memory_type, []).append(s)

        merged_ids: set[str] = set()
        count = 0
        for _mt, group in by_type.items():
            for i in range(len(group)):
                if str(group[i].id) in merged_ids:
                    continue
                candidates = [group[i]]
                for j in range(i + 1, len(group)):
                    if str(group[j].id) in merged_ids:
                        continue
                    sim = self._jaccard_similarity(group[i].content, group[j].content)
                    if sim >= self._config.merge_similarity_threshold:
                        candidates.append(group[j])
                        merged_ids.add(str(group[j].id))
                if len(candidates) > 1:
                    await self.merge_memories([str(c.id) for c in candidates], user_id)
                    count += 1
        return count

    async def _run_contradiction_detection(self, snapshots: list[EvolutionSnapshot], user_id: str) -> int:
        by_type: dict[str, list[EvolutionSnapshot]] = {}
        for s in snapshots:
            by_type.setdefault(s.memory_type, []).append(s)

        count = 0
        for _mt, group in by_type.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    sim = self._jaccard_similarity(group[i].content, group[j].content)
                    if self._config.contradiction_similarity_threshold <= sim < self._config.merge_similarity_threshold:
                        if self._has_negation_shift(group[i].content, group[j].content):
                            for snap in (group[i], group[j]):
                                await self.weaken_confidence(
                                    str(snap.id), user_id,
                                    self._config.weaken_factor,
                                    reason=EvolutionReason.CONTRADICTION,
                                )
                            await self.add_lineage(
                                str(group[i].id), str(group[j].id), "contradicts",
                            )
                            count += 1
        return count

    async def _record_evolution_event(
        self,
        memory_id: str, user_id: str,
        evolution_type: str, reason: str,
        *,
        old_content: str | None = None,
        new_content: str | None = None,
        old_confidence: float | None = None,
        new_confidence: float | None = None,
        old_importance: float | None = None,
        new_importance: float | None = None,
        source_memory_ids: list[str] | None = None,
        detail: str = "",
    ) -> MemoryEvolutionRecord:
        from ayeneh.infrastructure.persistence.models.memory_evolution import MemoryEvolutionEventModel

        now = datetime.now(UTC)
        record = MemoryEvolutionRecord(
            id=uuid.uuid4(),
            memory_id=uuid.UUID(memory_id),
            user_id=uuid.UUID(user_id),
            evolution_type=evolution_type,
            reason=reason,
            old_content=old_content, new_content=new_content,
            old_confidence=old_confidence, new_confidence=new_confidence,
            old_importance=old_importance, new_importance=new_importance,
            source_memory_ids=[uuid.UUID(s) for s in (source_memory_ids or [])],
            detail=detail, created_at=now,
        )

        async with self._uow_factory() as uow:
            model = MemoryEvolutionEventModel(
                id=record.id, memory_id=record.memory_id,
                user_id=record.user_id, event_type=record.evolution_type,
                old_confidence=record.old_confidence,
                new_confidence=record.new_confidence,
                old_importance=record.old_importance,
                new_importance=record.new_importance,
                detail=record.detail, created_at=now,
            )
            await uow.memory_evolution_events.create(model)
            await uow.commit()

        return record

    @staticmethod
    def _model_to_record(m: Any) -> MemoryEvolutionRecord:
        return MemoryEvolutionRecord(
            id=m.id, memory_id=m.memory_id, user_id=m.user_id,
            evolution_type=m.event_type, reason="",
            old_confidence=m.old_confidence, new_confidence=m.new_confidence,
            old_importance=m.old_importance, new_importance=m.new_importance,
            detail=m.detail or "", created_at=m.created_at,
        )
