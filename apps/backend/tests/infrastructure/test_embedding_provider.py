"""Tests for embedding provider abstraction and LiteLLM implementation."""

from __future__ import annotations

import pytest

from ayeneh.application.ports.embedding import EmbeddingProvider
from ayeneh.infrastructure.embedding.litellm_provider import LiteLLMEmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Test double for EmbeddingProvider."""

    def __init__(self, dimensions: int = 4) -> None:
        self._model = "mock-model"
        self._dimensions = dimensions
        self.call_count = 0

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        self.call_count += 1
        return [0.1 * (i + 1) for i in range(self._dimensions)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [[0.1 * (i + 1) for i in range(self._dimensions)] for _ in texts]


class TestEmbeddingProviderContract:
    """Test the EmbeddingProvider abstract contract via mock."""

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimensions(self) -> None:
        provider = MockEmbeddingProvider(dimensions=4)
        result = await provider.embed("hello world")
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_embed_batch_returns_list(self) -> None:
        provider = MockEmbeddingProvider(dimensions=4)
        results = await provider.embed_batch(["hello", "world"])
        assert len(results) == 2
        assert all(len(r) == 4 for r in results)

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self) -> None:
        provider = MockEmbeddingProvider()
        results = await provider.embed_batch([])
        assert results == []

    def test_model_name(self) -> None:
        provider = MockEmbeddingProvider()
        assert provider.model_name == "mock-model"

    def test_dimensions(self) -> None:
        provider = MockEmbeddingProvider(dimensions=8)
        assert provider.dimensions == 8


class TestLiteLLMProvider:
    """Test LiteLLMEmbeddingProvider initialization."""

    def test_default_model(self) -> None:
        provider = LiteLLMEmbeddingProvider()
        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimensions == 1536

    def test_custom_model(self) -> None:
        provider = LiteLLMEmbeddingProvider(model="text-embedding-3-large", dimensions=3072)
        assert provider.model_name == "text-embedding-3-large"
        assert provider.dimensions == 3072
