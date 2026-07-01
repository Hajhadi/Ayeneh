"""Memory engine — manages creation, retrieval, ranking, consolidation, and lifecycle of memories."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ayeneh.application.ports.vector_store import SearchResult

logger = structlog.get_logger(__name__)


class MemoryType(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PATTERN = "pattern"
    REFLECTION = "reflection"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass
class Memory:
    """Domain memory entity."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: MemoryType
    content: str
    confidence: float = 0.5
    source_message_ids: list[uuid.UUID] = field(default_factory=list)
    superseded_by: uuid.UUID | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    embedding_version: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MemoryCreate:
    """Input for creating a new memory."""

    user_id: uuid.UUID
    type: MemoryType
    content: str
    confidence: float = 0.5
    source_message_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass
class MemoryScore:
    """Computed score for a memory during retrieval."""

    memory: Memory
    relevance: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    confidence_score: float = 0.0
    final_score: float = 0.0


@dataclass
class RankingWeights:
    """Weights for combining retrieval scoring dimensions."""

    relevance: float = 0.4
    recency: float = 0.25
    importance: float = 0.2
    confidence: float = 0.15


@dataclass
class ExpirationPolicy:
    """Controls when memories become candidates for consolidation or archival."""

    episodic_ttl_days: int = 90
    semantic_ttl_days: int = 365
    pattern_ttl_days: int = 180
    reflection_ttl_days: int = 365
    min_confidence: float = 0.2
    min_importance: float = 0.1


@dataclass
class ConsolidationResult:
    """Outcome of a consolidation pass."""

    merged: int = 0
    superseded: int = 0
    archived: int = 0
    deduplicated: int = 0


@dataclass
class RetrievalContext:
    """Assembled context returned by memory retrieval."""

    query: str
    episodic: list[Memory] = field(default_factory=list)
    semantic: list[Memory] = field(default_factory=list)
    pattern: list[Memory] = field(default_factory=list)
    reflection: list[Memory] = field(default_factory=list)
    scores: list[MemoryScore] = field(default_factory=list)
    total_tokens_estimate: int = 0


class MemoryRepository:
    """Abstract memory persistence interface used by the service."""

    async def create(self, memory: Memory) -> Memory:
        raise NotImplementedError

    async def get_by_id(self, memory_id: uuid.UUID) -> Memory | None:
        raise NotImplementedError

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        memory_type: MemoryType | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        raise NotImplementedError

    async def update(self, memory: Memory) -> Memory:
        raise NotImplementedError

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        raise NotImplementedError

    async def list_expiring(
        self, user_id: uuid.UUID, before: datetime, limit: int = 100
    ) -> list[Memory]:
        raise NotImplementedError

    async def find_similar_content(
        self, user_id: uuid.UUID, content: str, threshold: float = 0.95
    ) -> list[Memory]:
        raise NotImplementedError


class EmbeddingGateway:
    """Abstract embedding operations used by the memory service."""

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def search_similar(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        raise NotImplementedError

    async def upsert(self, entity_id: uuid.UUID, entity_type: str, text: str) -> None:
        raise NotImplementedError

    async def delete(self, entity_id: uuid.UUID, entity_type: str) -> None:
        raise NotImplementedError

    async def needs_reembedding(self, entity_id: uuid.UUID, entity_type: str) -> bool:
        raise NotImplementedError


@dataclass
class MemoryService:
    """Core memory engine — owns all memory business logic.

    Responsibilities:
    - Store memories with embedding generation
    - Retrieve memories via hybrid search (semantic + metadata)
    - Rank memories using recency, relevance, importance, confidence
    - Consolidate redundant or expiring memories
    - Deduplicate near-identical memories
    - Apply expiration policies
    - Build RetrievalContext objects
    """

    repo: MemoryRepository
    embeddings: EmbeddingGateway
    ranking_weights: RankingWeights = field(default_factory=RankingWeights)
    expiration: ExpirationPolicy = field(default_factory=ExpirationPolicy)
    embedding_entity_type: str = "memory"

    async def store(self, data: MemoryCreate) -> Memory:
        """Create a new memory, embed it, and persist."""
        duplicates = await self.repo.find_similar_content(
            data.user_id, data.content, threshold=0.95
        )
        for existing in duplicates:
            if existing.type == data.type and existing.status == MemoryStatus.ACTIVE:
                existing.confidence = max(existing.confidence, data.confidence)
                existing.updated_at = datetime.now(UTC)
                await self.repo.update(existing)
                await self.embeddings.upsert(existing.id, self.embedding_entity_type, existing.content)
                logger.info("memory_deduplicated", memory_id=str(existing.id))
                return existing

        now = datetime.now(UTC)
        memory = Memory(
            id=uuid.uuid4(),
            user_id=data.user_id,
            type=data.type,
            content=data.content,
            confidence=data.confidence,
            source_message_ids=data.source_message_ids,
            created_at=now,
            updated_at=now,
        )
        memory = await self.repo.create(memory)
        await self.embeddings.upsert(memory.id, self.embedding_entity_type, memory.content)
        logger.info("memory_stored", memory_id=str(memory.id), type=memory.type)
        return memory

    async def store_batch(self, items: list[MemoryCreate]) -> list[Memory]:
        """Create multiple memories in one pass."""
        results: list[Memory] = []
        for item in items:
            results.append(await self.store(item))
        return results

    async def retrieve(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        limit: int = 10,
        memory_types: list[MemoryType] | None = None,
        score_threshold: float = 0.0,
    ) -> RetrievalContext:
        """Hybrid retrieval: semantic similarity + metadata filtering + ranking."""
        search_results = await self.embeddings.search_similar(
            user_id,
            query,
            limit=limit * 3,
            score_threshold=score_threshold,
        )

        memory_ids = [uuid.UUID(r.record.entity_id) for r in search_results]
        score_map = {uuid.UUID(r.record.entity_id): r.score for r in search_results}

        all_memories: list[Memory] = []
        for mid in memory_ids:
            mem = await self.repo.get_by_id(mid)
            if mem and mem.status == MemoryStatus.ACTIVE and (memory_types is None or mem.type in memory_types):
                all_memories.append(mem)

        scored = self._rank(all_memories, query, score_map)
        ranked = scored[:limit]

        ctx = RetrievalContext(query=query, scores=ranked)
        for ms in ranked:
            bucket = getattr(ctx, ms.memory.type.value)
            bucket.append(ms.memory)
        ctx.total_tokens_estimate = sum(
            len(ms.memory.content.split()) * 4 for ms in ranked
        )
        return ctx

    async def retrieve_by_type(
        self,
        user_id: uuid.UUID,
        memory_type: MemoryType,
        limit: int = 20,
    ) -> list[Memory]:
        """Direct retrieval by type, no semantic search."""
        return await self.repo.list_by_user(user_id, memory_type=memory_type, limit=limit)

    async def supersede(
        self, memory_id: uuid.UUID, new_content: str, new_confidence: float = 0.5
    ) -> Memory:
        """Replace a memory with an updated version."""
        old = await self.repo.get_by_id(memory_id)
        if old is None:
            raise ValueError(f"Memory {memory_id} not found")

        old.status = MemoryStatus.SUPERSEDED
        old.superseded_by = uuid.uuid4()
        old.updated_at = datetime.now(UTC)
        await self.repo.update(old)
        await self.embeddings.delete(old.id, self.embedding_entity_type)

        new = await self.store(
            MemoryCreate(
                user_id=old.user_id,
                type=old.type,
                content=new_content,
                confidence=new_confidence,
                source_message_ids=old.source_message_ids,
            )
        )
        logger.info("memory_superseded", old_id=str(old.id), new_id=str(new.id))
        return new

    async def archive(self, memory_id: uuid.UUID) -> None:
        """Soft-archive a memory."""
        mem = await self.repo.get_by_id(memory_id)
        if mem is None:
            raise ValueError(f"Memory {memory_id} not found")
        mem.status = MemoryStatus.ARCHIVED
        mem.updated_at = datetime.now(UTC)
        await self.repo.update(mem)
        await self.embeddings.delete(mem.id, self.embedding_entity_type)

    async def delete(self, memory_id: uuid.UUID) -> None:
        """Permanently remove a memory."""
        mem = await self.repo.get_by_id(memory_id)
        if mem is None:
            raise ValueError(f"Memory {memory_id} not found")
        await self.embeddings.delete(mem.id, self.embedding_entity_type)
        # In a real implementation, this would call repo.hard_delete
        logger.info("memory_deleted", memory_id=str(memory_id))

    async def consolidate(self, user_id: uuid.UUID) -> ConsolidationResult:
        """Run a consolidation pass: expiration, deduplication, merging."""
        result = ConsolidationResult()

        expired = await self._expire_memories(user_id)
        result.archived = expired

        deduped = await self._deduplicate(user_id)
        result.deduplicated = deduped

        merged = await self._merge_similar(user_id)
        result.merged = merged

        logger.info(
            "consolidation_complete",
            user_id=str(user_id),
            archived=result.archived,
            deduplicated=result.deduplicated,
            merged=result.merged,
        )
        return result

    async def _expire_memories(self, user_id: uuid.UUID) -> int:
        """Archive memories past their TTL."""
        now = datetime.now(UTC)
        ttl_map = {
            MemoryType.EPISODIC: timedelta(days=self.expiration.episodic_ttl_days),
            MemoryType.SEMANTIC: timedelta(days=self.expiration.semantic_ttl_days),
            MemoryType.PATTERN: timedelta(days=self.expiration.pattern_ttl_days),
            MemoryType.REFLECTION: timedelta(days=self.expiration.reflection_ttl_days),
        }

        count = 0
        for mem_type, ttl in ttl_map.items():
            cutoff = now - ttl
            expiring = await self.repo.list_expiring(user_id, cutoff, limit=500)
            for mem in expiring:
                if mem.type == mem_type and mem.status == MemoryStatus.ACTIVE and mem.confidence < self.expiration.min_confidence:
                    mem.status = MemoryStatus.ARCHIVED
                    mem.updated_at = now
                    await self.repo.update(mem)
                    await self.embeddings.delete(mem.id, self.embedding_entity_type)
                    count += 1
        return count

    async def _deduplicate(self, user_id: uuid.UUID) -> int:
        """Find and merge near-duplicate active memories."""
        active = await self.repo.list_by_user(user_id, status=MemoryStatus.ACTIVE, limit=1000)
        seen_content: dict[str, Memory] = {}
        count = 0

        for mem in active:
            normalized = mem.content.strip().lower()
            if normalized in seen_content:
                existing = seen_content[normalized]
                if mem.confidence > existing.confidence:
                    mem.confidence = max(mem.confidence, existing.confidence)
                    mem.updated_at = datetime.now(UTC)
                    await self.repo.update(mem)
                    await self.embeddings.upsert(mem.id, self.embedding_entity_type, mem.content)

                    existing.status = MemoryStatus.SUPERSEDED
                    existing.superseded_by = mem.id
                    existing.updated_at = datetime.now(UTC)
                    await self.repo.update(existing)
                    await self.embeddings.delete(existing.id, self.embedding_entity_type)
                    count += 1
                else:
                    mem.status = MemoryStatus.SUPERSEDED
                    mem.superseded_by = existing.id
                    mem.updated_at = datetime.now(UTC)
                    await self.repo.update(mem)
                    await self.embeddings.delete(mem.id, self.embedding_entity_type)
                    count += 1
            else:
                seen_content[normalized] = mem

        return count

    async def _merge_similar(self, user_id: uuid.UUID) -> int:
        """Merge memories of the same type with high content similarity."""
        count = 0
        for mem_type in MemoryType:
            memories = await self.repo.list_by_user(user_id, memory_type=mem_type, limit=500)
            active = [m for m in memories if m.status == MemoryStatus.ACTIVE]

            for i in range(len(active)):
                if active[i].status != MemoryStatus.ACTIVE:
                    continue
                for j in range(i + 1, len(active)):
                    if active[j].status != MemoryStatus.ACTIVE:
                        continue
                    sim = self._content_similarity(active[i].content, active[j].content)
                    if sim > 0.85:
                        if active[i].confidence >= active[j].confidence:
                            winner, loser = active[i], active[j]
                        else:
                            winner, loser = active[j], active[i]

                        winner.content = f"{winner.content} | {loser.content}"
                        winner.confidence = max(winner.confidence, loser.confidence)
                        winner.updated_at = datetime.now(UTC)
                        await self.repo.update(winner)
                        await self.embeddings.upsert(
                            winner.id, self.embedding_entity_type, winner.content
                        )

                        loser.status = MemoryStatus.SUPERSEDED
                        loser.superseded_by = winner.id
                        loser.updated_at = datetime.now(UTC)
                        await self.repo.update(loser)
                        await self.embeddings.delete(loser.id, self.embedding_entity_type)
                        count += 1

        return count

    def _rank(
        self,
        memories: list[Memory],
        query: str,
        semantic_scores: dict[uuid.UUID, float],
    ) -> list[MemoryScore]:
        """Compute composite scores for memories."""
        now = datetime.now(UTC)
        scored: list[MemoryScore] = []

        for mem in memories:
            relevance = semantic_scores.get(mem.id, 0.0)

            age_days = max((now - mem.created_at).total_seconds() / 86400, 0)
            recency = max(0.0, 1.0 - (age_days / 365))

            importance = self._compute_importance(mem)
            conf = mem.confidence

            final = (
                self.ranking_weights.relevance * relevance
                + self.ranking_weights.recency * recency
                + self.ranking_weights.importance * importance
                + self.ranking_weights.confidence * conf
            )

            scored.append(
                MemoryScore(
                    memory=mem,
                    relevance=relevance,
                    recency=recency,
                    importance=importance,
                    confidence_score=conf,
                    final_score=final,
                )
            )

        scored.sort(key=lambda s: s.final_score, reverse=True)
        return scored

    def _compute_importance(self, memory: Memory) -> float:
        """Derive importance from memory type and content signals."""
        type_weights = {
            MemoryType.SEMANTIC: 0.8,
            MemoryType.PATTERN: 0.7,
            MemoryType.REFLECTION: 0.9,
            MemoryType.EPISODIC: 0.5,
        }
        base = type_weights.get(memory.type, 0.5)

        content = memory.content.lower()
        boost = 0.0
        for signal in ("important", "critical", "goal", "belief", "always", "never"):
            if signal in content:
                boost += 0.05

        return min(1.0, base + boost)

    @staticmethod
    def _content_similarity(a: str, b: str) -> float:
        """Jaccard similarity on word sets."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
