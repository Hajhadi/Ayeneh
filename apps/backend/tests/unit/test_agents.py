"""Tests for agent base contract and implementations."""

from __future__ import annotations

import pytest

from ayeneh.agents.blind_spot import BlindSpotAgent
from ayeneh.agents.conversation import ConversationAgent
from ayeneh.agents.library import LibraryAgent
from ayeneh.agents.memory import MemoryAgent
from ayeneh.agents.pattern import PatternAgent
from ayeneh.agents.reflection import ReflectionAgent


@pytest.mark.asyncio
async def test_conversation_agent_execute() -> None:
    agent = ConversationAgent()
    output = await agent.execute({"messages": []})
    assert output.status == "failed"
    assert "response_text" in output.data


@pytest.mark.asyncio
async def test_memory_agent_execute() -> None:
    agent = MemoryAgent()
    output = await agent.execute({"user_id": str(__import__("uuid").uuid4()), "user_message": "hello"})
    assert output.status == "success"
    assert "new_memories" in output.data


@pytest.mark.asyncio
async def test_library_agent_execute() -> None:
    agent = LibraryAgent()
    output = await agent.execute({})
    assert output.status == "success"
    assert "book_chunks" in output.data


@pytest.mark.asyncio
async def test_pattern_agent_execute() -> None:
    agent = PatternAgent()
    output = await agent.execute({"user_id": str(__import__("uuid").uuid4())})
    assert output.status == "success"
    assert "new_patterns" in output.data


@pytest.mark.asyncio
async def test_reflection_agent_execute() -> None:
    agent = ReflectionAgent()
    output = await agent.execute({"user_id": str(__import__("uuid").uuid4()), "semantic_memories": []})
    assert output.status == "success"
    assert "reflection" in output.data


@pytest.mark.asyncio
async def test_blind_spot_agent_execute() -> None:
    agent = BlindSpotAgent()
    output = await agent.execute({"user_id": str(__import__("uuid").uuid4()), "semantic_memories": []})
    assert output.status == "success"
    assert "blind_spots" in output.data
