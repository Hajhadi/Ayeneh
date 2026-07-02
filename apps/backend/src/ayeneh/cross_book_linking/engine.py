"""CrossBookConceptLinker — discovers semantic relations between concepts across books."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import structlog

from ayeneh.cross_book_linking.types import (
    AmbiguousRelation,
    CrossBookDiff,
    IncrementalLinkPlan,
    LinkingResult,
    RelationHypothesis,
    SemanticEdge,
    SemanticRelationType,
    SimilarityBreakdown,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Similarity Provider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SimilarityProvider(Protocol):
    """Protocol for pluggable similarity computation."""

    def compute(self, a: str, b: str, context: dict | None = None) -> SimilarityBreakdown:
        """Compute multi-factor similarity between two concepts."""
        ...


# ---------------------------------------------------------------------------
# Rule-Based Similarity Provider
# ---------------------------------------------------------------------------


class RuleBasedSimilarityProvider:
    """Default rule-based similarity provider."""

    def compute(self, a: str, b: str, context: dict | None = None) -> SimilarityBreakdown:
        ctx = context or {}

        # Lexical similarity
        lexical = self._compute_lexical(a, b)

        # Semantic similarity
        semantic = self._compute_semantic(a, b)

        # Epistemic similarity
        epistemic = ctx.get("epistemic_similarity", 0.5)

        # Graph similarity
        graph_sim = ctx.get("graph_similarity", 0.5)

        # Hierarchical similarity
        hierarchical = ctx.get("hierarchical_similarity", 0.5)

        # Cross-book support
        cross_book = ctx.get("cross_book_support", 0.5)

        # Overall
        overall = (
            lexical * 0.20
            + semantic * 0.25
            + epistemic * 0.15
            + graph_sim * 0.15
            + hierarchical * 0.10
            + cross_book * 0.15
        )

        return SimilarityBreakdown(
            lexical_similarity=lexical,
            semantic_similarity=semantic,
            epistemic_similarity=epistemic,
            graph_similarity=graph_sim,
            hierarchical_similarity=hierarchical,
            cross_book_support=cross_book,
            overall_similarity=overall,
        )

    def _compute_lexical(self, a: str, b: str) -> float:
        """Compute lexical similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    def _compute_semantic(self, a: str, b: str) -> float:
        """Compute semantic similarity."""
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()

        # Known semantic pairs
        pairs = {
            ("acceptance", "non-resistance"): 0.8,
            ("mindfulness", "awareness"): 0.7,
            ("self", "ego"): 0.75,
            ("meditation", "contemplation"): 0.7,
            ("compassion", "loving-kindness"): 0.8,
            ("suffering", "dukkha"): 0.7,
            ("presence", "awareness"): 0.65,
            ("consciousness", "awareness"): 0.7,
        }

        if (a_lower, b_lower) in pairs:
            return pairs[(a_lower, b_lower)]
        if (b_lower, a_lower) in pairs:
            return pairs[(b_lower, a_lower)]

        return 0.0


# ---------------------------------------------------------------------------
# Incremental Link Planner
# ---------------------------------------------------------------------------


class IncrementalLinkPlanner:
    """Plans incremental linking for new books."""

    def plan(
        self,
        new_book_id: str,
        new_concepts: list[str],
        existing_concepts: list[str],
    ) -> IncrementalLinkPlan:
        """Plan incremental linking work."""
        new_set = set(new_concepts)
        existing_set = set(existing_concepts)

        affected = list(new_set & existing_set)
        to_compare = list(new_set)

        return IncrementalLinkPlan(
            new_book_id=new_book_id,
            affected_concepts=affected,
            concepts_to_compare=to_compare,
            existing_concepts=list(existing_set),
            estimated_comparisons=len(to_compare) * len(existing_set),
        )


# ---------------------------------------------------------------------------
# CrossBookConceptLinker
# ---------------------------------------------------------------------------


class CrossBookConceptLinker:
    """Discovers semantic relations between concepts across different books.

    Never merges nodes. Only creates semantic edges.
    """

    def __init__(
        self,
        graph: Any = None,
        similarity_provider: SimilarityProvider | None = None,
    ) -> None:
        self._graph = graph
        self._similarity_provider = similarity_provider or RuleBasedSimilarityProvider()
        self._metrics = LinkingMetrics()
        self._planner = IncrementalLinkPlanner()

    def link_concepts(
        self,
        source_concept: str,
        target_concept: str,
        source_book_id: str = "",
        target_book_id: str = "",
        context: dict | None = None,
    ) -> SemanticEdge | None:
        """Create a semantic edge between two concepts."""
        breakdown = self._similarity_provider.compute(source_concept, target_concept, context)

        if breakdown.overall_similarity < 0.3:
            self._metrics.edges_skipped += 1
            return None

        relation_type = self._classify_relation(breakdown.overall_similarity)
        ambiguity = self._compute_ambiguity(breakdown.overall_similarity)

        edge = SemanticEdge(
            source_concept_id=source_concept,
            target_concept_id=target_concept,
            relation_type=relation_type,
            similarity_breakdown=breakdown,
            similarity_score=breakdown.overall_similarity,
            confidence=breakdown.overall_similarity * (1.0 - ambiguity),
            ambiguity=ambiguity,
            reason=f"Overall similarity {breakdown.overall_similarity:.2f}",
            supporting_books=[b for b in [source_book_id, target_book_id] if b],
            similarity_provider="rule_based",
            provider_version="1.0.0",
        )

        self._metrics.edges_created += 1
        return edge

    def find_ambiguous_relations(
        self,
        concepts: list[str],
    ) -> list[AmbiguousRelation]:
        """Find ambiguous relations between concepts."""
        ambiguous: list[AmbiguousRelation] = []

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                breakdown = self._similarity_provider.compute(c1, c2)
                if 0.3 <= breakdown.overall_similarity < 0.7:
                    ambiguity = self._compute_ambiguity(breakdown.overall_similarity)
                    possible_relations = self._suggest_relations(breakdown.overall_similarity)

                    ambiguous.append(AmbiguousRelation(
                        source_concept=c1,
                        target_concept=c2,
                        possible_relations=possible_relations,
                        probabilities={r: breakdown.overall_similarity for r in possible_relations},
                        similarity_score=breakdown.overall_similarity,
                        confidence=breakdown.overall_similarity * (1.0 - ambiguity),
                        recommended_resolution="Manual review recommended",
                    ))

        return ambiguous

    def detect_diff(
        self,
        old_concepts: list[str],
        new_concepts: list[str],
    ) -> CrossBookDiff:
        """Detect what changed between concept sets."""
        old_set = set(old_concepts)
        new_set = set(new_concepts)

        return CrossBookDiff(
            new_concepts=list(new_set - old_set),
            affected_concepts=list(old_set & new_set),
        )

    def plan_incremental(
        self,
        new_book_id: str,
        new_concepts: list[str],
        existing_concepts: list[str],
    ) -> IncrementalLinkPlan:
        """Plan incremental linking for a new book."""
        return self._planner.plan(new_book_id, new_concepts, existing_concepts)

    def get_metrics(self) -> dict[str, int]:
        """Get linking metrics."""
        return {
            "edges_created": self._metrics.edges_created,
            "edges_skipped": self._metrics.edges_skipped,
        }

    def _classify_relation(self, similarity: float) -> str:
        """Classify the relation type based on similarity."""
        if similarity >= 0.8:
            return SemanticRelationType.SUPPORTS
        elif similarity >= 0.6:
            return SemanticRelationType.SHARES_CONCEPT
        elif similarity >= 0.4:
            return SemanticRelationType.PARTIALLY_OVERLAPS
        else:
            return SemanticRelationType.RELATED_TO

    def _compute_ambiguity(self, similarity: float) -> float:
        """Compute ambiguity score."""
        if similarity >= 0.8:
            return 0.1
        elif similarity >= 0.6:
            return 0.3
        elif similarity >= 0.4:
            return 0.5
        else:
            return 0.7

    def _suggest_relations(self, similarity: float) -> list[str]:
        """Suggest possible relations."""
        relations = []
        if similarity >= 0.6:
            relations.append(SemanticRelationType.SUPPORTS)
            relations.append(SemanticRelationType.SHARES_CONCEPT)
        if similarity >= 0.4:
            relations.append(SemanticRelationType.PARTIALLY_OVERLAPS)
        relations.append(SemanticRelationType.RELATED_TO)
        return relations


@dataclass
class LinkingMetrics:
    """Metrics for linking operations."""

    edges_created: int = 0
    edges_skipped: int = 0
    ambiguous_found: int = 0