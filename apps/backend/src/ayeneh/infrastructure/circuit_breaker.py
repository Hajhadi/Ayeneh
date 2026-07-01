"""Circuit breaker — prevents cascading failures from external providers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker with configurable thresholds.

    States:
    - CLOSED: normal operation, failures counted
    - OPEN: calls blocked, wait for reset window
    - HALF_OPEN: one test call allowed through
    """

    name: str = "default"
    failure_threshold: int = 5
    reset_timeout_seconds: float = 30.0
    half_open_max_calls: int = 1

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.reset_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("circuit_half_open", name=self.name)
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info("circuit_closed", name=self.name)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("circuit_reopened", name=self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_opened", name=self.name, failures=self._failure_count)

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0


@dataclass
class CircuitBreakerRegistry:
    """Registry of named circuit breakers for different providers."""

    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

    def get(self, name: str, **kwargs: Any) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name, **kwargs)
        return self._breakers[name]

    def reset_all(self) -> None:
        for b in self._breakers.values():
            b.reset()

    def get_all_states(self) -> dict[str, str]:
        return {name: b.state.value for name, b in self._breakers.items()}


class CircuitBrokenError(Exception):
    """Raised when a circuit breaker blocks a call."""

    def __init__(self, circuit_name: str, retry_after: float = 0.0) -> None:
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.0f}s")


async def call_with_circuit_breaker(
    breaker: CircuitBreaker,
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute an async function protected by a circuit breaker."""
    if breaker.is_open():
        elapsed = time.monotonic() - breaker._last_failure_time
        retry_after = max(0, breaker.reset_timeout_seconds - elapsed)
        raise CircuitBrokenError(breaker.name, retry_after)

    try:
        result = await func(*args, **kwargs)
        breaker.record_success()
        return result
    except CircuitBrokenError:
        raise
    except Exception:
        breaker.record_failure()
        raise
