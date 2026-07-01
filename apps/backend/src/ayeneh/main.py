"""Ayeneh FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ayeneh.api.deps import set_container
from ayeneh.api.exception_handlers import register_exception_handlers
from ayeneh.api.v1.router import api_router
from ayeneh.config import get_settings
from ayeneh.container import Container
from ayeneh.logging_config import setup_logging
from ayeneh.middleware.request_id import RequestIDMiddleware
from ayeneh.middleware.timing import TimingMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown with graceful handling."""
    setup_logging()
    settings = get_settings()
    logger.info("application_starting", version=settings.app_version)

    container = Container()
    container.initialize()
    set_container(container)
    app.state.container = container

    try:
        await container.startup()
    except Exception as exc:
        logger.exception("startup_failed", error=str(exc))
        raise

    logger.info("application_started")
    yield

    logger.info("application_shutting_down")
    try:
        await container.shutdown()
    except Exception as exc:
        logger.exception("shutdown_error", error=str(exc))
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS — allow frontend to call API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware (order matters: outermost runs first)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Routes
    app.include_router(api_router)

    return app


app = create_app()
