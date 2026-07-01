"""Comprehensive tests for the ConversationAgent."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from ayeneh.agents.conversation import (
    ConversationAgent,
    LLMGateway,
    PromptBuilder,
    UsageMetrics,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeLLMGateway(LLMGateway):
    def __init__(
        self,
        response: str = '{"response": "Hello! How can I help you?"}',
        usage: dict[str, int] | None = None,
        fail_after: int = 0,
    ) -> None:
        self._response = response
        self._usage = usage or {"prompt_tokens": 100, "completion_tokens": 50}
        self._call_count = 0
        self._fail_after = fail_after
        self.calls: list[dict[str, Any]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        self._call_count += 1
        self.calls.append({"messages": messages, **kwargs})
        if self._fail_after and self._call_count <= self._fail_after:
            raise ConnectionError("LLM unavailable")
        return {"choices": [{"message": {"content": self._response}}], "usage": self._usage}


class FakePromptBuilder(PromptBuilder):
    def __init__(self, messages: list[dict[str, str]] | None = None) -> None:
        self._messages = messages or [
            {"role": "system", "content": "You are Ayeneh."},
            {"role": "user", "content": "Hello"},
        ]

    async def build(self, task_type: str, **kwargs: Any) -> dict[str, Any]:
        return {"messages": self._messages, "system_prompt": self._messages[0]["content"]}


class StreamingLLMGateway(LLMGateway):
    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        return {"choices": [{"message": {"content": "streamed response"}}], "usage": {}}

    async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        for chunk in ["Hello", " ", "world", "!"]:
            yield {"choices": [{"delta": {"content": chunk}}]}


@pytest.fixture
def fake_llm() -> FakeLLMGateway:
    return FakeLLMGateway()


@pytest.fixture
def fake_prompt() -> FakePromptBuilder:
    return FakePromptBuilder()


@pytest.fixture
def agent(fake_llm: FakeLLMGateway, fake_prompt: FakePromptBuilder) -> ConversationAgent:
    return ConversationAgent(llm=fake_llm, prompt_builder=fake_prompt)


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------

class TestBasicExecution:
    @pytest.mark.asyncio
    async def test_returns_success(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_response_text_populated(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.data["response_text"] == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_metadata_populated(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert "model" in output.metadata
        assert "latency_ms" in output.metadata
        assert "total_tokens" in output.metadata

    @pytest.mark.asyncio
    async def test_events_emitted(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert len(output.events) == 1
        assert output.events[0]["event_type"] == "ConversationResponseGenerated"


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

class TestPromptBuilding:
    @pytest.mark.asyncio
    async def test_uses_prompt_builder(self, agent: ConversationAgent, fake_prompt: FakePromptBuilder) -> None:
        await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert len(fake_prompt._messages) > 0

    @pytest.mark.asyncio
    async def test_fallback_without_prompt_builder(self) -> None:
        agent = ConversationAgent(llm=FakeLLMGateway(), prompt_builder=None)
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_conversation_history_formatted(self, fake_llm: FakeLLMGateway) -> None:
        builder = FakePromptBuilder()
        agent = ConversationAgent(llm=fake_llm, prompt_builder=builder)
        await agent.execute({
            "user_id": "u1",
            "user_message": "hello",
            "conversation_history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        })
        messages = fake_llm.calls[0]["messages"]
        assert len(messages) >= 2


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

class TestOutputParsing:
    @pytest.mark.asyncio
    async def test_json_response_parsed(self) -> None:
        llm = FakeLLMGateway(response=json.dumps({
            "response": "I understand your point.",
            "tone": "empathetic",
            "confidence": 0.8,
            "observations": [{"type": "insight", "content": "User is reflective"}],
        }))
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "I feel uncertain"})
        assert output.data["response_text"] == "I understand your point."
        assert output.metadata["tone"] == "empathetic"
        assert output.metadata["confidence"] == 0.8
        assert len(output.data["observations"]) >= 1
        assert any(o.get("type") == "insight" for o in output.data["observations"])

    @pytest.mark.asyncio
    async def test_plain_text_response(self) -> None:
        llm = FakeLLMGateway(response="Just a plain text response.")
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.data["response_text"] == "Just a plain text response."
        assert output.metadata["tone"] == "neutral"

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        llm = FakeLLMGateway(response="")
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "failed"


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

class TestOutputValidation:
    @pytest.mark.asyncio
    async def test_long_response_truncated(self) -> None:
        llm = FakeLLMGateway(response="x" * 15000)
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert len(output.data["response_text"]) <= 10000

    @pytest.mark.asyncio
    async def test_invalid_tone_normalized(self) -> None:
        llm = FakeLLMGateway(response=json.dumps({"response": "ok", "tone": "invalid_tone"}))
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["tone"] == "neutral"

    @pytest.mark.asyncio
    async def test_confidence_clamped(self) -> None:
        llm = FakeLLMGateway(response=json.dumps({"response": "ok", "confidence": 5.0}))
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_invalid_observations_filtered(self) -> None:
        llm = FakeLLMGateway(response=json.dumps({"response": "ok", "observations": ["bad", {"valid": True}]}))
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert all(isinstance(o, dict) for o in output.data["observations"])


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_failure(self) -> None:
        llm = FakeLLMGateway(response="ok after retry", fail_after=1)
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder(), max_retries=2)
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "success"
        assert output.metadata["retries"] == 1

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self) -> None:
        llm = FakeLLMGateway(fail_after=5)
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder(), max_retries=2)
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_no_llm_returns_failed(self) -> None:
        agent = ConversationAgent(llm=None, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.status == "failed"


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self) -> None:
        llm = StreamingLLMGateway()
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        chunks = []
        async for chunk in agent.stream({"user_id": "u1", "user_message": "hello"}):
            chunks.append(chunk)
        assert chunks == ["Hello", " ", "world", "!"]

    @pytest.mark.asyncio
    async def test_stream_error_handled(self) -> None:
        class FailingStreamLLM(LLMGateway):
            async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
                return {}

            async def chat_stream(self, messages: list[dict[str, str]], **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
                raise ConnectionError("stream failed")
                if False:
                    yield {}

        agent = ConversationAgent(llm=FailingStreamLLM(), prompt_builder=FakePromptBuilder())
        chunks = []
        async for chunk in agent.stream({"user_id": "u1", "user_message": "hello"}):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert "Error" in chunks[0]


# ---------------------------------------------------------------------------
# Usage metrics
# ---------------------------------------------------------------------------

class TestUsageMetrics:
    @pytest.mark.asyncio
    async def test_token_counts(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["prompt_tokens"] == 100
        assert output.metadata["completion_tokens"] == 50
        assert output.metadata["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_latency_tracked(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_cost_estimated(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["cost_usd"] >= 0

    @pytest.mark.asyncio
    async def test_retry_count_tracked(self) -> None:
        llm = FakeLLMGateway(response="ok", fail_after=1)
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder(), max_retries=1)
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert output.metadata["retries"] == 1


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class TestObservations:
    @pytest.mark.asyncio
    async def test_emotional_expression_detected(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "I feel anxious about the future"})
        obs_types = [o.get("type") for o in output.data["observations"]]
        assert "emotional_expression" in obs_types

    @pytest.mark.asyncio
    async def test_no_emotional_observation_for_neutral(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "What time is it?"})
        obs_types = [o.get("type") for o in output.data["observations"]]
        assert "emotional_expression" not in obs_types

    @pytest.mark.asyncio
    async def test_observations_from_llm(self) -> None:
        llm = FakeLLMGateway(response=json.dumps({
            "response": "ok",
            "observations": [{"type": "belief", "content": "User believes in growth"}],
        }))
        agent = ConversationAgent(llm=llm, prompt_builder=FakePromptBuilder())
        output = await agent.execute({"user_id": "u1", "user_message": "I believe in personal growth"})
        assert any(o.get("type") == "belief" for o in output.data["observations"])


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_message(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": ""})
        assert output.status in ("success", "failed")

    @pytest.mark.asyncio
    async def test_no_metadata(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "hello"})
        assert "model" in output.metadata

    @pytest.mark.asyncio
    async def test_unicode_message(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "مرحبا كيف حالك"})
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_very_long_message(self, agent: ConversationAgent) -> None:
        output = await agent.execute({"user_id": "u1", "user_message": "x" * 50000})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# UsageMetrics
# ---------------------------------------------------------------------------

class TestUsageMetricsDataclass:
    def test_defaults(self) -> None:
        m = UsageMetrics()
        assert m.prompt_tokens == 0
        assert m.latency_ms == 0.0
        assert m.retries == 0
