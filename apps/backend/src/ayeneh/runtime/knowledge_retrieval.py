"""Knowledge Retrieval Pipeline — per SPEC-23.

Executes a RetrievalPlan and collects evidence for downstream reasoning.
Performs no reasoning — only gathers knowledge.

Processing Phases (SPEC-23 §4):
1. Preparation
2. Knowledge Source Execution
3. Evidence Aggregation
4. Retrieval Validation
5. RetrievalResult Publication
"""

from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Retrieval Result Artifact (SPEC-23 §11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable retrieval result — per SPEC-23 §11."""

    # Identity
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    plan_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    producer_version: str = "1.0.0"

    # Retrieved artifacts
    chunks: list[dict[str, Any]] = field(default_factory=list)
    epistemic_profiles: list[dict[str, Any]] = field(default_factory=list)
    graph_nodes: list[dict[str, Any]] = field(default_factory=list)
    graph_edges: list[dict[str, Any]] = field(default_factory=list)
    concepts: list[dict[str, Any]] = field(default_factory=list)
    topics: list[dict[str, Any]] = field(default_factory=list)
    books: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    conversation_context: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    total_chunks: int = 0
    total_concepts: int = 0
    total_profiles: int = 0
    total_evidence: int = 0
    retrieval_confidence: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    duration_ms: float = 0.0
    producer: str = "knowledge_retrieval"


# ---------------------------------------------------------------------------
# Retrieval Validation (SPEC-23 §10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalValidation:
    """Result of retrieval validation."""
    is_valid: bool = True
    evidence_complete: bool = True
    traversal_complete: bool = True
    citation_complete: bool = True
    duplicates_found: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Knowledge Retrieval Pipeline
# ---------------------------------------------------------------------------


class KnowledgeRetrievalPipeline:
    """SPEC-23 compliant Knowledge Retrieval pipeline.

    Executes RetrievalPlan and collects evidence.
    Performs no reasoning — only gathers knowledge.
    """

    _cache: OrderedDict[str, list[dict]] = OrderedDict()
    _CACHE_MAX_SIZE = 100

    def __init__(self) -> None:
        self._db_path = "/home/hadi/ayeneh/Ayeneh/ayeneh.db"

    def execute(
        self,
        retrieval_plan: Any,
        session_id: str = "",
        knowledge_version: str = "0.0.0",
        graph_version: str = "0.0.0",
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> RetrievalResult:
        """Execute the full Knowledge Retrieval pipeline."""
        start = time.monotonic()

        # Phase 1: Preparation
        phase1 = self._phase_preparation(retrieval_plan)

        # Phase 2: Knowledge Source Execution
        phase2 = self._phase_source_execution(retrieval_plan, conversation_history)

        # Phase 3: Evidence Aggregation
        phase3 = self._phase_evidence_aggregation(phase2)

        # Phase 4: Retrieval Validation
        phase4 = self._phase_retrieval_validation(phase3)

        # Phase 5: Publication
        duration_ms = (time.monotonic() - start) * 1000
        result = self._phase_publication(
            retrieval_plan, phase2, phase3, phase4,
            session_id, knowledge_version, graph_version, duration_ms,
            conversation_history,
        )

        logger.debug(
            "retrieval_complete",
            result_id=result.result_id,
            chunks=result.total_chunks,
            profiles=result.total_profiles,
            duration_ms=round(result.duration_ms, 1),
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: Preparation (SPEC-23 §5)
    # ------------------------------------------------------------------

    def _phase_preparation(self, plan: Any) -> dict[str, Any]:
        """Validate upstream artifacts before retrieval."""
        return {
            "plan_valid": plan is not None,
            "strategy": getattr(plan, 'strategy', 'book_first'),
            "budget": getattr(plan, 'max_retrieval_budget', 20),
        }

    # ------------------------------------------------------------------
    # Phase 2: Knowledge Source Execution (SPEC-23 §6)
    # ------------------------------------------------------------------

    def _phase_source_execution(
        self,
        plan: Any,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute retrieval tasks per the RetrievalPlan."""
        chunks = []
        profiles = []
        books = []
        concepts_found = []
        cache_hits = 0
        cache_misses = 0

        target_concepts = getattr(plan, 'target_concepts', [])
        target_books = getattr(plan, 'target_books', [])
        budget = getattr(plan, 'max_retrieval_budget', 20)

        # Build cache key from sorted target_concepts + target_books
        cache_key = "|".join(sorted(target_concepts) + sorted(target_books))

        # Check cache
        if cache_key and cache_key in self.__class__._cache:
            self.__class__._cache.move_to_end(cache_key)
            cached = self.__class__._cache[cache_key]
            cache_hits = 1
            return {
                "chunks": cached,
                "profiles": [],
                "books": [],
                "concepts": concepts_found,
                "cache_hits": cache_hits,
                "cache_misses": 0,
            }

        # Extract conversation keywords if history provided
        conversation_keywords: list[str] = []
        if conversation_history:
            for msg in conversation_history[-5:]:
                text = msg.get("content", "")
                if text:
                    words = [w for w in text.split() if len(w) > 3]
                    conversation_keywords.extend(words[:3])

        keywords = list(target_concepts[:5]) + conversation_keywords[:3]
        keywords = [k for k in keywords if k][:5]

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Retrieve chunks by book references
            if target_books:
                for book_ref in target_books[:5]:
                    cursor.execute(
                        "SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                        "FROM book_chunks bc JOIN books b ON bc.book_id = b.id "
                        "WHERE bc.deleted_at IS NULL AND b.title LIKE ? "
                        "LIMIT ?",
                        (f"%{book_ref}%", budget // len(target_books)),
                    )
                    for row in cursor.fetchall():
                        chunks.append({
                            "id": row[0], "chapter_id": row[1], "content": row[2][:800],
                            "sequence": row[3], "token_count": row[4], "book_id": row[5], "book_title": row[6],
                        })

            # Fallback: retrieve by keywords if no chunks found
            if not chunks and keywords:
                conditions = " OR ".join(["bc.content LIKE ?" for _ in keywords])
                search_terms = [f"%{kw}%" for kw in keywords]
                cursor.execute(
                    f"SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                    f"FROM book_chunks bc JOIN books b ON bc.book_id = b.id "
                    f"WHERE bc.deleted_at IS NULL AND ({conditions}) "
                    f"LIMIT ?",
                    (*search_terms, budget),
                )
                for row in cursor.fetchall():
                    chunks.append({
                        "id": row[0], "chapter_id": row[1], "content": row[2][:800],
                        "sequence": row[3], "token_count": row[4], "book_id": row[5], "book_title": row[6],
                    })

            # Final fallback: all chunks
            if not chunks:
                cursor.execute(
                    "SELECT bc.id, bc.chapter_id, bc.content, bc.sequence_number, bc.token_count, b.id, b.title "
                    "FROM book_chunks bc LEFT JOIN books b ON bc.book_id = b.id "
                    "WHERE bc.deleted_at IS NULL ORDER BY bc.sequence_number LIMIT ?",
                    (budget,),
                )
                for row in cursor.fetchall():
                    chunks.append({
                        "id": row[0], "chapter_id": row[1], "content": row[2][:800],
                        "sequence": row[3], "token_count": row[4], "book_id": row[5], "book_title": row[6],
                    })

            # Retrieve epistemic profiles
            if chunks:
                book_ids = list(set(c.get("book_id", "") for c in chunks if c.get("book_id")))
                if book_ids:
                    placeholders = ",".join(["?" for _ in book_ids])
                    cursor.execute(
                        f"SELECT book_id, tradition, framework, discipline, primary_topics, evidence_level, reasoning_style "
                        f"FROM epistemic_profiles WHERE book_id IN ({placeholders}) AND deleted_at IS NULL",
                        book_ids,
                    )
                    for row in cursor.fetchall():
                        profiles.append({
                            "book_id": row[0], "tradition": row[1], "framework": row[2],
                            "discipline": row[3], "primary_topics": row[4], "evidence_level": row[5],
                            "reasoning_style": row[6],
                        })

            # Retrieve book metadata
            if chunks:
                book_ids = list(set(c.get("book_id", "") for c in chunks if c.get("book_id")))
                if book_ids:
                    placeholders = ",".join(["?" for _ in book_ids])
                    cursor.execute(
                        f"SELECT id, title, author, chunk_count FROM books WHERE id IN ({placeholders}) AND deleted_at IS NULL",
                        book_ids,
                    )
                    for row in cursor.fetchall():
                        books.append({"id": row[0], "title": row[1], "author": row[2], "chunk_count": row[3]})

            conn.close()

        except Exception as exc:
            logger.warning("retrieval_source_error", error=str(exc))

        # Store in cache on miss
        if cache_key and chunks:
            cls = self.__class__
            if len(cls._cache) >= cls._CACHE_MAX_SIZE:
                cls._cache.popitem(last=False)
            cls._cache[cache_key] = chunks
            cache_misses = 1

        return {
            "chunks": chunks,
            "profiles": profiles,
            "books": books,
            "concepts": concepts_found,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
        }

    # ------------------------------------------------------------------
    # Phase 3: Evidence Aggregation (SPEC-23 §8)
    # ------------------------------------------------------------------

    def _phase_evidence_aggregation(self, source_data: dict) -> dict[str, Any]:
        """Combine all retrieved artifacts into evidence bundle."""
        chunks = source_data.get("chunks", [])
        profiles = source_data.get("profiles", [])
        books = source_data.get("books", [])

        # Deduplicate chunks by ID
        seen_ids = set()
        unique_chunks = []
        for chunk in chunks:
            cid = chunk.get("id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique_chunks.append(chunk)

        # Build citations from chunks
        citations = []
        for chunk in unique_chunks:
            citations.append({
                "chunk_id": chunk.get("id", ""),
                "chapter_id": chunk.get("chapter_id", ""),
                "book_id": chunk.get("book_id", ""),
                "book_title": chunk.get("book_title", ""),
                "sequence": chunk.get("sequence", 0),
            })

        return {
            "chunks": unique_chunks,
            "profiles": profiles,
            "books": books,
            "citations": citations,
            "total_evidence": len(unique_chunks) + len(profiles),
        }

    # ------------------------------------------------------------------
    # Phase 4: Retrieval Validation (SPEC-23 §10)
    # ------------------------------------------------------------------

    def _phase_retrieval_validation(self, aggregated: dict) -> RetrievalValidation:
        """Validate retrieval completeness."""
        chunks = aggregated.get("chunks", [])
        profiles = aggregated.get("profiles", [])

        # Check evidence completeness
        evidence_complete = len(chunks) > 0

        # Check for duplicates
        chunk_ids = [c.get("id", "") for c in chunks]
        duplicates = len(chunk_ids) - len(set(chunk_ids))

        return RetrievalValidation(
            is_valid=evidence_complete,
            evidence_complete=evidence_complete,
            traversal_complete=True,
            citation_complete=len(chunks) > 0,
            duplicates_found=duplicates,
        )

    # ------------------------------------------------------------------
    # Phase 5: RetrievalResult Publication (SPEC-23 §11)
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        plan: Any,
        source_data: dict,
        aggregated: dict,
        validation: RetrievalValidation,
        session_id: str,
        knowledge_version: str,
        graph_version: str,
        duration_ms: float = 0.0,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> RetrievalResult:
        """Publish exactly one immutable RetrievalResult."""
        chunks = aggregated.get("chunks", [])
        profiles = aggregated.get("profiles", [])
        books = aggregated.get("books", [])
        citations = aggregated.get("citations", [])

        return RetrievalResult(
            session_id=session_id,
            plan_id=getattr(plan, 'plan_id', ''),
            knowledge_version=knowledge_version,
            graph_version=graph_version,
            chunks=chunks,
            epistemic_profiles=profiles,
            books=books,
            citations=citations,
            conversation_context=conversation_history or [],
            total_chunks=len(chunks),
            total_profiles=len(profiles),
            total_evidence=aggregated.get("total_evidence", 0),
            retrieval_confidence=1.0 if validation.is_valid else 0.5,
            cache_hits=source_data.get("cache_hits", 0),
            cache_misses=source_data.get("cache_misses", 0),
            duration_ms=duration_ms,
        )
