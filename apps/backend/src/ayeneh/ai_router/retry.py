"""AI Router retry — retry logic for transient provider failures."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Error patterns that indicate retryable failures
_RETRYABLE_ERROR_MESSAGES = (
    "timeout",
    "timed out",
    "connection",
    "connect",
    "rate limit",
    "rate_limit",
    "429",
    "503",
    "502",
    "504",
    "econnreset",
    "econnrefused",
    "broken pipe",
    "reset by peer",
    "temporarily unavailable",
    "service unavailable",
)

_NON_RETRYABLE_ERROR_MESSAGES = (
    "authentication",
    "auth",
    "unauthorized",
    "401",
    "403",
    "forbidden",
    "invalid api key",
    "quota",
    "insufficient",
    "billing",
    "payment",
)


class RetryManager:
    """Manages retry logic with exponential backoff and jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: float = 1000,
        max_delay_ms: float = 10000,
        exponential_base: float = 2,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base

    def is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable (transient).

        Retryable: timeout, connection, rate-limit errors.
        Non-retryable: auth, quota errors.
        """
        error_str = str(error).lower()

        # Check non-retryable first — auth/quota errors should not be retried
        for pattern in _NON_RETRYABLE_ERROR_MESSAGES:
            if pattern in error_str:
                return False

        # Check retryable patterns
        for pattern in _RETRYABLE_ERROR_MESSAGES:
            if pattern in error_str:
                return True

        # Retry on generic connection/network errors
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return True

        # Check exception type names for common retryable types
        type_name = type(error).__name__.lower()
        if any(kw in type_name for kw in ("timeout", "connection", "network")):
            return True

        return False

    def get_delay(self, attempt: int) -> float:
        """Calculate delay in seconds for the given attempt (0-indexed).

        Uses exponential backoff with full jitter.
        """
        delay_ms = min(
            self.base_delay_ms * (self.exponential_base ** attempt),
            self.max_delay_ms,
        )
        # Full jitter: random value between 0 and the calculated delay
        return random.uniform(0, delay_ms) / 1000

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if we should retry after the given attempt.

        Args:
            attempt: The attempt number (0-indexed, so attempt=0 means first try failed).
            error: The exception that occurred.

        Returns:
            True if we should retry, False otherwise.
        """
        if attempt >= self.max_retries:
            return False
        return self.is_retryable(error)

    async def execute_with_retry(
        self,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an async function with retry logic.

        Args:
            func: The async callable to execute.
            *args: Positional arguments for the callable.
            **kwargs: Keyword arguments for the callable.

        Returns:
            The result of the function call.

        Raises:
            The last exception if all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if not self.should_retry(attempt, exc):
                    raise

                delay = self.get_delay(attempt)
                logger.warning(
                    "retry_attempt",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    delay_ms=round(delay * 1000, 1),
                    error=str(exc)[:200],
                )
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        raise last_error  # type: ignore[misc]
