"""Retry policies with exponential backoff for external provider calls."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RetryPolicy:
    """Configurable retry policy with exponential backoff and jitter."""

    max_retries: int = 3
    base_delay_ms: float = 100.0
    max_delay_ms: float = 5000.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay_ms * (self.backoff_factor ** attempt),
            self.max_delay_ms,
        )
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay


async def call_with_retry(
    policy: RetryPolicy,
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic."""
    last_error: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except policy.retryable_exceptions as exc:
            last_error = exc
            if attempt < policy.max_retries:
                delay_ms = policy.get_delay(attempt)
                logger.warning(
                    "retrying_call",
                    attempt=attempt + 1,
                    max_retries=policy.max_retries,
                    delay_ms=round(delay_ms, 1),
                    error=str(exc),
                )
                await asyncio.sleep(delay_ms / 1000)

    raise last_error or RuntimeError("retry_policy_exhausted")


class RetryPolicyRegistry:
    """Pre-configured retry policies for different provider types."""

    def __init__(self) -> None:
        self.llm = RetryPolicy(
            max_retries=3, base_delay_ms=500, backoff_factor=2.0,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
        self.embedding = RetryPolicy(
            max_retries=2, base_delay_ms=200, backoff_factor=1.5,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
        self.database = RetryPolicy(
            max_retries=3, base_delay_ms=100, backoff_factor=2.0,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
        self.redis = RetryPolicy(
            max_retries=2, base_delay_ms=50, backoff_factor=2.0,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
