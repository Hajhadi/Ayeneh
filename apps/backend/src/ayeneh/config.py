"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    model_config = {"env_prefix": "AYENEH_", "env_file": ".env", "extra": "ignore"}

    app_name: str = "ayeneh"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://ayeneh:ayeneh@localhost:5432/ayeneh"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis (future)
    redis_url: str = "redis://localhost:6379/0"

    # LLM — provider selection
    llm_provider: str = "litellm"
    llm_default_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 3
    llm_fallback_models: str = "gpt-4o-mini,claude-3-5-sonnet-20241022,gemini-1.5-flash"

    # Per-provider API keys (never hardcoded, env-only)
    llm_openai_api_key: str = ""
    llm_openai_base_url: str = ""
    llm_anthropic_api_key: str = ""
    llm_gemini_api_key: str = ""
    llm_litellm_api_key: str = ""
    llm_litellm_api_base: str = ""

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "openai"

    # Runtime
    runtime_global_timeout_seconds: int = 60
    runtime_planner_confidence_threshold: float = 0.8

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "ayeneh-api"

    # Authentication
    auth_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    auth_refresh_secret_key: str = "change-me-refresh-key-use-openssl-rand-hex-32"
    auth_access_token_ttl_minutes: int = 15
    auth_refresh_token_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
