"""Tests for AI Router retry logic."""

from __future__ import annotations

import asyncio

import pytest

from ayeneh.ai_router import AIRouter, AITask, AITaskType
from ayeneh.ai_router.capabilities import Capability, CapabilitySet
from ayeneh.ai_router.providers import AIProvider
from ayeneh.ai_router.registry import ProviderRegistry
from ayeneh.ai_router.retry import RetryManager
from ayeneh.ai_router.types import ProviderType


# ---------------------------------------------------------------------------
# RetryManager Unit Tests
# ---------------------------------------------------------------------------


class TestRetryManagerDelay:
    """Test delay calculation."""

    def test_delay_is_within_bounds(self):
        rm = RetryManager(max_retries=5, base_delay_ms=1000, max_delay_ms=10000)
        for attempt in range(10):
            delay = rm.get_delay(attempt)
            assert 0 <= delay <= 10.0  # max_delay_ms / 1000

    def test_delay_base_case(self):
        rm = RetryManager(base_delay_ms=1000, exponential_base=2, max_delay_ms=100000)
        # With full jitter, delay should be between 0 and base_delay_ms for attempt=0
        delays = [rm.get_delay(0) for _ in range(100)]
        assert all(0 <= d <= 1.0 for d in delays)  # 1000ms = 1s

    def test_delay_exponential_growth(self):
        rm = RetryManager(base_delay_ms=1000, exponential_base=2, max_delay_ms=100000)
        # The upper bound should grow exponentially
        # attempt=0: max 1000ms, attempt=1: max 2000ms, attempt=2: max 4000ms
        for attempt in range(5):
            upper_bound = min(1000 * (2 ** attempt), 100000) / 1000
            delays = [rm.get_delay(attempt) for _ in range(200)]
            assert max(delays) <= upper_bound + 0.01  # small float tolerance

    def test_delay_capped_at_max(self):
        rm = RetryManager(base_delay_ms=1000, exponential_base=2, max_delay_ms=5000)
        # attempt=10 would be 1000 * 2^10 = 1024000, but capped at 5000ms
        delays = [rm.get_delay(10) for _ in range(200)]
        assert all(d <= 5.0 for d in delays)


class TestRetryManagerRetryable:
    """Test retryable error detection."""

    def test_timeout_is_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(TimeoutError("connection timed out")) is True
        assert rm.is_retryable(Exception("request timeout")) is True

    def test_connection_is_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(ConnectionError("connection refused")) is True
        assert rm.is_retryable(ConnectionError("econnreset")) is True

    def test_rate_limit_is_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(Exception("rate limit exceeded")) is True
        assert rm.is_retryable(Exception("429 too many requests")) is True

    def test_server_error_is_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(Exception("503 service unavailable")) is True
        assert rm.is_retryable(Exception("502 bad gateway")) is True

    def test_auth_error_not_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(Exception("authentication failed")) is False
        assert rm.is_retryable(Exception("unauthorized access")) is False
        assert rm.is_retryable(Exception("401 invalid api key")) is False
        assert rm.is_retryable(Exception("403 forbidden")) is False

    def test_quota_error_not_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(Exception("quota exceeded")) is False
        assert rm.is_retryable(Exception("insufficient credits")) is False
        assert rm.is_retryable(Exception("billing error")) is False

    def test_generic_error_not_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(ValueError("bad input")) is False
        assert rm.is_retryable(RuntimeError("something went wrong")) is False

    def test_network_error_type_retryable(self):
        rm = RetryManager()
        assert rm.is_retryable(ConnectionResetError("reset")) is True


class TestRetryManagerShouldRetry:
    """Test should_retry logic."""

    def test_should_retry_within_limit(self):
        rm = RetryManager(max_retries=3)
        assert rm.should_retry(0, TimeoutError("timeout")) is True
        assert rm.should_retry(1, TimeoutError("timeout")) is True
        assert rm.should_retry(2, TimeoutError("timeout")) is True

    def test_should_not_retry_at_limit(self):
        rm = RetryManager(max_retries=3)
        assert rm.should_retry(3, TimeoutError("timeout")) is False

    def test_should_not_retry_non_retryable(self):
        rm = RetryManager(max_retries=3)
        assert rm.should_retry(0, Exception("auth failed")) is False

    def test_should_not_retry_quota(self):
        rm = RetryManager(max_retries=3)
        assert rm.should_retry(0, Exception("quota exceeded")) is False


class TestRetryManagerExecute:
    """Test execute_with_retry."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        rm = RetryManager(max_retries=3)
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await rm.execute_with_retry(succeed)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_then_succeeds(self):
        rm = RetryManager(max_retries=3, base_delay_ms=1)
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("timeout")
            return "ok"

        result = await rm.execute_with_retry(fail_twice)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        rm = RetryManager(max_retries=2, base_delay_ms=1)
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("timeout")

        with pytest.raises(TimeoutError):
            await rm.execute_with_retry(always_fail)
        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable(self):
        rm = RetryManager(max_retries=3, base_delay_ms=1)
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("authentication failed")

        with pytest.raises(Exception, match="authentication"):
            await rm.execute_with_retry(auth_fail)
        assert call_count == 1  # no retries


# ---------------------------------------------------------------------------
# Router Integration Tests
# ---------------------------------------------------------------------------


class RetryableProvider(AIProvider):
    """Provider that fails on first call then succeeds."""

    provider_name = "retryable"
    provider_type = ProviderType.LOCAL

    def __init__(self, fail_count: int = 1):
        self._fail_count = fail_count
        self._call_count = 0

    def get_capabilities(self):
        return CapabilitySet(capabilities=frozenset([
            Capability.EXTRACTION,
            Capability.LOCAL_ONLY,
            Capability.STREAMING,
        ]))

    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise TimeoutError("connection timed out")
        return {"choices": [{"message": {"content": "retryable response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

    async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        self._call_count += 1
        if self._call_count <= self._fail_count:
            raise TimeoutError("connection timed out")
        yield {"choices": [{"delta": {"content": "retry "}}]}
        yield {"choices": [{"delta": {"content": "stream"}}]}

    async def health_check(self):
        return True

    def estimate_cost(self, prompt_tokens, completion_tokens):
        return 0.0


class AlwaysFailProvider(AIProvider):
    """Provider that always fails with non-retryable error."""

    provider_name = "always_fail"
    provider_type = ProviderType.LOCAL

    def get_capabilities(self):
        return CapabilitySet(capabilities=frozenset([
            Capability.EXTRACTION,
            Capability.LOCAL_ONLY,
        ]))

    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        raise Exception("authentication failed")

    async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        raise Exception("authentication failed")

    async def health_check(self):
        return True

    def estimate_cost(self, prompt_tokens, completion_tokens):
        return 0.0


@pytest.mark.asyncio
async def test_router_retry_then_succeed():
    """Router should retry the primary provider and succeed."""
    rm = RetryManager(max_retries=3, base_delay_ms=1)
    provider = RetryableProvider(fail_count=2)

    registry = ProviderRegistry()
    registry.register("retryable", provider)
    router = AIRouter(registry=registry, retry_manager=rm)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    result = await router.chat(task, messages)

    assert result["choices"][0]["message"]["content"] == "retryable response"
    assert provider._call_count == 3  # 2 failures + 1 success


@pytest.mark.asyncio
async def test_router_retry_exhausted_then_fallback():
    """Router should retry primary, then fallback to another provider."""
    rm = RetryManager(max_retries=1, base_delay_ms=1)
    failing = RetryableProvider(fail_count=10)  # always fails

    registry = ProviderRegistry()
    registry.register("failing", failing)
    registry.register("backup", _make_backup_provider())
    router = AIRouter(registry=registry, retry_manager=rm)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    result = await router.chat(task, messages)

    assert result["choices"][0]["message"]["content"] == "backup response"


@pytest.mark.asyncio
async def test_router_chat_stream_fallback():
    """chat_stream should fallback on error."""
    registry = ProviderRegistry()
    registry.register("failing", _make_failing_stream_provider())
    registry.register("backup", _make_backup_stream_provider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]

    chunks = []
    async for chunk in router.chat_stream(task, messages):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0]["choices"][0]["delta"]["content"] == "backup "
    assert chunks[1]["choices"][0]["delta"]["content"] == "streaming"


@pytest.mark.asyncio
async def test_router_chat_stream_all_fail():
    """chat_stream should yield error when all providers fail."""
    registry = ProviderRegistry()
    registry.register("failing", _make_failing_stream_provider())
    registry.register("also_failing", _make_failing_stream_provider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]

    chunks = []
    async for chunk in router.chat_stream(task, messages):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "Error:" in chunks[0]["choices"][0]["delta"]["content"]


@pytest.mark.asyncio
async def test_router_no_retry_manager_still_works():
    """Router without retry manager should work as before."""
    registry = ProviderRegistry()
    registry.register("test_provider", _make_backup_provider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    result = await router.chat(task, messages)

    assert result["choices"][0]["message"]["content"] == "backup response"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_backup_provider():
    class BackupProvider(AIProvider):
        provider_name = "backup"
        provider_type = ProviderType.LOCAL

        def get_capabilities(self):
            return CapabilitySet(capabilities=frozenset([
                Capability.EXTRACTION,
                Capability.LOCAL_ONLY,
                Capability.STREAMING,
            ]))

        async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            return {"choices": [{"message": {"content": "backup response"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            yield {"choices": [{"delta": {"content": "backup "}}]}
            yield {"choices": [{"delta": {"content": "streaming"}}]}

        async def health_check(self):
            return True

        def estimate_cost(self, prompt_tokens, completion_tokens):
            return 0.0

    return BackupProvider()


def _make_failing_stream_provider():
    class FailingStreamProvider(AIProvider):
        provider_name = "failing_stream"
        provider_type = ProviderType.LOCAL

        def get_capabilities(self):
            return CapabilitySet(capabilities=frozenset([
                Capability.EXTRACTION,
                Capability.LOCAL_ONLY,
                Capability.STREAMING,
            ]))

        async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            raise RuntimeError("chat failed")

        async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            raise RuntimeError("stream failed")

        async def health_check(self):
            return True

        def estimate_cost(self, prompt_tokens, completion_tokens):
            return 0.0

    return FailingStreamProvider()


def _make_backup_stream_provider():
    class BackupStreamProvider(AIProvider):
        provider_name = "backup_stream"
        provider_type = ProviderType.LOCAL

        def get_capabilities(self):
            return CapabilitySet(capabilities=frozenset([
                Capability.EXTRACTION,
                Capability.LOCAL_ONLY,
                Capability.STREAMING,
            ]))

        async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            return {"choices": [{"message": {"content": "backup"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
            yield {"choices": [{"delta": {"content": "backup "}}]}
            yield {"choices": [{"delta": {"content": "streaming"}}]}

        async def health_check(self):
            return True

        def estimate_cost(self, prompt_tokens, completion_tokens):
            return 0.0

    return BackupStreamProvider()
