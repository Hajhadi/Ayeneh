"""Structured, low-overhead logging for pipeline execution events."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger("ayeneh.pipeline")


class PipelineLogger:
    """Emit pipeline telemetry without coupling runtime code to storage.

    The logger deliberately keeps event payloads bounded and structured. A
    log collector can persist them, while local development remains useful
    without creating a second database or file lifecycle.
    """

    @staticmethod
    def log_event(
        *,
        request_id: str,
        stage: str,
        status: str,
        confidence: float = 0.0,
        duration_ms: float = 0.0,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "pipeline_stage",
            request_id=request_id,
            stage=stage,
            status=status,
            confidence=round(float(confidence), 4),
            duration_ms=round(float(duration_ms), 2),
            error=error[:500] if error else None,
            details=details or {},
        )

    @staticmethod
    def log_complete(
        *,
        request_id: str,
        total_duration_ms: float,
        stages_count: int,
        errors: list[str] | None = None,
    ) -> None:
        logger.info(
            "pipeline_complete",
            request_id=request_id,
            total_duration_ms=round(float(total_duration_ms), 2),
            stages_count=int(stages_count),
            errors=(errors or [])[:10],
        )
