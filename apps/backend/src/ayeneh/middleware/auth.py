"""Authentication middleware — attaches user context to requests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ayeneh.auth.tokens import decode_access_token

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response
    pass

logger = structlog.get_logger(__name__)

PUBLIC_PATHS = {"/api/v1/health", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Extracts and validates JWT from Authorization header.

    Does NOT enforce authentication — that is done by route-level dependencies.
    This middleware simply parses the token and attaches it to request.state
    for downstream use.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_access_token(token)
            if payload:
                request.state.user_id = payload.sub
                request.state.user_email = payload.email
                request.state.user_role = payload.role
                request.state.user_jti = payload.jti
                logger.debug("token_verified", user_id=payload.sub)
            else:
                request.state.user_id = None
                logger.debug("token_invalid")
        else:
            request.state.user_id = None

        response = await call_next(request)
        return response
