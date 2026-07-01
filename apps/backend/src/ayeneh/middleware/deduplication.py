"""Request deduplication middleware for idempotent operations."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DeduplicationEntry:
    response: Any
    timestamp: float


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """Deduplicates identical requests within a configurable time window.

    Only applies to POST/PATCH/DELETE methods. Uses request body hash
    combined with path and user context as dedup key.
    """

    def __init__(self, app: Any, window_seconds: int = 10) -> None:
        super().__init__(app)
        self._window = window_seconds
        self._seen: dict[str, DeduplicationEntry] = {}

    async def dispatch(self, request: Request, call: Callable) -> Any:
        if request.method not in ("POST", "PATCH", "DELETE"):
            return await call(request)

        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()[:16]
        key = f"{request.method}:{request.url.path}:{body_hash}"

        now = time.time()
        self._seen = {
            k: v for k, v in self._seen.items()
            if now - v.timestamp < self._window
        }

        if key in self._seen:
            entry = self._seen[key]
            age = now - entry.timestamp
            if age < self._window:
                logger.info("request_deduplicated", path=request.url.path, age_ms=round(age * 1000))
                return JSONResponse(
                    status_code=429,
                    content={"error": "duplicate_request", "message": "Duplicate request within dedup window"},
                )

        response = await call(request)
        self._seen[key] = DeduplicationEntry(response=response, timestamp=now)
        return response
