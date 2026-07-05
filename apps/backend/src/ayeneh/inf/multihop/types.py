"""INF-03 Multi-Hop Reasoning types.

Defines MultiHopChain, MultiHopResult, and supporting value objects
for recursive reasoning chains across cognitive dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

HOP_TYPES: list[str] = [
    'observation_to_behavioral',
    'behavioral_to_identity',
    'identity_to_narrative',
    'narrative_to_meta_cognitive',
    'meta_cognitive_to_reality_calibration',
]

REASONING_DIMENSIONS: list[str] = [
    'observation',
    'behavioral',
    'identity',
    'narrative',
    'meta_cognitive',
    'reality_calibration',
]

LOOP_TYPES: list[str] = [
    'observation_interpretation_loop',
    'narrative_behavior_loop',
    'belief_confirmation_loop',
    'identity_reinforcement_loop',
    'meta_cognitive_reflexive_loop',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReasoningHop:
    """A single hop in a multi-hop reasoning chain."""

    hop_id: str
    hop_type: str
    source_dimension: str
    target_dimension: str
    source_statement: str
    target_statement: str
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()
    reasoning_method: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NarrativeLoop:
    """A detected self-reinforcing narrative loop."""

    loop_id: str
    loop_type: str
    node_ids: tuple[str, ...] = ()
    statements: tuple[str, ...] = ()
    reinforcement_strength: float = 0.0
    description: str = ''
    evidence_count: int = 0


@dataclass(frozen=True)
class HiddenPattern:
    """A pattern discovered through multi-hop reasoning."""

    pattern_id: str
    pattern_type: str
    description: str = ''
    confidence: float = 0.0
    hop_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiHopChain:
    """A complete multi-hop reasoning chain (INF-03)."""

    chain_id: str
    starting_observation: str
    hops: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    depth: int = 0
    alternative_chains: tuple[str, ...] = ()
    hidden_patterns: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class MultiHopResult:
    """Complete result of the multi-hop reasoning pipeline."""

    chains: tuple[MultiHopChain, ...] = ()
    narrative_loops: tuple[NarrativeLoop, ...] = ()
    hidden_patterns: tuple[HiddenPattern, ...] = ()
    overall_confidence: float = 0.0
    calibration_notes: tuple[str, ...] = ()
    processing_metadata: dict[str, Any] = field(default_factory=dict)
