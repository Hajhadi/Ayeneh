"""Redis-backed distributed cache with fallback to in-memory."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class DistributedCache:
    """Distributed cache backed by Redis with local in-memory fallback."""

    def __init__(self, redis_client: Any | None = None, default_ttl: int = 300) -> None:
        self._redis = redis_client
        self._default_ttl = default_ttl
        self._memory: dict[str, CacheEntry] = {}
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    async def get(self, key: str) -> Any | None:
        if self._redis:
            try:
                raw = await self._redis.get(f"cache:{key}")
                if raw:
                    self._stats["hits"] += 1
                    return json.loads(raw)
            except Exception as exc:
                logger.warning("cache_redis_get_failed", error=str(exc))

        entry = self._memory.get(key)
        if entry and time.time() < entry.expires_at:
            self._stats["hits"] += 1
            return entry.value

        self._stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or self._default_ttl

        if self._redis:
            try:
                await self._redis.setex(
                    f"cache:{key}", ttl, json.dumps(value, default=str)
                )
            except Exception as exc:
                logger.warning("cache_redis_set_failed", error=str(exc))

        self._memory[key] = CacheEntry(
            value=value,
            expires_at=time.time() + ttl,
        )
        self._stats["sets"] += 1

    async def delete(self, key: str) -> None:
        if self._redis:
            try:
                await self._redis.delete(f"cache:{key}")
            except Exception:
                pass

        self._memory.pop(key, None)
        self._stats["deletes"] += 1

    async def invalidate_pattern(self, pattern: str) -> int:
        count = 0
        if self._redis:
            try:
                keys = []
                async for key in self._redis.scan_iter(f"cache:{pattern}*"):
                    keys.append(key)
                if keys:
                    count = await self._redis.delete(*keys)
            except Exception:
                pass

        prefix = pattern.rstrip("*")
        to_remove = [k for k in self._memory if k.startswith(prefix)]
        for k in to_remove:
            del self._memory[k]
            count += 1
        return count

    def get_stats(self) -> dict[str, int]:
        return dict(self._stats)
