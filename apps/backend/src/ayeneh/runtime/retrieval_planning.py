"""Retrieval Planning — per SPEC-01A Part 2 §74-76.

Retrieval Planning determines what should be retrieved.
It performs no retrieval itself.

The RetrievalPlan is immutable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# RetrievalPlan Artifact (SPEC-01A §75)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalPlan:
    """What should be retrieved — immutable after creation.

    Per SPEC-01A §75: the RetrievalPlan is immutable.
    """

    # Identity
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    query_analysis_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    policy_version: str = "0.0.0"
    producer_version: str = "1.0.0"
    artifact_version: str = "1.0.0"

    # Targets (what to retrieve)
    target_books: list[str] = field(default_factory=list)
    target_chapters: list[str] = field(default_factory=list)
    target_documents: list[str] = field(default_factory=list)
    target_concepts: list[str] = field(default_factory=list)
    target_topics: list[str] = field(default_factory=list)
    graph_regions: list[str] = field(default_factory=list)

    # Strategy
    strategy: str = "concept_first"  # concept_first | book_first | topic_first | hierarchy_first | evidence_first
    traversal_limits: dict[str, int] = field(default_factory=lambda: {"max_depth": 3, "max_nodes": 50})
    graph_expansion_rules: list[str] = field(default_factory=list)
    max_retrieval_budget: int = 20  # max chunks to retrieve
    expected_evidence_count: int = 5
    required_evidence_level: str = "any"  # any | empirical | experiential | theoretical
    expected_confidence: float = 0.5

    # Constraints
    provider_constraints: dict[str, Any] = field(default_factory=dict)

    # Provenance
    producer: str = "retrieval_planning"


# ---------------------------------------------------------------------------
# Retrieval Strategy Definitions
# ---------------------------------------------------------------------------


class RetrievalStrategy:
    """Strategy identifiers per SPEC-01A §76."""

    CONCEPT_FIRST = "concept_first"
    BOOK_FIRST = "book_first"
    TOPIC_FIRST = "topic_first"
    HIERARCHY_FIRST = "hierarchy_first"
    EVIDENCE_FIRST = "evidence_first"


# ---------------------------------------------------------------------------
# RetrievalPlanner
# ---------------------------------------------------------------------------


class RetrievalPlanner:
    """Determines what should be retrieved — performs no retrieval.

    Per SPEC-01A §74: Retrieval Planning determines what should be retrieved.
    It performs no retrieval itself.
    """

    def plan(
        self,
        query_analysis: Any,
        session_id: str = "",
        knowledge_version: str = "0.0.0",
        graph_version: str = "0.0.0",
    ) -> RetrievalPlan:
        """Create a RetrievalPlan from QueryAnalysis.

        This is a pure planning step — no retrieval happens here.
        """
        # Extract information from QueryAnalysis
        concepts = getattr(query_analysis, 'concepts', [])
        entities = getattr(query_analysis, 'entities', [])
        topics = getattr(query_analysis, 'topics', [])
        book_refs = getattr(query_analysis, 'book_references', [])
        scope = getattr(query_analysis, 'scope', 'single_book')
        complexity = getattr(query_analysis, 'complexity', 'medium')
        required_reasoning = getattr(query_analysis, 'required_reasoning', 'single_source')

        # Determine strategy based on scope and complexity
        strategy = self._determine_strategy(scope, complexity, required_reasoning)

        # Determine budget based on complexity
        budget = self._determine_budget(complexity, len(concepts))

        # Determine expected evidence count
        expected_evidence = self._determine_expected_evidence(scope, complexity)

        # Determine required evidence level
        evidence_level = self._determine_evidence_level(required_reasoning)

        # Determine traversal limits
        traversal = self._determine_traversal_limits(scope, complexity)

        plan = RetrievalPlan(
            session_id=session_id,
            target_concepts=concepts,
            target_topics=topics,
            target_books=book_refs,
            strategy=strategy,
            traversal_limits=traversal,
            max_retrieval_budget=budget,
            expected_evidence_count=expected_evidence,
            required_evidence_level=evidence_level,
            knowledge_version=knowledge_version,
            graph_version=graph_version,
        )

        logger.debug(
            "retrieval_plan_created",
            plan_id=plan.plan_id,
            strategy=strategy,
            concepts=len(concepts),
            budget=budget,
        )

        return plan

    def _determine_strategy(self, scope: str, complexity: str, reasoning: str) -> str:
        """Choose retrieval strategy based on query characteristics."""
        if scope == "cross_book" or reasoning == "cross_book":
            return RetrievalStrategy.CONCEPT_FIRST
        if scope == "cross_tradition" or reasoning == "cross_tradition":
            return RetrievalStrategy.TOPIC_FIRST
        if scope == "whole_library":
            return RetrievalStrategy.EVIDENCE_FIRST
        if complexity == "high":
            return RetrievalStrategy.CONCEPT_FIRST
        return RetrievalStrategy.BOOK_FIRST

    def _determine_budget(self, complexity: str, num_concepts: int) -> int:
        """Determine max chunks to retrieve."""
        base = {"low": 8, "medium": 15, "high": 25}.get(complexity, 15)
        return min(base + num_concepts * 2, 40)

    def _determine_expected_evidence(self, scope: str, complexity: str) -> int:
        """Determine expected evidence count."""
        if scope in ("cross_book", "cross_tradition"):
            return 8
        if complexity == "high":
            return 6
        return 4

    def _determine_evidence_level(self, reasoning: str) -> str:
        """Determine required evidence level."""
        if reasoning in ("cross_book", "cross_tradition", "synthesis"):
            return "empirical"
        return "any"

    def _determine_traversal_limits(self, scope: str, complexity: str) -> dict[str, int]:
        """Determine graph traversal limits."""
        depth = {"low": 1, "medium": 2, "high": 3}.get(complexity, 2)
        nodes = {"low": 20, "medium": 40, "high": 80}.get(complexity, 40)
        if scope in ("cross_book", "cross_tradition"):
            depth = min(depth + 1, 5)
            nodes = min(nodes + 20, 100)
        return {"max_depth": depth, "max_nodes": nodes}
