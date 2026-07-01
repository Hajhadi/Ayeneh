"""Tests for configuration loading."""

from __future__ import annotations

from ayeneh.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "ayeneh"
    assert settings.app_version == "0.1.0"
    assert settings.debug is False
