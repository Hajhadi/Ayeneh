"""Retrieval Planning Pipeline — per SPEC-22.

Determines what knowledge should be retrieved before any reasoning begins.
Performs no retrieval itself — only constructs an executable RetrievalPlan.

Processing Phases (SPEC-22 §4):
1. Preparation
2. Knowledge Source Selection
3. Evidence Requirement Analysis
4. Graph Traversal Planning
5. Strategy Construction
6. Capability Analysis
7. RetrievalPlan Publication
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Phase Output Types
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeSourceSelection:
    """Output of Source Selection phase (SPEC-22 §6)."""
    selected_sources: list[dict[str, Any]] = field(default_factory=list)
    justification: str = ""


@dataclass
class EvidenceRequirement:
    """Single evidence requirement (SPEC-22 §7)."""
    category: str = ""  # definition, relationship, comparison, etc.
    min_count: int = 1
    required_level: str = "any"  # any | empirical | experiential | theoretical
    cross_source: bool = False


@dataclass
class EvidenceRequirementAnalysis:
    """Output of Evidence Requirement phase (SPEC-22 §7)."""
    requirements: list[EvidenceRequirement] = field(default_factory=list)
    total_min_evidence: int = 0


@dataclass
class GraphTraversalPlan:
    """Output of Graph Traversal Planning phase (SPEC-22 §8)."""
    starting_nodes: list[str] = field(default_factory=list)
    traversal_direction: str = "outbound"  # outbound | inbound | both
    max_depth: int = 2
    relationship_types: list[str] = field(default_factory=list)
    budget: int = 50
    stopping_conditions: list[str] = field(default_factory=list)


@dataclass
class RetrievalStrategyPlan:
    """Output of Strategy Construction phase (SPEC-22 §9)."""
    strategy: str = "concept_first"
    retrieval_order: list[str] = field(default_factory=list)
    parallel_opportunities: list[list[str]] = field(default_factory=list)
    cache_policy: str = "read_through"
    priority_levels: dict[str, int] = field(default_factory=dict)
    early_stop_rules: list[str] = field(default_factory=list)
    fallback_sources: list[str] = field(default_factory=list)
    cost_estimate: float = 0.0
    latency_estimate_ms: float = 0.0
    confidence_targets: dict[str, float] = field(default_factory=dict)


@dataclass
class RetrievalCapabilityAnalysis:
    """Output of Capability Analysis phase (SPEC-22 §10)."""
    required_capabilities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RetrievalPlan Artifact (SPEC-22 §12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalPlan:
    """Immutable RetrievalPlan — per SPEC-22 §12."""

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

    # Knowledge Sources (from Phase 2)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)

    # Evidence Requirements (from Phase 3)
    evidence_requirements: list[dict[str, Any]] = field(default_factory=list)
    total_min_evidence: int = 0

    # Graph Traversal (from Phase 4)
    starting_nodes: list[str] = field(default_factory=list)
    traversal_direction: str = "outbound"
    max_depth: int = 2
    relationship_types: list[str] = field(default_factory=list)
    traversal_budget: int = 50
    stopping_conditions: list[str] = field(default_factory=list)

    # Strategy (from Phase 5)
    strategy: str = "concept_first"
    retrieval_order: list[str] = field(default_factory=list)
    parallel_opportunities: list[list[str]] = field(default_factory=list)
    cache_policy: str = "read_through"
    priority_levels: dict[str, int] = field(default_factory=dict)
    early_stop_rules: list[str] = field(default_factory=list)
    fallback_sources: list[str] = field(default_factory=list)
    cost_estimate: float = 0.0
    latency_estimate_ms: float = 0.0
    confidence_targets: dict[str, float] = field(default_factory=dict)

    # Capabilities (from Phase 6)
    required_capabilities: list[str] = field(default_factory=list)

    # Targets (derived from all phases)
    target_books: list[str] = field(default_factory=list)
    target_concepts: list[str] = field(default_factory=list)
    target_topics: list[str] = field(default_factory=list)
    max_retrieval_budget: int = 20
    expected_evidence_count: int = 5
    required_evidence_level: str = "any"

    # Provenance
    producer: str = "retrieval_planning"


# ---------------------------------------------------------------------------
# Retrieval Planning Pipeline
# ---------------------------------------------------------------------------


class RetrievalPlanningPipeline:
    """SPEC-22 compliant Retrieval Planning pipeline.

    Each phase is a separate method. Phases execute in order.
    Final output: RetrievalPlan artifact.
    """

    def execute(
        self,
        query_analysis: Any,
        session_id: str = "",
        knowledge_version: str = "0.0.0",
        graph_version: str = "0.0.0",
    ) -> RetrievalPlan:
        """Execute the full Retrieval Planning pipeline.

        Returns exactly one immutable RetrievalPlan.
        """
        # Extract upstream data
        concepts = getattr(query_analysis, 'concepts', [])
        entities = getattr(query_analysis, 'entities', [])
        topics = getattr(query_analysis, 'topics', [])
        book_refs = getattr(query_analysis, 'book_references', [])
        scope = getattr(query_analysis, 'scope', 'single_book')
        complexity = getattr(query_analysis, 'complexity', 'medium')
        required_reasoning = getattr(query_analysis, 'required_reasoning', 'single_source')
        intent = getattr(query_analysis, 'intent', 'question')

        # Phase 1: Preparation
        phase1 = self._phase_preparation(query_analysis)

        # Phase 2: Knowledge Source Selection
        phase2 = self._phase_source_selection(concepts, entities, topics, book_refs, scope)

        # Phase 3: Evidence Requirement Analysis
        phase3 = self._phase_evidence_requirements(intent, scope, complexity, concepts)

        # Phase 4: Graph Traversal Planning
        phase4 = self._phase_graph_traversal(concepts, entities, scope, complexity)

        # Phase 5: Strategy Construction
        phase5 = self._phase_strategy_construction(
            scope, complexity, required_reasoning, phase2, phase3, phase4
        )

        # Phase 6: Capability Analysis
        phase6 = self._phase_capability_analysis(
            scope, complexity, required_reasoning, phase3, phase4
        )

        # Phase 7: RetrievalPlan Publication
        plan = self._phase_publication(
            query_analysis, phase2, phase3, phase4, phase5, phase6,
            concepts, topics, book_refs, session_id,
            knowledge_version, graph_version,
        )

        return plan

    # ------------------------------------------------------------------
    # Phase 1: Preparation (SPEC-22 §5)
    # ------------------------------------------------------------------

    def _phase_preparation(self, query_analysis: Any) -> dict[str, Any]:
        """Validate upstream artifacts and initialize."""
        return {
            "query_analysis_valid": query_analysis is not None,
            "timestamp": datetime.now(UTC),
        }

    # ------------------------------------------------------------------
    # Phase 2: Knowledge Source Selection (SPEC-22 §6)
    # ------------------------------------------------------------------

    def _phase_source_selection(
        self,
        concepts: list[str],
        entities: list[str],
        topics: list[str],
        book_refs: list[str],
        scope: str,
    ) -> KnowledgeSourceSelection:
        """Select every knowledge source required."""
        sources = []

        # Always include chunk store (primary retrieval source)
        sources.append({
            "name": "chunk_store",
            "type": "storage",
            "justification": "Primary source for document content retrieval",
            "priority": 1,
        })

        # Include concept registry if concepts exist
        if concepts:
            sources.append({
                "name": "canonical_concept_registry",
                "type": "registry",
                "justification": f"Concepts detected: {', '.join(concepts[:3])}",
                "priority": 2,
            })

        # Include book metadata if book references exist
        if book_refs:
            sources.append({
                "name": "book_metadata_store",
                "type": "storage",
                "justification": f"Book references detected: {', '.join(book_refs[:3])}",
                "priority": 3,
            })

        # Include knowledge graph for cross-book/cross-tradition
        if scope in ("cross_book", "cross_tradition"):
            sources.append({
                "name": "knowledge_graph",
                "type": "graph",
                "justification": f"Scope requires graph traversal: {scope}",
                "priority": 2,
            })

        # Include epistemic profiles
        sources.append({
            "name": "epistemic_profile_store",
            "type": "storage",
            "justification": "Required for evidence quality assessment",
            "priority": 4,
        })

        # Include conversation memory if available
        sources.append({
            "name": "conversation_memory",
            "type": "memory",
            "justification": "Contextual continuity support",
            "priority": 5,
        })

        return KnowledgeSourceSelection(
            selected_sources=sources,
            justification=f"Selected {len(sources)} sources based on scope={scope}, concepts={len(concepts)}, entities={len(entities)}",
        )

    # ------------------------------------------------------------------
    # Phase 3: Evidence Requirement Analysis (SPEC-22 §7)
    # ------------------------------------------------------------------

    def _phase_evidence_requirements(
        self,
        intent: str,
        scope: str,
        complexity: str,
        concepts: list[str],
    ) -> EvidenceRequirementAnalysis:
        """Determine minimum evidence required."""
        requirements = []

        # Base requirement: at least one evidence source
        requirements.append(EvidenceRequirement(
            category="definition",
            min_count=1,
            required_level="any",
            cross_source=False,
        ))

        # Comparison requires multiple sources
        if intent == "comparison":
            requirements.append(EvidenceRequirement(
                category="comparison",
                min_count=2,
                required_level="empirical",
                cross_source=True,
            ))

        # Cross-book requires cross-source evidence
        if scope == "cross_book":
            requirements.append(EvidenceRequirement(
                category="cross_book",
                min_count=2,
                required_level="empirical",
                cross_source=True,
            ))

        # Cross-tradition requires cross-source evidence
        if scope == "cross_tradition":
            requirements.append(EvidenceRequirement(
                category="cross_tradition",
                min_count=2,
                required_level="any",
                cross_source=True,
            ))

        # High complexity requires more evidence
        if complexity in ("high", "very_high"):
            requirements.append(EvidenceRequirement(
                category="relationship",
                min_count=3,
                required_level="empirical",
                cross_source=False,
            ))

        total_min = sum(r.min_count for r in requirements)

        return EvidenceRequirementAnalysis(
            requirements=requirements,
            total_min_evidence=total_min,
        )

    # ------------------------------------------------------------------
    # Phase 4: Graph Traversal Planning (SPEC-22 §8)
    # ------------------------------------------------------------------

    def _phase_graph_traversal(
        self,
        concepts: list[str],
        entities: list[str],
        scope: str,
        complexity: str,
    ) -> GraphTraversalPlan:
        """Determine graph traversal parameters."""
        depth = {"low": 1, "medium": 2, "high": 3, "very_high": 4}.get(complexity, 2)
        budget = {"low": 20, "medium": 40, "high": 80, "very_high": 120}.get(complexity, 40)

        if scope in ("cross_book", "cross_tradition"):
            depth = min(depth + 1, 5)
            budget = min(budget + 30, 150)

        starting_nodes = concepts[:5] + entities[:3]

        relationship_types = ["APPEARS_IN", "BELONGS_TO", "RELATED_TO"]
        if scope == "cross_tradition":
            relationship_types.append("CROSS_TRADITION")

        stopping_conditions = ["max_depth", "max_budget", "confidence_threshold"]

        return GraphTraversalPlan(
            starting_nodes=starting_nodes,
            traversal_direction="both" if scope in ("cross_book", "cross_tradition") else "outbound",
            max_depth=depth,
            relationship_types=relationship_types,
            budget=budget,
            stopping_conditions=stopping_conditions,
        )

    # ------------------------------------------------------------------
    # Phase 5: Strategy Construction (SPEC-22 §9)
    # ------------------------------------------------------------------

    def _phase_strategy_construction(
        self,
        scope: str,
        complexity: str,
        reasoning: str,
        sources: KnowledgeSourceSelection,
        evidence: EvidenceRequirementAnalysis,
        traversal: GraphTraversalPlan,
    ) -> RetrievalStrategyPlan:
        """Construct executable retrieval strategy."""
        # Determine primary strategy
        if scope == "cross_book" or reasoning == "cross_book":
            strategy = "concept_first"
        elif scope == "cross_tradition" or reasoning == "cross_tradition":
            strategy = "topic_first"
        elif scope == "whole_library":
            strategy = "evidence_first"
        elif complexity in ("high", "very_high"):
            strategy = "concept_first"
        else:
            strategy = "book_first"

        # Determine retrieval order based on strategy
        if strategy == "concept_first":
            order = ["concept_registry", "chunk_store", "knowledge_graph", "epistemic_profiles"]
        elif strategy == "book_first":
            order = ["book_metadata", "chunk_store", "concept_registry"]
        elif strategy == "topic_first":
            order = ["topic_registry", "knowledge_graph", "chunk_store"]
        elif strategy == "evidence_first":
            order = ["chunk_store", "knowledge_graph", "epistemic_profiles", "citation_store"]
        else:
            order = ["chunk_store", "concept_registry"]

        # Determine parallel opportunities
        parallel = []
        if strategy in ("concept_first", "topic_first"):
            parallel.append(["concept_registry", "book_metadata"])
        parallel.append(["epistemic_profiles", "conversation_memory"])

        # Budget and cost
        budget = traversal.budget
        cost_estimate = budget * 0.01  # simple cost model
        latency_estimate = budget * 5.0  # ms per chunk

        # Confidence targets
        confidence_targets = {
            "evidence_completeness": 0.8,
            "concept_coverage": 0.7,
            "source_diversity": 0.6,
        }

        return RetrievalStrategyPlan(
            strategy=strategy,
            retrieval_order=order,
            parallel_opportunities=parallel,
            cache_policy="read_through",
            priority_levels={"concept": 1, "book": 2, "topic": 3},
            early_stop_rules=["confidence_threshold_met", "budget_exhausted"],
            fallback_sources=["chunk_store"],
            cost_estimate=cost_estimate,
            latency_estimate_ms=latency_estimate,
            confidence_targets=confidence_targets,
        )

    # ------------------------------------------------------------------
    # Phase 6: Capability Analysis (SPEC-22 §10)
    # ------------------------------------------------------------------

    def _phase_capability_analysis(
        self,
        scope: str,
        complexity: str,
        reasoning: str,
        evidence: EvidenceRequirementAnalysis,
        traversal: GraphTraversalPlan,
    ) -> RetrievalCapabilityAnalysis:
        """Derive retrieval capability requirements."""
        capabilities = ["chunk_retrieval", "evidence_aggregation"]

        if scope in ("cross_book", "cross_tradition"):
            capabilities.append("cross_book_retrieval")
        if scope == "cross_tradition":
            capabilities.append("cross_tradition_retrieval")
        if traversal.max_depth > 2:
            capabilities.append("graph_traversal")
        if any(r.cross_source for r in evidence.requirements):
            capabilities.append("evidence_ranking")
        if complexity in ("high", "very_high"):
            capabilities.append("large_context_retrieval")
        if len(evidence.requirements) > 3:
            capabilities.append("hybrid_retrieval")

        return RetrievalCapabilityAnalysis(
            required_capabilities=list(set(capabilities)),
        )

    # ------------------------------------------------------------------
    # Phase 7: RetrievalPlan Publication (SPEC-22 §12)
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        query_analysis: Any,
        sources: KnowledgeSourceSelection,
        evidence: EvidenceRequirementAnalysis,
        traversal: GraphTraversalPlan,
        strategy: RetrievalStrategyPlan,
        capabilities: RetrievalCapabilityAnalysis,
        concepts: list[str],
        topics: list[str],
        book_refs: list[str],
        session_id: str,
        knowledge_version: str,
        graph_version: str,
    ) -> RetrievalPlan:
        """Publish exactly one immutable RetrievalPlan."""
        # Determine budget
        budget = traversal.budget
        if strategy.strategy == "concept_first":
            budget = min(budget + len(concepts) * 3, 150)
        elif strategy.strategy == "book_first":
            budget = min(budget + len(book_refs) * 5, 100)

        plan = RetrievalPlan(
            session_id=session_id,
            query_analysis_id=str(getattr(query_analysis, 'query_length', '')),
            knowledge_version=knowledge_version,
            graph_version=graph_version,
            # Sources
            knowledge_sources=[{"name": s["name"], "type": s["type"], "justification": s["justification"]} for s in sources.selected_sources],
            # Evidence
            evidence_requirements=[{"category": r.category, "min_count": r.min_count, "level": r.required_level, "cross_source": r.cross_source} for r in evidence.requirements],
            total_min_evidence=evidence.total_min_evidence,
            # Traversal
            starting_nodes=traversal.starting_nodes,
            traversal_direction=traversal.traversal_direction,
            max_depth=traversal.max_depth,
            relationship_types=traversal.relationship_types,
            traversal_budget=traversal.budget,
            stopping_conditions=traversal.stopping_conditions,
            # Strategy
            strategy=strategy.strategy,
            retrieval_order=strategy.retrieval_order,
            parallel_opportunities=strategy.parallel_opportunities,
            cache_policy=strategy.cache_policy,
            priority_levels=strategy.priority_levels,
            early_stop_rules=strategy.early_stop_rules,
            fallback_sources=strategy.fallback_sources,
            cost_estimate=strategy.cost_estimate,
            latency_estimate_ms=strategy.latency_estimate_ms,
            confidence_targets=strategy.confidence_targets,
            # Capabilities
            required_capabilities=capabilities.required_capabilities,
            # Targets
            target_concepts=concepts,
            target_topics=topics,
            target_books=book_refs,
            max_retrieval_budget=budget,
            expected_evidence_count=evidence.total_min_evidence,
            required_evidence_level="empirical" if evidence.total_min_evidence > 2 else "any",
        )

        logger.debug(
            "retrieval_plan_published",
            plan_id=plan.plan_id,
            strategy=strategy.strategy,
            sources=len(sources.selected_sources),
            budget=budget,
        )

        return plan
