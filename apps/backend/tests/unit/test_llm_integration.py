"""Tests for LLM provider registry, configuration, and integration."""

from __future__ import annotations

import asyncio

import pytest

from ayeneh.config import Settings
from ayeneh.llm.gateway import LLMGateway, LLMUsageTracker
from ayeneh.llm.registry import ProviderRegistry, initialize_providers
from ayeneh.llm.types import LLMConfig, LLMMessage, LLMResponse, LLMUsage, ToolCall, ToolDefinition


class FakeGateway(LLMGateway):
    def __init__(self, model: str = "test-model"):
        self._model = model
        self.call_count = 0

    async def chat(self, messages, config=None, *, request_id=None):
        self.call_count += 1
        return LLMResponse(content="test response", model=self._model)

    async def chat_stream(self, messages, config=None, *, request_id=None):
        from ayeneh.llm.types import StreamChunk
        yield StreamChunk(delta="hello")
        yield StreamChunk(delta="", finish_reason="stop")

    async def embed(self, texts, model=""):
        return [[0.1] * 128 for _ in texts]

    def supports_structured_output(self):
        return True

    def supports_tool_calling(self):
        return True

    def get_model_info(self, model=None):
        return {"model": model or self._model, "provider": "fake", "max_tokens": 4096}

    async def cancel(self, request_id):
        return True


# ════════════════════════════════════════════════════════════════════════
# Configuration tests
# ════════════════════════════════════════════════════════════════════════

class TestLLMConfiguration:
    def test_config_defaults(self):
        s = Settings(_env_file=None)
        assert s.llm_default_model == "gpt-4o-mini"
        assert s.llm_openai_api_key == ""
        assert s.llm_anthropic_api_key == ""
        assert s.llm_gemini_api_key == ""
        assert s.llm_litellm_api_key == ""
        assert s.llm_temperature == 0.7
        assert s.llm_max_tokens == 2048

    def test_config_temperature(self):
        s = Settings(_env_file=None)
        assert s.llm_temperature == 0.7
        assert s.llm_max_tokens == 2048
        assert s.llm_timeout_seconds == 30.0
        assert s.llm_max_retries == 3

    def test_config_fallback_models(self):
        s = Settings(_env_file=None)
        assert "gpt-4o-mini" in s.llm_fallback_models


# ════════════════════════════════════════════════════════════════════════
# Provider registry tests
# ════════════════════════════════════════════════════════════════════════

class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        gw = FakeGateway("model-a")
        registry.register("provider-a", gw)
        assert registry.get("provider-a") is gw
        assert registry.get("nonexistent") is None

    def test_get_or_default(self):
        registry = ProviderRegistry()
        gw = FakeGateway("model-a")
        registry.register("openai", gw)
        assert registry.get_or_default("openai") is gw

    def test_get_or_default_fallback(self):
        registry = ProviderRegistry()
        gw = FakeGateway("model-a")
        registry.register("openai", gw)
        registry.set_fallback_chain(["anthropic", "openai"])
        assert registry.get_or_default("anthropic") is gw

    def test_get_or_default_first_available(self):
        registry = ProviderRegistry()
        gw = FakeGateway()
        registry.register("any-provider", gw)
        assert registry.get_or_default("nonexistent") is gw

    def test_get_or_default_no_providers_raises(self):
        with pytest.raises(RuntimeError, match="No LLM provider available"):
            ProviderRegistry().get_or_default()

    def test_list_providers(self):
        registry = ProviderRegistry()
        registry.register("a", FakeGateway())
        registry.register("b", FakeGateway())
        providers = registry.list_providers()
        assert len(providers) == 2

    def test_has_provider(self):
        registry = ProviderRegistry()
        registry.register("test", FakeGateway())
        assert registry.has_provider("test")
        assert not registry.has_provider("missing")

    def test_singleton(self):
        ProviderRegistry.reset()
        r1 = ProviderRegistry.get_instance()
        r2 = ProviderRegistry.get_instance()
        assert r1 is r2
        ProviderRegistry.reset()

    def test_reset_clears_providers(self):
        ProviderRegistry.reset()
        r1 = ProviderRegistry.get_instance()
        r1.register("test", FakeGateway())
        ProviderRegistry.reset()
        r2 = ProviderRegistry.get_instance()
        assert r2.get("test") is None


# ════════════════════════════════════════════════════════════════════════
# Initialize providers tests
# ════════════════════════════════════════════════════════════════════════

class TestInitializeProviders:
    def test_no_providers_configured(self):
        ProviderRegistry.reset()
        settings = Settings(
            _env_file=None,
            llm_openai_api_key="",
            llm_anthropic_api_key="",
            llm_gemini_api_key="",
            llm_litellm_api_key="",
        )
        registry = initialize_providers(settings)
        assert len(registry.list_providers()) == 0

    def test_with_openai_key(self):
        ProviderRegistry.reset()
        settings = Settings(_env_file=None, llm_openai_api_key="test-key")
        registry = initialize_providers(settings)
        assert "openai" in registry.list_providers()

    def test_with_anthropic_key(self):
        ProviderRegistry.reset()
        settings = Settings(_env_file=None, llm_anthropic_api_key="test-key")
        registry = initialize_providers(settings)
        assert "anthropic" in registry.list_providers()

    def test_with_gemini_key(self):
        ProviderRegistry.reset()
        settings = Settings(_env_file=None, llm_gemini_api_key="test-key")
        registry = initialize_providers(settings)
        assert "gemini" in registry.list_providers()


# ════════════════════════════════════════════════════════════════════════
# Gateway type tests
# ════════════════════════════════════════════════════════════════════════

class TestGatewayTypes:
    def test_llm_message_to_dict(self):
        msg = LLMMessage(role="user", content="hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "hello"

    def test_tool_call_parse_arguments(self):
        tc = ToolCall(id="t1", name="fn", arguments='{"x": 1}')
        assert tc.parse_arguments() == {"x": 1}

    def test_tool_call_bad_json(self):
        tc = ToolCall(id="t1", name="fn", arguments="not json")
        assert tc.parse_arguments() == {}

    def test_tool_definition(self):
        td = ToolDefinition(name="fn", description="desc", parameters={"type": "object"})
        d = td.to_dict()
        assert d["type"] == "function"
        assert d["function"]["name"] == "fn"

    def test_llm_usage_add(self):
        u1 = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        u2 = LLMUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30, estimated_cost_usd=0.01)
        u1.add(u2)
        assert u1.total_tokens == 45
        assert u1.estimated_cost_usd == 0.01

    def test_usage_tracker(self):
        tracker = LLMUsageTracker()
        tracker.record(LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150))
        tracker.record(LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300))
        summary = tracker.get_summary()
        assert summary["total_tokens"] == 450
        assert summary["request_count"] == 2


# ════════════════════════════════════════════════════════════════════════
# Agent integration tests
# ════════════════════════════════════════════════════════════════════════

class TestAgentLLMIntegration:
    def test_conversation_agent_accepts_gateway(self):
        from ayeneh.agents.conversation import ConversationAgent
        gw = FakeGateway()
        agent = ConversationAgent(llm=gw)
        assert agent._llm is gw

    def test_reflection_agent_accepts_gateway(self):
        from ayeneh.agents.reflection import ReflectionAgent
        gw = FakeGateway()
        agent = ReflectionAgent(llm=gw)
        assert agent._llm is gw

    def test_blind_spot_agent_accepts_gateway(self):
        from ayeneh.agents.blind_spot import BlindSpotAgent
        gw = FakeGateway()
        agent = BlindSpotAgent(llm=gw)
        assert agent._llm is gw

    def test_agents_work_without_gateway(self):
        from ayeneh.agents.conversation import ConversationAgent
        from ayeneh.agents.reflection import ReflectionAgent
        from ayeneh.agents.blind_spot import BlindSpotAgent

        assert ConversationAgent()._llm is None
        assert ReflectionAgent()._llm is None
        assert BlindSpotAgent()._llm is None


# ════════════════════════════════════════════════════════════════════════
# Concurrent request tests
# ════════════════════════════════════════════════════════════════════════

class TestConcurrentRequests:
    @pytest.mark.asyncio
    async def test_concurrent_gateway_calls(self):
        gw = FakeGateway()

        async def call():
            return await gw.chat([LLMMessage(role="user", content="hi")])

        results = await asyncio.gather(*[call() for _ in range(10)])
        assert all(r.content == "test response" for r in results)
        assert gw.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_registry_operations(self):
        registry = ProviderRegistry()
        for i in range(5):
            registry.register(f"p{i}", FakeGateway())
        assert len(registry.list_providers()) == 5

    @pytest.mark.asyncio
    async def test_concurrent_chat_and_stream(self):
        gw = FakeGateway()
        chat_task = asyncio.create_task(
            gw.chat([LLMMessage(role="user", content="hi")])
        )
        chunks = []
        async for chunk in gw.chat_stream([LLMMessage(role="user", content="hi")]):
            chunks.append(chunk)
        result = await chat_task
        assert result.content == "test response"
        assert len(chunks) >= 1
