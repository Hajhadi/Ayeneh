"""Provenance Module — End-to-End traceability for Ayeneh."""

from ayeneh.provenance.bundle import ProvenanceBundle, merge_bundles
from ayeneh.provenance.types import (
    ChunkOrigin,
    DocumentOrigin,
    EdgeOrigin,
    InterpretationOrigin,
    NodeOrigin,
    ReasoningOrigin,
    ResponseMetadata,
    SafetyOrigin,
)

__all__ = [
    "ChunkOrigin",
    "DocumentOrigin",
    "EdgeOrigin",
    "InterpretationOrigin",
    "NodeOrigin",
    "ProvenanceBundle",
    "ReasoningOrigin",
    "ResponseMetadata",
    "SafetyOrigin",
    "merge_bundles",
]
