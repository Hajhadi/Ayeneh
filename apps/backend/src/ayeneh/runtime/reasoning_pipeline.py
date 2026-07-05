"""Runtime Reasoning Engine Pipeline — per SPEC-24.

Transforms retrieved evidence into structured conclusions.
Preserves provenance, uncertainty, and epistemic integrity.

Processing Phases (SPEC-24 §4):
1. Preparation
2. Evidence Interpretation
3. Reasoning Execution
4. Confidence Assessment
5. ReasoningResult Publication
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Reasoning Result Artifact (SPEC-24 §15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReasoningResult:
    """Immutable reasoning result — per SPEC-24 §15."""

    # Identity
    reasoning_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    request_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    reasoning_version: str = "1.0.0"
    provider_version: str = "0.0.0"

    # Reasoning mode
    reasoning_mode: str = "single_source"  # single_source | cross_book | cross_tradition | comparative | hierarchical | relationship | definition | methodological | conversation | meta

    # Conclusions
    conclusions: list[dict[str, Any]] = field(default_factory=list)

    # Evidence references
    evidence_references: list[dict[str, Any]] = field(default_factory=list)

    # Conflicts
    conflicts: list[dict[str, Any]] = field(default_factory=list)

    # Assumptions
    assumptions: list[dict[str, Any]] = field(default_factory=list)

    # Uncertainty
    uncertainty_statements: list[str] = field(default_factory=list)

    # Confidence
    overall_confidence: float = 0.0
    confidence_components: dict[str, float] = field(default_factory=dict)

    # Metadata
    duration_ms: float = 0.0
    provider_used: str = ""
    producer: str = "reasoning_engine"


# ---------------------------------------------------------------------------
# Evidence Interpretation (SPEC-24 §6)
# ---------------------------------------------------------------------------


@dataclass
class EvidenceInterpretation:
    """Interpreted evidence for reasoning."""
    facts: list[dict[str, Any]] = field(default_factory=list)
    evidence_graph: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    ranking: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reasoning Pipeline
# ---------------------------------------------------------------------------


class ReasoningPipeline:
    """SPEC-24 compliant Reasoning pipeline.

    Transforms retrieved evidence into structured conclusions.
    Uses AI Router for LLM-based reasoning when available (REA-007/021).
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._graph_reasoner = None
        self._ai_router = ai_router

    def _init(self) -> None:
        if self._graph_reasoner is None:
            from ayeneh.graph_reasoning.engine import GraphReasoningEngine
            self._graph_reasoner = GraphReasoningEngine()

    def execute(
        self,
        retrieval_result: Any,
        query_analysis: Any = None,
        session_id: str = "",
        knowledge_version: str = "0.0.0",
        graph_version: str = "0.0.0",
    ) -> ReasoningResult:
        """Execute the full Reasoning pipeline."""
        self._init()
        start = time.monotonic()

        # Phase 1: Preparation
        phase1 = self._phase_preparation(retrieval_result, query_analysis)

        # Phase 2: Evidence Interpretation
        phase2 = self._phase_evidence_interpretation(retrieval_result, query_analysis)

        # Phase 3: Reasoning Execution
        phase3 = self._phase_reasoning_execution(phase2, query_analysis)

        # Phase 4: Confidence Assessment
        phase4 = self._phase_confidence_assessment(phase3, phase2)

        # Phase 5: Publication
        duration_ms = (time.monotonic() - start) * 1000
        result = self._phase_publication(
            retrieval_result, phase2, phase3, phase4,
            session_id, knowledge_version, graph_version, duration_ms,
        )

        logger.debug(
            "reasoning_complete",
            reasoning_id=result.reasoning_id,
            mode=result.reasoning_mode,
            conclusions=len(result.conclusions),
            conflicts=len(result.conflicts),
            confidence=result.overall_confidence,
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: Preparation (SPEC-24 §5)
    # ------------------------------------------------------------------

    def _phase_preparation(self, retrieval_result: Any, query_analysis: Any) -> dict[str, Any]:
        """Validate upstream artifacts."""
        chunks = getattr(retrieval_result, 'chunks', [])
        return {
            "retrieval_valid": retrieval_result is not None,
            "chunks_available": len(chunks),
            "query_analysis_valid": query_analysis is not None,
        }

    # ------------------------------------------------------------------
    # Phase 2: Evidence Interpretation (SPEC-24 §6)
    # ------------------------------------------------------------------

    def _phase_evidence_interpretation(
        self, retrieval_result: Any, query_analysis: Any
    ) -> EvidenceInterpretation:
        """Convert retrieved evidence into reasoning representation."""
        chunks = getattr(retrieval_result, 'chunks', [])
        profiles = getattr(retrieval_result, 'epistemic_profiles', [])
        books = getattr(retrieval_result, 'books', [])

        # Extract facts from chunks
        facts = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content and len(content) > 50:
                facts.append({
                    "type": "evidence",
                    "source": chunk.get("book_title", "unknown"),
                    "content": content[:500],
                    "chunk_id": chunk.get("id", ""),
                    "confidence": 0.8,
                })

        # Build evidence graph (simple: facts linked by source)
        evidence_graph = []
        for i, fact in enumerate(facts):
            for j, other in enumerate(facts):
                if i < j and fact["source"] == other["source"]:
                    evidence_graph.append({
                        "type": "same_source",
                        "fact_a": i,
                        "fact_b": j,
                        "source": fact["source"],
                    })

        # Detect conflicts (simple: opposing claims)
        conflicts = []
        for i, fact in enumerate(facts):
            for j, other in enumerate(facts):
                if i < j and fact["source"] != other["source"]:
                    # Simple conflict detection: check for negation patterns
                    content_a = fact["content"].lower()
                    content_b = other["content"].lower()
                    if ("not" in content_a and "not" not in content_b) or \
                       ("not" not in content_a and "not" in content_b):
                        conflicts.append({
                            "type": "potential_contradiction",
                            "fact_a": i,
                            "fact_b": j,
                            "source_a": fact["source"],
                            "source_b": other["source"],
                            "confidence": 0.5,
                        })

        # Rank evidence by source diversity and content length
        ranking = []
        for i, fact in enumerate(facts):
            ranking.append({
                "fact_index": i,
                "score": len(fact["content"]) * 0.001 + (1.0 if fact["source"] != facts[0]["source"] else 0.5),
                "source": fact["source"],
            })
        ranking.sort(key=lambda x: x["score"], reverse=True)

        return EvidenceInterpretation(
            facts=facts,
            evidence_graph=evidence_graph,
            conflicts=conflicts,
            ranking=ranking,
        )

    # ------------------------------------------------------------------
    # Phase 3: Reasoning Execution (SPEC-24 §7)
    # ------------------------------------------------------------------

    def _phase_reasoning_execution(
        self, interpretation: EvidenceInterpretation, query_analysis: Any
    ) -> dict[str, Any]:
        """Execute reasoning over interpreted evidence.

        When AI Router is available, uses LLM for complex reasoning.
        Falls back to local rule-based reasoning otherwise.
        """
        facts = interpretation.facts
        conflicts = interpretation.conflicts

        # Determine reasoning mode
        intent = getattr(query_analysis, 'intent', 'question') if query_analysis else 'question'
        scope = getattr(query_analysis, 'scope', 'single_book') if query_analysis else 'single_book'

        if scope == "cross_book" or len(set(f.get("source", "") for f in facts)) > 1:
            mode = "cross_book"
        elif intent == "comparison":
            mode = "comparative"
        elif intent == "definition":
            mode = "definition"
        elif intent == "methodology":
            mode = "methodological"
        else:
            mode = "single_source"

        # Try LLM-based reasoning via AI Router if available and complex enough
        llm_conclusions = None
        if self._ai_router and mode in ("cross_book", "comparative", "cross_tradition"):
            llm_conclusions = self._try_llm_reasoning(facts, conflicts, mode, query_analysis)

        # Generate conclusions: use LLM results if available, else local
        if llm_conclusions:
            conclusions = llm_conclusions
        else:
            conclusions = []
            for fact in facts:
                conclusions.append({
                    "statement": fact["content"][:200],
                    "source": fact["source"],
                    "evidence_type": "retrieved_chunk",
                    "confidence": fact.get("confidence", 0.7),
                    "provenance": {"chunk_id": fact.get("chunk_id", ""), "source": fact["source"]},
                })

        # Generate uncertainty statements
        uncertainty = []
        if conflicts:
            uncertainty.append(f"Found {len(conflicts)} potential conflicts between sources")
        if len(facts) < 3:
            uncertainty.append("Limited evidence available for this query")
        if mode == "cross_book":
            uncertainty.append("Cross-book reasoning involves multiple perspectives")
        if llm_conclusions:
            uncertainty.append("Conclusions generated via LLM-assisted reasoning")

        # Assumptions
        assumptions = []
        for fact in facts:
            assumptions.append({
                "assumption": f"Source '{fact['source']}' provides reliable evidence",
                "confidence": fact.get("confidence", 0.7),
                "revisable": True,
            })

        return {
            "mode": mode,
            "conclusions": conclusions,
            "conflicts": conflicts,
            "assumptions": assumptions,
            "uncertainty": uncertainty,
        }

    def _try_llm_reasoning(
        self, facts: list[dict], conflicts: list[dict], mode: str, query_analysis: Any
    ) -> list[dict[str, Any]] | None:
        """Attempt LLM-based reasoning via AI Router. Returns None on failure."""
        try:
            import asyncio
            from ayeneh.ai_router.types import AITask, AITaskType

            # Build evidence summary for LLM
            evidence_text = "\n".join(
                f"- [{f.get('source', 'unknown')}] {f.get('content', '')[:300]}"
                for f in facts[:10]
            )
            conflict_text = ""
            if conflicts:
                conflict_text = "\nPotential conflicts:\n" + "\n".join(
                    f"- {c.get('type', 'unknown')}" for c in conflicts[:5]
                )

            user_message = (
                f"Based on the following evidence, provide structured conclusions "
                f"for a {mode} reasoning task.\n\n"
                f"Evidence:\n{evidence_text}\n{conflict_text}\n\n"
                f"Return a JSON array of conclusions, each with: "
                f"statement, source, confidence (0-1)."
            )

            messages = [
                {"role": "system", "content": "You are a knowledge reasoning assistant. Analyze evidence and provide structured conclusions."},
                {"role": "user", "content": user_message},
            ]

            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=user_message,
                max_tokens=1024,
                temperature=0.3,
            )

            # Run async router in sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                return None  # Can't block in async context

            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse LLM response
            import json
            # Try to extract JSON array from response
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                raw_conclusions = json.loads(content[start:end])
                conclusions = []
                for c in raw_conclusions[:10]:
                    conclusions.append({
                        "statement": c.get("statement", "")[:200],
                        "source": c.get("source", "unknown"),
                        "evidence_type": "llm_reasoned",
                        "confidence": float(c.get("confidence", 0.6)),
                        "provenance": {"method": "ai_router_llm", "mode": mode},
                    })
                return conclusions if conclusions else None

        except Exception as exc:
            logger.debug("llm_reasoning_fallback", error=str(exc))

        return None

    # ------------------------------------------------------------------
    # Phase 4: Confidence Assessment (SPEC-24 §10)
    # ------------------------------------------------------------------

    def _phase_confidence_assessment(
        self, reasoning: dict, interpretation: EvidenceInterpretation
    ) -> dict[str, Any]:
        """Assess confidence for all conclusions."""
        conclusions = reasoning.get("conclusions", [])
        conflicts = reasoning.get("conflicts", [])

        # Evidence quality (average of source confidences)
        evidence_quality = 0.7
        if conclusions:
            evidence_quality = sum(c.get("confidence", 0.5) for c in conclusions) / len(conclusions)

        # Evidence quantity
        evidence_quantity = min(1.0, len(conclusions) * 0.2)

        # Agreement level (inverse of conflicts)
        total_pairs = max(1, len(conclusions) * (len(conclusions) - 1) // 2)
        agreement_level = 1.0 - (len(conflicts) / total_pairs) if total_pairs > 0 else 1.0

        # Conflict severity
        conflict_severity = min(1.0, len(conflicts) * 0.3)

        # Retrieval completeness
        retrieval_completeness = min(1.0, len(conclusions) / 5)

        # Overall confidence
        overall = (
            evidence_quality * 0.25 +
            evidence_quantity * 0.15 +
            agreement_level * 0.20 +
            (1.0 - conflict_severity) * 0.15 +
            retrieval_completeness * 0.10 +
            0.5 * 0.15  # base confidence
        )

        return {
            "overall": round(overall, 3),
            "evidence_quality": round(evidence_quality, 3),
            "evidence_quantity": round(evidence_quantity, 3),
            "agreement_level": round(agreement_level, 3),
            "conflict_severity": round(conflict_severity, 3),
            "retrieval_completeness": round(retrieval_completeness, 3),
        }

    # ------------------------------------------------------------------
    # Phase 5: ReasoningResult Publication (SPEC-24 §15)
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        retrieval_result: Any,
        interpretation: EvidenceInterpretation,
        reasoning: dict,
        confidence: dict,
        session_id: str,
        knowledge_version: str,
        graph_version: str,
        duration_ms: float,
    ) -> ReasoningResult:
        """Publish exactly one immutable ReasoningResult."""
        return ReasoningResult(
            session_id=session_id,
            reasoning_mode=reasoning.get("mode", "single_source"),
            conclusions=reasoning.get("conclusions", []),
            evidence_references=[{"fact": f, "source": f.get("source", "")} for f in interpretation.facts],
            conflicts=reasoning.get("conflicts", []),
            assumptions=reasoning.get("assumptions", []),
            uncertainty_statements=reasoning.get("uncertainty", []),
            overall_confidence=confidence.get("overall", 0.5),
            confidence_components=confidence,
            knowledge_version=knowledge_version,
            graph_version=graph_version,
            duration_ms=duration_ms,
        )
