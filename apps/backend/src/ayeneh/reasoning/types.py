"""Deliberative Reasoning Engine — core domain types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class EvidenceSource(StrEnum):
    GOAL = "goal"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    PATTERN = "pattern"
    REFLECTION = "reflection"
    BLIND_SPOT = "blind_spot"
    CONVERSATION = "conversation"


@dataclass
class Evidence:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_type: str = ""
    source_id: str = ""
    content: str = ""
    confidence: float = 0.5
    relevance: float = 0.5
    recency_days: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypothesis:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    claim: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    opposing_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    missing_evidence: list[str] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)


@dataclass
class Conflict:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    conflict_type: str = ""
    description: str = ""
    evidence_a: str = ""
    evidence_b: str = ""
    source_a: str = ""
    source_b: str = ""
    severity: float = 0.5
    resolution_status: str = "unresolved"


@dataclass
class ReasoningStep:
    stage: str = ""
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = True


class ReasoningStage(StrEnum):
    UNDERSTAND = "understand_request"
    OBJECTIVE = "determine_objective"
    EVIDENCE = "collect_evidence"
    MISSING = "detect_missing_information"
    HYPOTHESIS = "generate_hypotheses"
    EVALUATE = "evaluate_hypotheses"
    CONFLICTS = "resolve_conflicts"
    CONFIDENCE = "estimate_confidence"
    SUMMARY = "build_reasoning_summary"


@dataclass
class ReasoningSummary:
    objective: str = ""
    reasoning_path: list[str] = field(default_factory=list)
    selected_evidence: list[dict[str, Any]] = field(default_factory=list)
    ignored_evidence: list[dict[str, Any]] = field(default_factory=list)
    alternative_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = field(default_factory=list)
    questions_for_clarification: list[str] = field(default_factory=list)
    total_evidence_evaluated: int = 0
    alternatives_considered: int = 0
    conflicts_detected: int = 0
    uncertainty_reasons: list[str] = field(default_factory=list)


@dataclass
class ReasoningSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    user_id: str = ""
    objective: str = ""
    query: str = ""
    assumptions: list[str] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    alternatives: list[Hypothesis] = field(default_factory=list)
    confidence_evolution: list[float] = field(default_factory=list)
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    summary: ReasoningSummary = field(default_factory=ReasoningSummary)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return (datetime.now(UTC) - self.start_time).total_seconds() * 1000

    def add_step(self, stage: str, description: str, inputs: list[str] | None = None,
                 outputs: list[str] | None = None, duration_ms: float = 0.0) -> ReasoningStep:
        step = ReasoningStep(
            stage=stage, description=description,
            inputs=inputs or [], outputs=outputs or [], duration_ms=duration_ms,
        )
        self.reasoning_steps.append(step)
        return step
