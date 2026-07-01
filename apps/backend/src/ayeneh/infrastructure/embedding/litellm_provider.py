"""LiteLLM embedding provider — concrete implementation using litellm."""

from __future__ import annotations

import structlog

from ayeneh.application.ports.embedding import EmbeddingProvider

logger = structlog.get_logger(__name__)


class LiteLLMEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by LiteLLM."""

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536) -> None:
        self._model = model
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for a single text."""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts via litellm."""
        if not texts:
            return []

        import litellm

        logger.debug("embedding_batch", model=self._model, count=len(texts))

        response = await litellm.aembedding(
            model=self._model,
            input=texts,
        )

        embeddings = [item["embedding"] for item in response.data]

        logger.debug("embedding_batch_complete", model=self._model, count=len(embeddings))
        return embeddings
