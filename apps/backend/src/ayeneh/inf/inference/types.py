"""INF-01 Inference Engine types.

Defines InferenceObject, InferenceResult, and supporting value objects
for the evidence-based reasoning pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

INFERENCE_TYPES: list[str] = [
    'descriptive',
    'behavioral',
    'causal',
    'identity',
    'narrative',
    'goal',
    'planning',
    'predictive',
    'meta_cognitive',
    'reality_calibration',
]

EVIDENCE_STANDARDS: dict[str, float] = {
    'descriptive': 0.5,
    'behavioral': 0.6,
    'causal': 0.7,
    'identity': 0.9,
    'narrative': 0.6,
    'goal': 0.5,
    'planning': 0.5,
    'predictive': 0.4,
    'meta_cognitive': 0.7,
    'reality_calibration': 0.8,
}

INFERENCE_VALIDATION_STATUSES: list[str] = [
    'candidate',
    'provisional',
    'validated',
    'contradicted',
    'refined',
    'archived',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReasoningStep:
    """A single step in the inference reasoning chain."""

    step_id: str
    description: str
    input_evidence: tuple[str, ...] = ()
    output_conclusion: str = ''
    confidence: float = 0.0
    reasoning_method: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompetingHypothesis:
    """An alternative hypothesis that competes with the primary inference."""

    hypothesis_id: str
    statement: str
    confidence: float = 0.0
    supporting_evidence: tuple[str, ...] = ()
    explanation: str = ''


@dataclass(frozen=True)
class ContradictionRecord:
    """Records a contradiction between inferences or evidence."""

    contradiction_id: str
    inference_id_a: str
    inference_id_b: str
    description: str = ''
    severity: float = 0.0
    resolution: str = ''


@dataclass(frozen=True)
class EvidenceQualityAssessment:
    """Multi-dimensional assessment of evidence quality."""

    directness: float = 0.5
    specificity: float = 0.5
    temporal_proximity: float = 0.5
    consistency: float = 0.5
    source_reliability: float = 0.5

    def overall(self) -> float:
        """Weighted average across all dimensions."""
        return (
            self.directness * 0.25
            + self.specificity * 0.20
            + self.temporal_proximity * 0.20
            + self.consistency * 0.20
            + self.source_reliability * 0.15
        )


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InferenceObject:
    """A single inference produced by the reasoning engine (INF-01)."""

    inference_id: str
    context_id: str
    inference_type: str
    statement: str
    supporting_evidence: tuple[str, ...] = ()
    evidence_quality: float = 0.0
    reasoning_chain: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    competing_hypotheses: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    associated_memories: tuple[str, ...] = ()
    associated_graph_nodes: tuple[str, ...] = ()
    version_history: tuple[dict[str, Any], ...] = ()
    explainability_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class InferenceResult:
    """Complete result of the inference pipeline."""

    inferences: tuple[InferenceObject, ...] = ()
    evidence_assessment: EvidenceQualityAssessment = field(
        default_factory=EvidenceQualityAssessment,
    )
    reasoning_steps: tuple[ReasoningStep, ...] = ()
    competing_hypotheses: tuple[CompetingHypothesis, ...] = ()
    contradictions: tuple[ContradictionRecord, ...] = ()
    calibration_notes: tuple[str, ...] = ()
    overall_confidence: float = 0.0
    processing_metadata: dict[str, Any] = field(default_factory=dict)
