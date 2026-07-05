"""Observability configuration — centralized, versioned, env-driven.

Replaces hard-coded thresholds scattered across pipeline modules.
All fields have sensible defaults and can be overridden via environment
variables with prefix AYENEH_OBS_.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class ObservabilityConfig(BaseSettings):
    """Central configuration for observability layer.

    Environment variable prefix: AYENEH_OBS_
    Example: AYENEH_OBS_TRACING_ENABLED=false
    """

    model_config = {"env_prefix": "AYENEH_OBS_", "extra": "ignore"}

    # -- Tracing --
    tracing_enabled: bool = True
    trace_max_events_per_stage: int = 100
    trace_max_total_events: int = 1000
    trace_capture_raw_input: bool = False  # privacy guard

    # -- Metrics --
    metrics_window_size: int = 1000

    # -- Diagnostics --
    diagnostics_interval_s: int = 30
    diagnostics_version_check: bool = True

    # -- Confidence thresholds (replace hard-coded values in pipeline) --
    confidence_threshold_retrieval: float = 0.3
    confidence_threshold_reasoning: float = 0.2
    confidence_threshold_response: float = 0.3

    # -- Retrieval --
    retrieval_budget_default: int = 20
    retrieval_timeout_s: float = 30.0

    # -- Export --
    prometheus_enabled: bool = True
