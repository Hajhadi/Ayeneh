"""Redis-backed rate limiter using sliding window algorithm."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_ms: int = 0


class RateLimiter:
    """Sliding window rate limiter backed by Redis.

    Falls back to in-memory limiting when Redis is unavailable.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._memory_store: dict[str, list[float]] = {}

    async def check(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> RateLimitResult:
        if self._redis:
            return await self._check_redis(key, limit, window_seconds)
        return self._check_memory(key, limit, window_seconds)

    async def _check_redis(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            results = await pipe.execute()

            count = results[2]
            remaining = max(0, limit - count)
            allowed = count <= limit

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                retry_after_ms=int(window_seconds * 1000) if not allowed else 0,
            )
        except Exception as exc:
            logger.warning("ratelimit_redis_failed", error=str(exc))
            return self._check_memory(key, limit, window_seconds)

    def _check_memory(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds

        if key not in self._memory_store:
            self._memory_store[key] = []

        self._memory_store[key] = [
            ts for ts in self._memory_store[key] if ts > window_start
        ]

        count = len(self._memory_store[key])
        remaining = max(0, limit - count)

        if count < limit:
            self._memory_store[key].append(now)
            return RateLimitResult(allowed=True, limit=limit, remaining=remaining)

        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            retry_after_ms=int(window_seconds * 1000),
        )


class RateLimitPresets:
    """Common rate limit configurations."""

    API_DEFAULT = {"limit": 100, "window_seconds": 60}
    API_AUTH = {"limit": 10, "window_seconds": 60}
    API_UPLOAD = {"limit": 5, "window_seconds": 300}
    LLM_CALL = {"limit": 20, "window_seconds": 60}
    EMBEDDING_CALL = {"limit": 30, "window_seconds": 60}
