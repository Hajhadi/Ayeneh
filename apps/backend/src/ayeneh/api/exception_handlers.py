"""Global exception handlers mapping errors to HTTP responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Base application error."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(code="RESOURCE_NOT_FOUND", message=message, status_code=404)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=400)


class PlanningError(AppError):
    def __init__(self, message: str = "Could not produce execution plan") -> None:
        super().__init__(code="PLANNING_FAILED", message=message, status_code=422)


class AgentError(AppError):
    def __init__(self, message: str = "Agent execution failed") -> None:
        super().__init__(code="AGENT_FAILED", message=message, status_code=422)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "error": {"code": exc.code, "message": exc.message, "details": []},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": [],
                },
            },
        )
