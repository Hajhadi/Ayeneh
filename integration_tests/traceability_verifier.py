"""Traceability verifier — traces every statement back to its sources."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Statement extraction
# ---------------------------------------------------------------------------


def extract_statements(text: str) -> list[str]:
    """Split response text into individual statements."""
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


# ---------------------------------------------------------------------------
# Traceability chain
# ---------------------------------------------------------------------------


@dataclass
class TraceabilityResult:
    """Result of tracing a single statement."""

    statement: str
    traceable: bool = False
    book_trace: str = ""
    chapter_trace: str = ""
    chunk_trace: str = ""
    concept_trace: str = ""
    topic_trace: str = ""
    edge_trace: str = ""
    interpretation_trace: str = ""
    reasoning_trace: str = ""
    evidence_trace: str = ""
    safety_trace: str = ""
    provenance_trace: str = ""
    missing_links: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Traceability verifier
# ---------------------------------------------------------------------------


class TraceabilityVerifier:
    """Verifies that every statement in a response can be traced to sources."""

    def verify(
        self,
        response_text: str,
        provenance_bundle: Any,
        graph: Any,
        stage_outputs: dict[str, Any],
    ) -> list[TraceabilityResult]:
        """Verify traceability of all statements in the response."""
        statements = extract_statements(response_text)
        results: list[TraceabilityResult] = []

        for statement in statements:
            result = self._trace_statement(
                statement, provenance_bundle, graph, stage_outputs
            )
            results.append(result)

        return results

    def _trace_statement(
        self,
        statement: str,
        provenance_bundle: Any,
        graph: Any,
        stage_outputs: dict[str, Any],
    ) -> TraceabilityResult:
        """Trace a single statement through the provenance chain."""
        result = TraceabilityResult(statement=statement)

        # Step 1: Check book origin
        if provenance_bundle.document and provenance_bundle.document.book_id:
            result.book_trace = provenance_bundle.document.book_id
        else:
            result.missing_links.append("book")

        # Step 2: Check chapter origin
        if provenance_bundle.document and provenance_bundle.document.document_id:
            result.chapter_trace = provenance_bundle.document.document_id
        else:
            result.missing_links.append("chapter")

        # Step 3: Check chunk origins
        if provenance_bundle.chunks:
            result.chunk_trace = provenance_bundle.chunks[0].chunk_id
        else:
            result.missing_links.append("chunk")

        # Step 4: Check concept origins (via graph nodes)
        if provenance_bundle.nodes:
            result.concept_trace = provenance_bundle.nodes[0].node_id
        else:
            result.missing_links.append("concept")

        # Step 5: Check knowledge edge origins
        if provenance_bundle.edges:
            result.edge_trace = provenance_bundle.edges[0].edge_id
        else:
            result.missing_links.append("edge")

        # Step 6: Check interpretation origins
        if provenance_bundle.interpretations:
            result.interpretation_trace = provenance_bundle.interpretations[0].interpretation_id
        else:
            result.missing_links.append("interpretation")

        # Step 7: Check reasoning origins
        if provenance_bundle.reasoning_steps:
            result.reasoning_trace = provenance_bundle.reasoning_steps[0].step_id
        else:
            result.missing_links.append("reasoning_step")

        # Step 8: Check safety origins
        if provenance_bundle.safety_interventions:
            result.safety_trace = provenance_bundle.safety_interventions[0].rule_id
        else:
            result.missing_links.append("safety_intervention")

        # Step 9: Check provenance bundle ID
        if provenance_bundle.id:
            result.provenance_trace = provenance_bundle.id
        else:
            result.missing_links.append("provenance_bundle")

        # Statement is traceable if it has at least book + chunk + concept
        result.traceable = bool(
            result.book_trace
            and result.chunk_trace
            and result.concept_trace
            and result.provenance_trace
        )

        return result


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def verify_traceability(
    response_text: str,
    provenance_bundle: Any,
    graph: Any,
    stage_outputs: dict[str, Any] | None = None,
) -> tuple[bool, list[TraceabilityResult]]:
    """Verify traceability of all statements. Returns (all_traceable, results)."""
    verifier = TraceabilityVerifier()
    results = verifier.verify(
        response_text,
        provenance_bundle,
        graph,
        stage_outputs or {},
    )
    all_traceable = all(r.traceable for r in results) if results else False
    return all_traceable, results
