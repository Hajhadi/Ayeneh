"""Provenance types — immutable provenance objects for traceability."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentOrigin:
    """Origin reference for a document."""

    document_id: str = ""
    book_id: str = ""
    title: str = ""
    author: str = ""


@dataclass(frozen=True)
class ChunkOrigin:
    """Origin reference for a chunk."""

    chunk_id: str = ""
    chapter_id: str = ""
    page_number: int = 0
    character_start: int = 0
    character_end: int = 0
    text_origin: str = "native"
    ocr_confidence: float = 1.0
    ocr_engine: str = ""
    ocr_model: str = ""


@dataclass(frozen=True)
class NodeOrigin:
    """Origin reference for a knowledge graph node."""

    node_id: str = ""
    node_type: str = ""
    title: str = ""


@dataclass(frozen=True)
class EdgeOrigin:
    """Origin reference for a knowledge graph edge."""

    edge_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    relation_type: str = ""


@dataclass(frozen=True)
class ReasoningOrigin:
    """Origin reference for a reasoning step."""

    step_id: str = ""
    step_type: str = ""
    description: str = ""
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InterpretationOrigin:
    """Origin reference for an interpretation."""

    interpretation_id: str = ""
    interpretation_kind: str = ""
    confidence: float = 0.5


@dataclass(frozen=True)
class SafetyOrigin:
    """Origin reference for a safety intervention."""

    rule_id: str = ""
    rule_name: str = ""
    before_text: str = ""
    after_text: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ResponseMetadata:
    """Metadata for a generated response."""

    provenance_bundle_id: str = ""
    cited_chunks: list[str] = field(default_factory=list)
    interpretation_ids: list[str] = field(default_factory=list)
    graph_nodes: list[str] = field(default_factory=list)
    graph_edges: list[str] = field(default_factory=list)
    retrieval_ids: list[str] = field(default_factory=list)
    engine_versions: dict[str, str] = field(default_factory=dict)
    timestamp: str = ""
