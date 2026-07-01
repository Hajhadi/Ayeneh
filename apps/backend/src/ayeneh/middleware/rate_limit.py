"""Rate limiting middleware for FastAPI."""

from __future__ import annotations

import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ayeneh.infrastructure.rate_limiter import RateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies per-IP rate limiting."""

    def __init__(self, app: Any, rate_limiter: RateLimiter) -> None:
        super().__init__(app)
        self._limiter = rate_limiter
        self._excluded_paths = {"/health", "/ready", "/live", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call: Callable) -> Any:
        path = request.url.path
        if path in self._excluded_paths:
            return await call(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}:{path}"

        result = await self._limiter.check(key, limit=100, window_seconds=60)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after_ms": result.retry_after_ms,
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(result.retry_after_ms // 1000),
                },
            )

        response = await call(request)
        if hasattr(response, "headers"):
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
