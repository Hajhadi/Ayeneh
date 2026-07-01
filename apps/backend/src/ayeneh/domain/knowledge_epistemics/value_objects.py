"""Epistemic value objects — immutable typed values for knowledge source properties."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Applicability:
    """Where and under what conditions this source is applicable."""

    contexts: list[str]
    conditions: list[str]
    contraindications: list[str]


@dataclass(frozen=True)
class Limitation:
    """A known limitation of this knowledge source."""

    description: str
    severity: str  # "minor" | "moderate" | "significant" | "critical"
    affected_domains: list[str]


@dataclass(frozen=True)
class ScopeBoundary:
    """What this source covers and what it explicitly excludes."""

    included_topics: list[str]
    excluded_topics: list[str]
    overlap_notes: list[str]


@dataclass(frozen=True)
class CitationPolicy:
    """How this source should be cited."""

    required: bool
    format: str  # "inline" | "footnote" | "endnote" | "author-date"
    min_confidence: float
    notes: str = ""


@dataclass(frozen=True)
class TranslationMetadata:
    """Translation details for non-original-language sources."""

    translator: str | None
    original_language: str
    translation_year: int | None
    translation_notes: str = ""


@dataclass(frozen=True)
class SourceReliability:
    """Reliability assessment of this knowledge source."""

    score: float  # 0.0 - 1.0
    basis: str  # "peer_reviewed" | "scholarly_consensus" | "expert_opinion" | "traditional" | "mixed"
    notes: str = ""
