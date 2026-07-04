"""Concept Integration — per SPEC-01A Part 2 §93-97.

Concept Integration constructs a unified semantic view over retrieved knowledge.
It performs organization only — no reasoning.

The IntegratedKnowledge artifact is immutable after validation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# IntegratedKnowledge Artifact (SPEC-01A §95)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntegratedKnowledge:
    """Unified semantic view over retrieved knowledge — immutable.

    Per SPEC-01A §95: IntegratedKnowledge shall contain all referenced
    knowledge objects in a structured, organized form.
    """

    # Identity
    integration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # References to upstream artifacts
    query_analysis_id: str = ""
    retrieval_plan_id: str = ""

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    producer_version: str = "1.0.0"
    artifact_version: str = "1.0.0"

    # Referenced knowledge objects
    referenced_books: list[dict[str, Any]] = field(default_factory=list)
    referenced_chapters: list[dict[str, Any]] = field(default_factory=list)
    referenced_chunks: list[dict[str, Any]] = field(default_factory=list)
    referenced_concepts: list[dict[str, Any]] = field(default_factory=list)
    referenced_topics: list[dict[str, Any]] = field(default_factory=list)

    # Graph elements
    retrieved_graph_nodes: list[dict[str, Any]] = field(default_factory=list)
    retrieved_graph_edges: list[dict[str, Any]] = field(default_factory=list)

    # Evidence and interpretations
    retrieved_evidence: list[dict[str, Any]] = field(default_factory=list)
    retrieved_interpretations: list[dict[str, Any]] = field(default_factory=list)

    # Cross-book relations
    cross_book_relations: list[dict[str, Any]] = field(default_factory=list)

    # Profiles
    epistemic_profiles: list[dict[str, Any]] = field(default_factory=list)
    hierarchical_profiles: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    total_chunks: int = 0
    total_concepts: int = 0
    total_evidence: int = 0
    producer: str = "concept_integration"


# ---------------------------------------------------------------------------
# ConceptIntegrator
# ---------------------------------------------------------------------------


class ConceptIntegrator:
    """Constructs a unified semantic view over retrieved knowledge.

    Per SPEC-01A §93: Concept Integration performs organization only.
    It performs no reasoning.
    """

    def integrate(
        self,
        chunks: list[dict[str, Any]],
        epistemic_profiles: list[dict[str, Any]],
        query_analysis: Any = None,
        retrieval_plan: Any = None,
        knowledge_version: str = "0.0.0",
        graph_version: str = "0.0.0",
    ) -> IntegratedKnowledge:
        """Construct IntegratedKnowledge from retrieved artifacts.

        This is an organization step — no reasoning occurs here.
        """
        # Extract unique books and chapters from chunks
        books = {}
        chapters = {}
        concepts = {}
        topics = {}

        for chunk in chunks:
            book_id = chunk.get("book_id", "")
            book_title = chunk.get("book_title", "")
            chapter_id = chunk.get("chapter_id", "")

            if book_id and book_id not in books:
                books[book_id] = {
                    "id": book_id,
                    "title": book_title,
                    "chunk_count": sum(1 for c in chunks if c.get("book_id") == book_id),
                }

            if chapter_id and chapter_id not in chapters:
                chapters[chapter_id] = {
                    "id": chapter_id,
                    "book_id": book_id,
                    "title": chunk.get("chapter_title", ""),
                }

        # Extract concepts from query analysis
        if query_analysis:
            for concept in getattr(query_analysis, 'concepts', []):
                if concept not in concepts:
                    concepts[concept] = {"name": concept, "source": "query_analysis"}

            for topic in getattr(query_analysis, 'topics', []):
                if topic not in topics:
                    topics[topic] = {"name": topic, "source": "query_analysis"}

        # Extract concepts from epistemic profiles
        for profile in epistemic_profiles:
            primary_topics = profile.get("primary_topics", [])
            if isinstance(primary_topics, str):
                try:
                    import json
                    primary_topics = json.loads(primary_topics)
                except (json.JSONDecodeError, TypeError):
                    primary_topics = []

            for t in primary_topics:
                if t not in topics:
                    topics[t] = {"name": t, "source": "epistemic_profile"}

        # Build cross-book relations (simple: books sharing concepts)
        cross_book_relations = []
        book_concept_map = {}
        for chunk in chunks:
            book_id = chunk.get("book_id", "")
            content = chunk.get("content", "").lower()
            for concept_name in concepts:
                if concept_name.lower() in content:
                    if book_id not in book_concept_map:
                        book_concept_map[book_id] = set()
                    book_concept_map[book_id].add(concept_name)

        book_ids = list(book_concept_map.keys())
        for i in range(len(book_ids)):
            for j in range(i + 1, len(book_ids)):
                shared = book_concept_map[book_ids[i]] & book_concept_map[book_ids[j]]
                if shared:
                    cross_book_relations.append({
                        "book_a": book_ids[i],
                        "book_b": book_ids[j],
                        "shared_concepts": list(shared),
                    })

        integrated = IntegratedKnowledge(
            query_analysis_id=getattr(query_analysis, 'session_id', '') if query_analysis else "",
            retrieval_plan_id=getattr(retrieval_plan, 'plan_id', '') if retrieval_plan else "",
            referenced_books=list(books.values()),
            referenced_chapters=list(chapters.values()),
            referenced_chunks=chunks,
            referenced_concepts=list(concepts.values()),
            referenced_topics=list(topics.values()),
            cross_book_relations=cross_book_relations,
            epistemic_profiles=epistemic_profiles,
            total_chunks=len(chunks),
            total_concepts=len(concepts),
            total_evidence=len(chunks),
            knowledge_version=knowledge_version,
            graph_version=graph_version,
        )

        logger.debug(
            "concept_integration_complete",
            integration_id=integrated.integration_id,
            books=len(books),
            concepts=len(concepts),
            topics=len(topics),
            cross_book_relations=len(cross_book_relations),
        )

        return integrated
