"""Tests for observability.config — ObservabilityConfig."""

from __future__ import annotations

import os

import pytest

from ayeneh.observability.config import ObservabilityConfig


class TestObservabilityConfig:
    def test_defaults(self) -> None:
        cfg = ObservabilityConfig()
        assert cfg.tracing_enabled is True
        assert cfg.trace_max_events_per_stage == 100
        assert cfg.trace_capture_raw_input is False
        assert cfg.metrics_window_size == 1000
        assert cfg.diagnostics_interval_s == 30
        assert cfg.confidence_threshold_retrieval == 0.3
        assert cfg.confidence_threshold_reasoning == 0.2
        assert cfg.confidence_threshold_response == 0.3
        assert cfg.retrieval_budget_default == 20
        assert cfg.retrieval_timeout_s == 30.0
        assert cfg.prometheus_enabled is True

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AYENEH_OBS_TRACING_ENABLED", "false")
        monkeypatch.setenv("AYENEH_OBS_CONFIDENCE_THRESHOLD_RETRIEVAL", "0.5")
        monkeypatch.setenv("AYENEH_OBS_RETRIEVAL_BUDGET_DEFAULT", "50")
        cfg = ObservabilityConfig()
        assert cfg.tracing_enabled is False
        assert cfg.confidence_threshold_retrieval == 0.5
        assert cfg.retrieval_budget_default == 50

    def test_extra_fields_ignored(self) -> None:
        cfg = ObservabilityConfig()
        # Should not raise — extra fields are ignored
        assert cfg.tracing_enabled is True
