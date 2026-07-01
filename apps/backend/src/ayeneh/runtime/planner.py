"""Execution planner — determines which agents run and in what order."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorStrategy(StrEnum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    DEGRADE = "degrade"


@dataclass
class PlanStep:
    """Single step in an execution plan."""

    step_id: str
    agent_name: str
    input_binding: dict[str, Any] = field(default_factory=dict)
    error_strategy: ErrorStrategy = ErrorStrategy.RETRY
    timeout_seconds: int = 30
    optional: bool = False
    condition: str | None = None
    max_retries: int = 1
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Structured execution plan — a DAG of agent steps."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: list[PlanStep] = field(default_factory=list)
    strategy: str = "rule_based"
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class PlanTemplate:
    """A pre-defined plan template for known request patterns."""

    def __init__(
        self,
        name: str,
        match_keywords: list[str],
        steps: list[PlanStep],
        confidence: float = 0.9,
    ) -> None:
        self.name = name
        self.match_keywords = match_keywords
        self.steps = steps
        self.confidence = confidence

    def score(self, request_text: str) -> float:
        text_lower = request_text.lower()
        matches = sum(1 for kw in self.match_keywords if kw in text_lower)
        if not self.match_keywords:
            return 0.0
        return matches / len(self.match_keywords)


class RulePlanner:
    """Deterministic fast path — evaluates templates, never calls LLM."""

    def __init__(self, templates: list[PlanTemplate] | None = None) -> None:
        self._templates = templates or []

    def evaluate(self, request_text: str) -> tuple[ExecutionPlan | None, float]:
        best_template: PlanTemplate | None = None
        best_score = 0.0

        for template in self._templates:
            score = template.score(request_text)
            if score > best_score:
                best_score = score
                best_template = template

        if best_template and best_score > 0:
            plan = ExecutionPlan(
                steps=[PlanStep(
                    step_id=f"s{i}",
                    agent_name=step.agent_name,
                    input_binding=step.input_binding.copy(),
                    error_strategy=step.error_strategy,
                    timeout_seconds=step.timeout_seconds,
                    optional=step.optional,
                    dependencies=list(step.dependencies),
                ) for i, step in enumerate(best_template.steps)],
                strategy="rule_based",
                confidence=best_score,
                metadata={"template": best_template.name},
            )
            return plan, best_score

        return None, 0.0


class LLMPlanner:
    """Adaptive path — invoked when Rule Planner confidence is below threshold."""

    def __init__(self, agent_catalog: dict[str, dict[str, Any]] | None = None) -> None:
        self._catalog = agent_catalog or {}

    async def generate_plan(self, request_text: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        """Placeholder — would call LLM to produce a plan."""
        logger.info("llm_planner_invoked", request_text_length=len(request_text))
        return ExecutionPlan(
            steps=[
                PlanStep(step_id="s1", agent_name="conversation"),
            ],
            strategy="llm_assisted",
            confidence=0.7,
        )


class ExecutionPlanner:
    """Top-level planner — hybrid strategy with validation."""

    def __init__(
        self,
        rule_planner: RulePlanner,
        llm_planner: LLMPlanner,
        confidence_threshold: float = 0.5,
        registered_agents: set[str] | None = None,
    ) -> None:
        self._rule_planner = rule_planner
        self._llm_planner = llm_planner
        self._confidence_threshold = confidence_threshold
        self._registered_agents = registered_agents or set()

    async def plan(
        self, request_text: str, context: dict[str, Any] | None = None
    ) -> ExecutionPlan:
        rule_plan, confidence = self._rule_planner.evaluate(request_text)

        if rule_plan and confidence >= self._confidence_threshold:
            validated = self._validate(rule_plan)
            logger.info("plan_created", strategy="rule_based", confidence=confidence)
            return validated

        logger.info("plan_escalated", rule_confidence=confidence)
        llm_plan = await self._llm_planner.generate_plan(request_text, context)
        validated = self._validate(llm_plan)
        logger.info("plan_created", strategy="llm_assisted", confidence=validated.confidence)
        return validated

    def _validate(self, plan: ExecutionPlan) -> ExecutionPlan:
        valid_steps: list[PlanStep] = []
        seen_ids: set[str] = set()
        for step in plan.steps:
            if step.step_id in seen_ids:
                continue
            seen_ids.add(step.step_id)
            if self._registered_agents and step.agent_name not in self._registered_agents:
                logger.warning("agent_not_registered", agent=step.agent_name)
                continue
            valid_steps.append(step)
        plan.steps = valid_steps
        return plan
