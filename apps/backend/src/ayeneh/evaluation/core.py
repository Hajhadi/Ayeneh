"""Cognitive evaluation framework — core types and base classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class AgentType(StrEnum):
    CONVERSATION = "conversation"
    MEMORY = "memory"
    PATTERN = "pattern"
    REFLECTION = "reflection"
    BLIND_SPOT = "blind_spot"


class MetricType(StrEnum):
    GROUNDEDNESS = "groundedness"
    HALLUCINATION_RATE = "hallucination_rate"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    CONSISTENCY = "consistency"
    CITATION_CORRECTNESS = "citation_correctness"
    LATENCY_MS = "latency_ms"
    CUSTOM = "custom"


@dataclass
class EvalCase:
    """A single evaluation input + expected output pair."""
    case_id: str
    agent_type: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    difficulty: str = "standard"


@dataclass
class EvalResult:
    """Result of evaluating a single case."""
    case_id: str
    agent_type: str
    metrics: dict[str, float]
    passed: bool
    actual_output: dict[str, Any]
    judge_reasoning: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class EvalReport:
    """Aggregated report across multiple cases."""
    agent_type: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    metrics_summary: dict[str, float]
    results: list[EvalResult]
    regression_detected: bool = False
    regression_details: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class QualityThreshold:
    """Threshold for a metric that triggers CI failure."""
    metric_name: str
    min_value: float = 0.0
    max_value: float | None = None


class Evaluator(Protocol):
    """Protocol for all agent evaluators."""

    def evaluate(self, case: EvalCase, actual: dict[str, Any]) -> EvalResult: ...


class Judge(Protocol):
    """Protocol for LLM-as-a-Judge implementations."""

    def judge(
        self, input_data: dict[str, Any], expected: dict[str, Any],
        actual: dict[str, Any], context: dict[str, Any] | None = None,
    ) -> tuple[float, str]: ...
