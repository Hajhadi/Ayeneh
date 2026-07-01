"""Knowledge retrieval engine — manages chunk retrieval, ranking, citations, and context assembly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

import structlog

from ayeneh.application.ports.vector_store import SearchResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain entities
# ---------------------------------------------------------------------------

@dataclass
class Book:
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    author: str | None = None
    source_format: str = "unknown"
    status: str = "ready"
    chunk_count: int = 0


@dataclass
class BookChunk:
    id: uuid.UUID
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    content: str
    sequence_number: int = 0
    page_start: int | None = None
    page_end: int | None = None
    section_heading: str | None = None
    token_count: int = 0


@dataclass
class Citation:
    """Structured citation for a retrieved chunk."""

    chunk_id: uuid.UUID
    book_id: uuid.UUID
    book_title: str
    author: str | None = None
    section_heading: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    excerpt: str = ""
    score: float = 0.0


@dataclass
class RankedChunk:
    """A chunk with its retrieval score and citation."""

    chunk: BookChunk
    book: Book
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    final_score: float = 0.0
    citation: Citation | None = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class RetrievalStrategy(StrEnum):
    SEMANTIC_ONLY = "semantic_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"


@dataclass
class RetrievalConfig:
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    max_chunks_per_source: int = 5
    max_total_chunks: int = 15
    score_threshold: float = 0.1
    token_budget: int = 8000
    tokens_per_chunk_estimate: int = 200


@dataclass
class KnowledgeRetrievalContext:
    """Assembled context from knowledge retrieval."""

    query: str
    chunks: list[RankedChunk] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    total_tokens_estimate: int = 0
    token_budget: int = 8000
    sources_used: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------

class BookRepository:
    async def get_by_user(self, user_id: uuid.UUID) -> list[Book]:
        raise NotImplementedError

    async def get_by_id(self, book_id: uuid.UUID) -> Book | None:
        raise NotImplementedError

    async def get_chunks_by_book(self, book_id: uuid.UUID) -> list[BookChunk]:
        raise NotImplementedError

    async def get_chunks_by_ids(self, chunk_ids: list[uuid.UUID]) -> list[BookChunk]:
        raise NotImplementedError


class ChunkSearchGateway:
    async def search_by_embedding(
        self,
        query_embedding: list[float],
        *,
        user_id: uuid.UUID,
        entity_type: str = "book_chunk",
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        raise NotImplementedError

    async def keyword_search(
        self,
        query: str,
        *,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[SearchResult]:
        raise NotImplementedError


class EmbeddingGateway:
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# KnowledgeService
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeService:
    """Knowledge retrieval engine — owns all knowledge retrieval business logic.

    Responsibilities:
    - Retrieve chunks via semantic, keyword, or hybrid search
    - Rank chunks using configurable strategies
    - Generate structured citations
    - Compress context to fit token budgets
    - Merge retrieval contexts from multiple sources
    """

    book_repo: BookRepository
    chunk_search: ChunkSearchGateway
    embeddings: EmbeddingGateway
    config: RetrievalConfig = field(default_factory=RetrievalConfig)

    async def retrieve(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        book_ids: list[uuid.UUID] | None = None,
        config: RetrievalConfig | None = None,
    ) -> KnowledgeRetrievalContext:
        """Main retrieval entry point — hybrid search + ranking + citations + compression."""
        cfg = config or self.config

        search_results = await self._search(user_id, query, cfg)

        chunks, books = await self._load_chunks(search_results)

        ranked = self._rank(chunks, books, search_results, cfg)

        with_citations = self._generate_citations(ranked)

        compressed = self._compress(with_citations, cfg)

        ctx = KnowledgeRetrievalContext(
            query=query,
            chunks=compressed,
            citations=[c.citation for c in compressed if c.citation],
            total_tokens_estimate=sum(c.chunk.token_count for c in compressed),
            token_budget=cfg.token_budget,
            sources_used=list({c.book.title for c in compressed}),
        )

        logger.info(
            "knowledge_retrieved",
            user_id=str(user_id),
            chunks=len(compressed),
            tokens=ctx.total_tokens_estimate,
        )
        return ctx

    async def retrieve_from_books(
        self,
        user_id: uuid.UUID,
        query: str,
        book_ids: list[uuid.UUID],
    ) -> KnowledgeRetrievalContext:
        """Retrieve from specific books only."""
        return await self.retrieve(user_id, query, book_ids=book_ids)

    async def _search(
        self,
        user_id: uuid.UUID,
        query: str,
        cfg: RetrievalConfig,
    ) -> list[SearchResult]:
        """Execute search based on configured strategy."""
        if cfg.strategy == RetrievalStrategy.SEMANTIC_ONLY:
            return await self._semantic_search(user_id, query, cfg)
        if cfg.strategy == RetrievalStrategy.KEYWORD_ONLY:
            return await self.chunk_search.keyword_search(
                query, user_id=user_id, limit=cfg.max_total_chunks
            )
        return await self._hybrid_search(user_id, query, cfg)

    async def _semantic_search(
        self,
        user_id: uuid.UUID,
        query: str,
        cfg: RetrievalConfig,
    ) -> list[SearchResult]:
        embedding = await self.embeddings.embed(query)
        return await self.chunk_search.search_by_embedding(
            embedding,
            user_id=user_id,
            limit=cfg.max_total_chunks,
            score_threshold=cfg.score_threshold,
        )

    async def _hybrid_search(
        self,
        user_id: uuid.UUID,
        query: str,
        cfg: RetrievalConfig,
    ) -> list[SearchResult]:
        semantic_results = await self._semantic_search(user_id, query, cfg)
        keyword_results = await self.chunk_search.keyword_search(
            query, user_id=user_id, limit=cfg.max_total_chunks
        )

        score_map: dict[str, float] = {}
        for r in semantic_results:
            score_map[r.record.entity_id] = r.score * cfg.semantic_weight

        for r in keyword_results:
            existing = score_map.get(r.record.entity_id, 0.0)
            score_map[r.record.entity_id] = existing + r.score * cfg.keyword_weight

        merged = []
        seen = set()
        for entity_id, score in sorted(score_map.items(), key=lambda x: x[1], reverse=True):
            if entity_id not in seen and score >= cfg.score_threshold:
                record = next(
                    (r.record for r in semantic_results if r.record.entity_id == entity_id),
                    next(
                        (r.record for r in keyword_results if r.record.entity_id == entity_id),
                        None,
                    ),
                )
                if record:
                    merged.append(SearchResult(record=record, score=score))
                seen.add(entity_id)

        return merged[: cfg.max_total_chunks]

    async def _load_chunks(
        self, search_results: list[SearchResult]
    ) -> tuple[dict[str, BookChunk], dict[uuid.UUID, Book]]:
        """Load BookChunk and Book domain objects for search results."""
        chunk_ids = [uuid.UUID(r.record.entity_id) for r in search_results]
        if not chunk_ids:
            return {}, {}
        chunks = await self.book_repo.get_chunks_by_ids(chunk_ids)
        book_ids = list({c.book_id for c in chunks})
        books: dict[uuid.UUID, Book] = {}
        for bid in book_ids:
            b = await self.book_repo.get_by_id(bid)
            if b:
                books[bid] = b
        return {str(c.id): c for c in chunks}, books

    def _rank(
        self,
        chunks: dict[str, BookChunk],
        books: dict[uuid.UUID, Book],
        search_results: list[SearchResult],
        cfg: RetrievalConfig,
    ) -> list[RankedChunk]:
        """Rank chunks by their retrieval scores."""
        ranked: list[RankedChunk] = []
        for result in search_results:
            chunk = chunks.get(result.record.entity_id)
            if chunk is None:
                continue
            book = books.get(chunk.book_id, Book(id=chunk.book_id, user_id=uuid.uuid4(), title="Unknown"))
            ranked.append(RankedChunk(
                chunk=chunk,
                book=book,
                semantic_score=result.score,
                final_score=result.score,
            ))
        ranked.sort(key=lambda r: r.final_score, reverse=True)
        return ranked[: cfg.max_total_chunks]

    def _generate_citations(self, ranked: list[RankedChunk]) -> list[RankedChunk]:
        """Attach citations to ranked chunks."""
        for rc in ranked:
            rc.citation = Citation(
                chunk_id=rc.chunk.id,
                book_id=rc.chunk.book_id,
                book_title=rc.book.title,
                author=rc.book.author,
                section_heading=rc.chunk.section_heading,
                page_start=rc.chunk.page_start,
                page_end=rc.chunk.page_end,
                excerpt=rc.chunk.content[:200],
                score=rc.final_score,
            )
        return ranked

    def _compress(
        self, ranked: list[RankedChunk], cfg: RetrievalConfig
    ) -> list[RankedChunk]:
        """Compress ranked chunks to fit within token budget."""
        total = 0
        compressed: list[RankedChunk] = []
        for rc in ranked:
            chunk_tokens = rc.chunk.token_count or cfg.tokens_per_chunk_estimate
            if total + chunk_tokens > cfg.token_budget:
                break
            compressed.append(rc)
            total += chunk_tokens
        return compressed
