"""Integration tests for production hardening infrastructure.

Covers: circuit breaker, retry, rate limiter, cache, audit logging,
observability metrics, health endpoints.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from ayeneh.infrastructure.audit import AuditLogger
from ayeneh.infrastructure.cache import DistributedCache
from ayeneh.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBrokenError,
    CircuitBreakerRegistry,
    CircuitState,
    call_with_circuit_breaker,
)
from ayeneh.infrastructure.observability import PrometheusMetrics
from ayeneh.infrastructure.rate_limiter import RateLimitPresets, RateLimiter
from ayeneh.infrastructure.retry import RetryPolicy, RetryPolicyRegistry, call_with_retry


# ════════════════════════════════════════════════════════════════════════
# Circuit breaker tests
# ════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_after_reset(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_success_in_half_open(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_blocks_when_open(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.is_open()

    def test_reset(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.is_open()
        cb.reset()
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerRegistry:
    def test_get_creates_breaker(self) -> None:
        reg = CircuitBreakerRegistry()
        cb = reg.get("llm", failure_threshold=5)
        assert cb.name == "llm"
        assert cb.failure_threshold == 5

    def test_get_returns_same(self) -> None:
        reg = CircuitBreakerRegistry()
        cb1 = reg.get("llm")
        cb2 = reg.get("llm")
        assert cb1 is cb2

    def test_get_all_states(self) -> None:
        reg = CircuitBreakerRegistry()
        reg.get("llm")
        reg.get("embedding")
        states = reg.get_all_states()
        assert states["llm"] == "closed"
        assert states["embedding"] == "closed"


@pytest.mark.asyncio
async def test_call_with_circuit_breaker_success() -> None:
    cb = CircuitBreaker(name="test")

    async def ok():
        return "result"

    result = await call_with_circuit_breaker(cb, ok)
    assert result == "result"


@pytest.mark.asyncio
async def test_call_with_circuit_breaker_failure() -> None:
    cb = CircuitBreaker(name="test", failure_threshold=2)

    async def fail():
        raise ValueError("boom")

    for _ in range(2):
        with pytest.raises(ValueError):
            await call_with_circuit_breaker(cb, fail)

    assert cb.is_open()

    with pytest.raises(CircuitBrokenError):
        await call_with_circuit_breaker(cb, lambda: None)


# ════════════════════════════════════════════════════════════════════════
# Retry policy tests
# ════════════════════════════════════════════════════════════════════════

class TestRetryPolicy:
    def test_delay_increases(self) -> None:
        policy = RetryPolicy(base_delay_ms=100, backoff_factor=2.0, jitter=False)
        assert policy.get_delay(0) == 100.0
        assert policy.get_delay(1) == 200.0
        assert policy.get_delay(2) == 400.0

    def test_max_delay_cap(self) -> None:
        policy = RetryPolicy(max_delay_ms=500, backoff_factor=10.0, jitter=False)
        assert policy.get_delay(5) == 500.0


@pytest.mark.asyncio
async def test_call_with_retry_success() -> None:
    policy = RetryPolicy(max_retries=2)

    async def ok(msg: str) -> str:
        return msg

    result = await call_with_retry(policy, ok, "hi")
    assert result == "hi"


@pytest.mark.asyncio
async def test_call_with_retry_exhausted() -> None:
    policy = RetryPolicy(max_retries=1, base_delay_ms=1, jitter=False)

    async def fail():
        raise ConnectionError("nope")

    with pytest.raises(ConnectionError):
        await call_with_retry(policy, fail)


# ════════════════════════════════════════════════════════════════════════
# Rate limiter tests
# ════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_under_limit(self) -> None:
        limiter = RateLimiter()
        result = await limiter.check("key1", limit=5, window_seconds=60)
        assert result.allowed is True
        assert result.remaining >= 0

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self) -> None:
        limiter = RateLimiter()
        for _ in range(5):
            await limiter.check("key2", limit=5, window_seconds=60)
        result = await limiter.check("key2", limit=5, window_seconds=60)
        assert result.allowed is False
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self) -> None:
        limiter = RateLimiter()
        for _ in range(5):
            await limiter.check("k1", limit=5, window_seconds=60)
        result = await limiter.check("k2", limit=5, window_seconds=60)
        assert result.allowed is True


# ════════════════════════════════════════════════════════════════════════
# Cache tests
# ════════════════════════════════════════════════════════════════════════

class TestDistributedCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        cache = DistributedCache()
        await cache.set("k", {"data": 1}, ttl=60)
        result = await cache.get("k")
        assert result == {"data": 1}

    @pytest.mark.asyncio
    async def test_miss(self) -> None:
        cache = DistributedCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        cache = DistributedCache()
        await cache.set("k", "v")
        await cache.delete("k")
        assert await cache.get("k") is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self) -> None:
        cache = DistributedCache()
        await cache.set("mem:1", "a")
        await cache.set("mem:2", "b")
        await cache.set("user:1", "c")
        count = await cache.invalidate_pattern("mem:")
        assert count >= 2
        assert await cache.get("mem:1") is None
        assert await cache.get("user:1") == "c"

    def test_stats(self) -> None:
        cache = DistributedCache()
        assert cache.get_stats()["hits"] == 0


# ════════════════════════════════════════════════════════════════════════
# Audit logging tests
# ════════════════════════════════════════════════════════════════════════

class TestAuditLogger:
    def test_log_creates_event(self) -> None:
        audit = AuditLogger()
        event = audit.log(
            event_type="memory_created",
            user_id="u1",
            resource_type="memory",
            resource_id="m1",
            action="create",
        )
        assert event.event_id
        assert event.event_type == "memory_created"

    def test_filter_by_user(self) -> None:
        audit = AuditLogger()
        audit.log(event_type="a", user_id="u1", resource_type="r", resource_id="1", action="x")
        audit.log(event_type="a", user_id="u2", resource_type="r", resource_id="2", action="x")
        events = audit.get_events(user_id="u1")
        assert len(events) == 1

    def test_count(self) -> None:
        audit = AuditLogger()
        audit.log(event_type="a", user_id="u1", resource_type="r", resource_id="1", action="x")
        audit.log(event_type="b", user_id="u1", resource_type="r", resource_id="2", action="x")
        assert audit.get_event_count("a") == 1
        assert audit.get_event_count() == 2


# ════════════════════════════════════════════════════════════════════════
# Prometheus metrics tests
# ════════════════════════════════════════════════════════════════════════

class TestPrometheusMetrics:
    def test_record_request(self) -> None:
        m = PrometheusMetrics()
        m.record_request("GET", "/health", 200, 5.0)
        output = m.export_prometheus_text()
        assert "ayeneh_requests_total" in output

    def test_record_llm_call(self) -> None:
        m = PrometheusMetrics()
        m.record_llm_call("gpt-4o-mini", 100.0)
        assert m.llm_call_count == 1
        assert m.llm_call_duration_ms == 100.0

    def test_record_evolution_operation(self) -> None:
        m = PrometheusMetrics()
        m.record_evolution_operation("merge")
        m.record_evolution_operation("merge")
        assert m.evolution_operations["merge"] == 2

    def test_export_format(self) -> None:
        m = PrometheusMetrics()
        m.record_request("POST", "/api", 201, 10.0)
        m.record_llm_call("gpt-4o", 200.0)
        text = m.export_prometheus_text()
        assert text.startswith("# HELP")
        assert "ayeneh_llm_calls_total 1" in text


# ════════════════════════════════════════════════════════════════════════
# Retry policy registry tests
# ════════════════════════════════════════════════════════════════════════

class TestRetryPolicyRegistry:
    def test_has_llm_policy(self) -> None:
        reg = RetryPolicyRegistry()
        assert reg.llm.max_retries == 3

    def test_has_embedding_policy(self) -> None:
        reg = RetryPolicyRegistry()
        assert reg.embedding.max_retries == 2

    def test_has_database_policy(self) -> None:
        reg = RetryPolicyRegistry()
        assert reg.database.max_retries == 3
