"""Failure manager — handles retries, circuit breaking, and graceful degradation."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from ayeneh.runtime.planner import ErrorStrategy, PlanStep

logger = structlog.get_logger(__name__)


@dataclass
class CircuitState:
    """Tracks circuit breaker state for an agent."""

    agent_name: str
    failure_count: int = 0
    last_failure: datetime | None = None
    is_open: bool = False
    open_until: datetime | None = None


class FailureManager:
    """Handles agent failures with retries, circuit breaking, and degradation."""

    def __init__(
        self,
        max_retries: int = 2,
        backoff_base: float = 0.1,
        circuit_threshold: int = 3,
        circuit_cooldown_seconds: int = 60,
    ) -> None:
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._circuit_threshold = circuit_threshold
        self._circuit_cooldown = circuit_cooldown_seconds
        self._circuits: dict[str, CircuitState] = {}

    def is_circuit_open(self, agent_name: str) -> bool:
        circuit = self._circuits.get(agent_name)
        if circuit is None or not circuit.is_open:
            return False
        if circuit.open_until and datetime.now(UTC) >= circuit.open_until:
            circuit.is_open = False
            circuit.failure_count = 0
            logger.info("circuit_reset", agent=agent_name)
            return False
        return True

    def record_failure(self, agent_name: str) -> None:
        circuit = self._circuits.setdefault(agent_name, CircuitState(agent_name=agent_name))
        circuit.failure_count += 1
        circuit.last_failure = datetime.now(UTC)
        if circuit.failure_count >= self._circuit_threshold:
            from datetime import timedelta
            circuit.is_open = True
            circuit.open_until = datetime.now(UTC) + timedelta(seconds=self._circuit_cooldown)
            logger.warning("circuit_opened", agent=agent_name, failures=circuit.failure_count)

    def record_success(self, agent_name: str) -> None:
        circuit = self._circuits.get(agent_name)
        if circuit:
            circuit.failure_count = 0

    async def handle_step_failure(
        self,
        step: PlanStep,
        error: Exception,
        retry_count: int,
    ) -> tuple[bool, str]:
        """Decide whether to retry, skip, abort, or degrade.

        Returns (should_retry, action_taken).
        """
        self.record_failure(step.agent_name)

        if step.error_strategy == ErrorStrategy.ABORT:
            logger.error("step_abort", step_id=step.step_id, agent=step.agent_name)
            return False, "abort"

        if step.error_strategy == ErrorStrategy.SKIP:
            logger.warning("step_skipped", step_id=step.step_id, agent=step.agent_name)
            return False, "skip"

        if step.error_strategy == ErrorStrategy.DEGRADE:
            logger.warning("step_degraded", step_id=step.step_id, agent=step.agent_name)
            return False, "degrade"

        if retry_count < step.max_retries:
            delay = self._backoff_base * (2 ** retry_count) + random.uniform(0, 0.05)
            logger.info("step_retrying", step_id=step.step_id, retry=retry_count + 1, delay=delay)
            await asyncio.sleep(delay)
            return True, "retry"

        logger.error("step_retry_exhausted", step_id=step.step_id, agent=step.agent_name)
        return False, "exhausted"

    def should_skip(self, agent_name: str) -> bool:
        return self.is_circuit_open(agent_name)
