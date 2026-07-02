"""GraphReasoningEngine — single owner of reasoning over the Knowledge Graph."""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.graph_reasoning.types import (
    CacheEntry,
    CacheKey,
    Hypothesis,
    ReasoningAgreement,
    ReasoningChain,
    ReasoningConflict,
    ReasoningConfidence,
    ReasoningExplanation,
    ReasoningMetrics,
    ReasoningPolicy,
    ReasoningResult,
    ReasoningStep,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Policy Registry
# ---------------------------------------------------------------------------


class ReasoningPolicyRegistry:
    """Registry for reasoning policies."""

    def __init__(self) -> None:
        self._policies: dict[str, ReasoningPolicy] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._policies["conservative"] = ReasoningPolicy(
            id="conservative", name="Conservative",
            hypothesis_generation_behavior="conservative",
            confidence_calibration="strict",
            conflict_tolerance="low",
            uncertainty_disclosure="always",
            explanation_style="detailed",
        )
        self._policies["comparative"] = ReasoningPolicy(
            id="comparative", name="Comparative",
            hypothesis_generation_behavior="balanced",
            confidence_calibration="standard",
            conflict_tolerance="moderate",
            uncertainty_disclosure="always",
            explanation_style="comparative",
        )
        self._policies["exploratory"] = ReasoningPolicy(
            id="exploratory", name="Exploratory",
            hypothesis_generation_behavior="aggressive",
            confidence_calibration="relaxed",
            conflict_tolerance="high",
            uncertainty_disclosure="always",
            explanation_style="exploratory",
        )
        self._policies["scientific"] = ReasoningPolicy(
            id="scientific", name="Scientific",
            hypothesis_generation_behavior="evidence_based",
            confidence_calibration="strict",
            conflict_tolerance="low",
            uncertainty_disclosure="always",
            explanation_style="detailed",
        )
        self._policies["reflective"] = ReasoningPolicy(
            id="reflective", name="Reflective",
            hypothesis_generation_behavior="conservative",
            confidence_calibration="strict",
            conflict_tolerance="moderate",
            uncertainty_disclosure="always",
            explanation_style="contemplative",
        )

    def get_policy(self, policy_id: str) -> ReasoningPolicy:
        return self._policies.get(policy_id, self._policies["conservative"])

    def register_policy(self, policy: ReasoningPolicy) -> None:
        self._policies[policy.id] = policy

    def list_policies(self) -> list[str]:
        return list(self._policies.keys())


# ---------------------------------------------------------------------------
# Reasoning Cache
# ---------------------------------------------------------------------------


class ReasoningCache:
    """Context-aware reasoning cache."""

    def __init__(self, max_size: int = 1000) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: CacheKey) -> Any | None:
        key_str = key.to_string()
        entry = self._cache.get(key_str)
        if entry:
            self._hits += 1
            entry.hit_count += 1
            return entry.result
        self._misses += 1
        return None

    def put(self, key: CacheKey, result: Any) -> None:
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest = min(self._cache.values(), key=lambda e: e.created_at)
            del self._cache[oldest.key.to_string()]
        self._cache[key.to_string()] = CacheEntry(key=key, result=result)

    def invalidate_by_graph_version(self, graph_version: int) -> int:
        to_remove = [k for k, v in self._cache.items() if v.key.graph_version == graph_version]
        for k in to_remove:
            del self._cache[k]
        return len(to_remove)

    def invalidate_by_concept(self, concept: str) -> int:
        return 0  # Concept-based invalidation placeholder

    def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def clear(self) -> None:
        self._cache.clear()


class GraphRetriever:
    """Retrieves relevant nodes and edges from the Knowledge Graph."""

    def __init__(self, graph: Any = None) -> None:
        self._graph = graph

    def retrieve_by_concept(self, concept: str) -> list[Any]:
        """Retrieve nodes related to a concept."""
        if not self._graph:
            return []
        return self._graph.find_concept(concept) if hasattr(self._graph, 'find_concept') else []

    def retrieve_by_topic(self, topic: str) -> list[Any]:
        """Retrieve nodes related to a topic."""
        if not self._graph:
            return []
        return self._graph.find_topic(topic) if hasattr(self._graph, 'find_topic') else []

    def retrieve_edges(self, node_id: str) -> list[Any]:
        """Retrieve edges for a node."""
        if not self._graph:
            return []
        return self._graph.get_edges_from_node(node_id) if hasattr(self._graph, 'get_edges_from_node') else []


class PathDiscoveryEngine:
    """Discovers meaningful reasoning paths in the graph."""

    def __init__(self, graph: Any = None) -> None:
        self._graph = graph

    def find_paths(self, start: str, end: str, max_depth: int = 5) -> list[list[str]]:
        """Find all paths between two nodes."""
        if not self._graph or not hasattr(self._graph, 'find_all_paths'):
            return []
        return self._graph.find_all_paths(start, end, max_depth)


class EvidenceAggregator:
    """Collects evidence from multiple sources."""

    def aggregate(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Aggregate evidence from multiple sources."""
        aggregated = []
        seen = set()
        for source in sources:
            key = source.get("id", str(id(source)))
            if key not in seen:
                seen.add(key)
                aggregated.append(source)
        return aggregated


class HypothesisGenerator:
    """Generates candidate hypotheses from evidence."""

    def generate(self, evidence: list[dict[str, Any]], query: str) -> list[Hypothesis]:
        """Generate hypotheses from evidence."""
        hypotheses = []
        if evidence:
            hypotheses.append(Hypothesis(
                statement=f"Based on {len(evidence)} evidence sources regarding: {query}",
                supporting_evidence=[e.get("id", "") for e in evidence[:5]],
                confidence=min(0.7, len(evidence) * 0.1),
            ))
        return hypotheses


class ConflictAnalyzer:
    """Analyzes conflicts between evidence sources."""

    def analyze(self, evidence: list[dict[str, Any]]) -> list[ReasoningConflict]:
        """Analyze conflicts in evidence."""
        conflicts = []
        for i, e1 in enumerate(evidence):
            for e2 in evidence[i + 1:]:
                if e1.get("stance") != e2.get("stance") and e1.get("stance") and e2.get("stance"):
                    conflicts.append(ReasoningConflict(
                        conflict_type="epistemic",
                        description=f"Sources disagree on topic",
                        source_a=e1.get("id", ""),
                        source_b=e2.get("id", ""),
                        confidence=0.6,
                    ))
        return conflicts


class AgreementAnalyzer:
    """Analyzes agreements between evidence sources."""

    def analyze(self, evidence: list[dict[str, Any]]) -> list[ReasoningAgreement]:
        """Analyze agreements in evidence."""
        agreements = []
        for i, e1 in enumerate(evidence):
            for e2 in evidence[i + 1:]:
                if e1.get("stance") == e2.get("stance") and e1.get("stance"):
                    agreements.append(ReasoningAgreement(
                        agreement_type="agreement",
                        description="Sources agree on topic",
                        source_a=e1.get("id", ""),
                        source_b=e2.get("id", ""),
                        confidence=0.7,
                    ))
        return agreements


class ScopeAnalyzer:
    """Analyzes scope of hypotheses."""

    def analyze(self, hypothesis: Hypothesis, evidence: list[dict[str, Any]]) -> dict:
        """Analyze scope of a hypothesis."""
        return {
            "valid_contexts": ["general"],
            "invalid_contexts": [],
            "supporting_sources": len(hypothesis.supporting_evidence),
            "weakening_sources": len(hypothesis.missing_evidence),
        }


class ReasoningConfidenceAggregator:
    """Aggregates confidence from multiple sources."""

    def aggregate(self, components: dict[str, float]) -> ReasoningConfidence:
        """Aggregate confidence from components."""
        weights = {
            "retrieval": 0.15,
            "graph": 0.15,
            "evidence": 0.20,
            "interpretation": 0.15,
            "cross_book": 0.10,
            "cross_tradition": 0.10,
            "ocr": 0.05,
            "reasoning": 0.10,
        }

        overall = sum(components.get(k, 0.5) * v for k, v in weights.items())

        return ReasoningConfidence(
            retrieval_confidence=components.get("retrieval", 0.5),
            graph_confidence=components.get("graph", 0.5),
            evidence_confidence=components.get("evidence", 0.5),
            interpretation_confidence=components.get("interpretation", 0.5),
            cross_book_confidence=components.get("cross_book", 0.5),
            cross_tradition_confidence=components.get("cross_tradition", 0.5),
            ocr_confidence=components.get("ocr", 1.0),
            reasoning_confidence=components.get("reasoning", 0.5),
            overall_confidence=overall,
        )


class GraphReasoningEngine:
    """Single owner of reasoning over the Knowledge Graph.

    Transforms the Knowledge Graph from a storage system into a reasoning system.
    Policy-driven, cache-aware, version-tracked.
    """

    def __init__(
        self,
        graph: Any = None,
        policy: ReasoningPolicy | None = None,
        cache: ReasoningCache | None = None,
    ) -> None:
        self._graph = graph
        self._policy = policy or ReasoningPolicy()
        self._cache = cache or ReasoningCache()
        self._policy_registry = ReasoningPolicyRegistry()
        self._retriever = GraphRetriever(graph)
        self._path_engine = PathDiscoveryEngine(graph)
        self._evidence_aggregator = EvidenceAggregator()
        self._hypothesis_generator = HypothesisGenerator()
        self._conflict_analyzer = ConflictAnalyzer()
        self._agreement_analyzer = AgreementAnalyzer()
        self._scope_analyzer = ScopeAnalyzer()
        self._confidence_aggregator = ReasoningConfidenceAggregator()
        self._metrics = ReasoningMetrics()

    def set_policy(self, policy_id: str) -> None:
        """Set the active reasoning policy."""
        self._policy = self._policy_registry.get_policy(policy_id)

    def reason(self, query: str, context: dict[str, Any] | None = None) -> ReasoningResult:
        """Main reasoning entry point."""
        start = time.monotonic()
        ctx = context or {}

        # Check cache
        cache_key = CacheKey(
            graph_version=ctx.get("graph_version", 0),
            policy_version=self._policy.id,
            product_profile=ctx.get("product_profile", "default"),
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._metrics.cache_hit_rate = (
                self._metrics.cache_hit_rate * 0.9 + 0.1
            )
            return cached

        # Retrieve evidence
        evidence = self._retrieve_evidence(query, ctx)

        # Generate hypotheses based on policy
        hypotheses = self._hypothesis_generator.generate(evidence, query)

        # Analyze conflicts and agreements
        conflicts = self._conflict_analyzer.analyze(evidence)
        agreements = self._agreement_analyzer.analyze(evidence)

        # Aggregate confidence
        confidence = self._confidence_aggregator.aggregate({
            "evidence": min(1.0, len(evidence) / 5),
            "reasoning": 0.6,
        })

        # Build explanation
        explanation = ReasoningExplanation(
            why_conclusion=f"Based on {len(evidence)} evidence sources",
            books_contributed=[e.get("book_id", "") for e in evidence if e.get("book_id")],
            concepts_contributed=[e.get("concept", "") for e in evidence if e.get("concept")],
        )

        # Build chain
        chain = ReasoningChain(
            query=query,
            overall_confidence=confidence.overall_confidence,
        )

        duration_ms = (time.monotonic() - start) * 1000
        self._metrics.record_reasoning(duration_ms, len(hypotheses), len(conflicts))

        result = ReasoningResult(
            query=query,
            chain=chain,
            hypotheses=hypotheses,
            conflicts=conflicts,
            confidence=confidence,
            explanation=explanation,
            policy_version=self._policy.id,
        )

        # Cache the result
        self._cache.put(cache_key, result)

        return result

    def _retrieve_evidence(self, query: str, context: dict) -> list[dict[str, Any]]:
        """Retrieve evidence from the graph."""
        evidence: list[dict[str, Any]] = []

        # Retrieve by concept if provided
        concepts = context.get("concepts", [])
        for concept in concepts:
            nodes = self._retriever.retrieve_by_concept(concept)
            for node in nodes:
                evidence.append({"id": node.id, "type": node.node_type, "title": node.title})

        # Retrieve by topic if provided
        topics = context.get("topics", [])
        for topic in topics:
            nodes = self._retriever.retrieve_by_topic(topic)
            for node in nodes:
                evidence.append({"id": node.id, "type": node.node_type, "title": node.title})

        return evidence

    def reason_stream(self, query: str, context: dict[str, Any] | None = None):
        """Streaming reasoning entry point. Yields partial results."""
        ctx = context or {}

        # Yield initial state
        yield {"type": "start", "query": query}

        # Retrieve evidence
        evidence = self._retrieve_evidence(query, ctx)
        yield {"type": "evidence", "count": len(evidence), "data": evidence}

        # Generate hypotheses
        hypotheses = self._hypothesis_generator.generate(evidence, query)
        yield {"type": "hypotheses", "count": len(hypotheses), "data": [h.statement for h in hypotheses]}

        # Analyze conflicts and agreements
        conflicts = self._conflict_analyzer.analyze(evidence)
        agreements = self._agreement_analyzer.analyze(evidence)

        # Aggregate confidence
        confidence = self._confidence_aggregator.aggregate({
            "evidence": min(1.0, len(evidence) / 5),
            "reasoning": 0.6,
        })
        yield {"type": "confidence", "data": confidence.__dict__}

        # Build explanation
        explanation = ReasoningExplanation(
            why_conclusion=f"Based on {len(evidence)} evidence sources",
            books_contributed=[e.get("book_id", "") for e in evidence if e.get("book_id")],
            concepts_contributed=[e.get("concept", "") for e in evidence if e.get("concept")],
        )
        yield {"type": "explanation", "data": explanation.__dict__}

        # Build chain
        chain = ReasoningChain(
            query=query,
            overall_confidence=confidence.overall_confidence,
        )

        result = ReasoningResult(
            query=query,
            chain=chain,
            hypotheses=hypotheses,
            conflicts=conflicts,
            confidence=confidence,
            explanation=explanation,
        )

        yield {"type": "complete", "result": result}

    def reason_from_concept(self, concept_id: str, context: dict[str, Any] | None = None) -> ReasoningResult:
        """Reason from a specific concept."""
        ctx = context or {}
        ctx["concepts"] = [concept_id]
        return self.reason(f"Reasoning about concept: {concept_id}", ctx)

    def reason_from_book(self, book_id: str, context: dict[str, Any] | None = None) -> ReasoningResult:
        """Reason from a specific book."""
        ctx = context or {}
        ctx["book_id"] = book_id
        return self.reason(f"Reasoning from book: {book_id}", ctx)

    def reason_from_topic(self, topic_id: str, context: dict[str, Any] | None = None) -> ReasoningResult:
        """Reason from a specific topic."""
        ctx = context or {}
        ctx["topics"] = [topic_id]
        return self.reason(f"Reasoning about topic: {topic_id}", ctx)

    def reason_from_graph(self, node_ids: list[str], context: dict[str, Any] | None = None) -> ReasoningResult:
        """Reason from specific graph nodes."""
        ctx = context or {}
        ctx["node_ids"] = node_ids
        return self.reason(f"Reasoning from {len(node_ids)} nodes", ctx)

    def explain(self, reasoning_id: str) -> dict[str, Any]:
        """Get explanation for a reasoning result."""
        # In production, this would retrieve from storage
        return {"reasoning_id": reasoning_id, "status": "explanation_available"}

    def get_reasoning_chain(self, reasoning_id: str) -> ReasoningChain | None:
        """Get the reasoning chain for a result."""
        # In production, this would retrieve from storage
        return None

    def get_metrics(self) -> dict[str, Any]:
        """Get reasoning metrics."""
        return {
            **self._metrics.__dict__,
            "cache_stats": self._cache.get_stats(),
        }


class ReasoningMetrics:
    """Metrics for reasoning operations."""

    def __init__(self) -> None:
        self._reasoning_count: int = 0
        self._total_duration_ms: float = 0.0
        self._hypothesis_count: int = 0
        self._conflict_count: int = 0

    def record_reasoning(self, duration_ms: float, hypotheses: int, conflicts: int) -> None:
        """Record a reasoning operation."""
        self._reasoning_count += 1
        self._total_duration_ms += duration_ms
        self._hypothesis_count += hypotheses
        self._conflict_count += conflicts

    def get_metrics(self) -> dict[str, Any]:
        """Get metrics."""
        return {
            "reasoning_count": self._reasoning_count,
            "total_duration_ms": self._total_duration_ms,
            "hypothesis_count": self._hypothesis_count,
            "conflict_count": self._conflict_count,
            "average_duration_ms": self._total_duration_ms / max(1, self._reasoning_count),
        }
