from __future__ import annotations

from dataclasses import dataclass

from ..capabilities import Capability, CapabilitySet
from ..types import ProviderType
from . import _LLMAdapter


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "llama3"
    timeout: float = 60
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    num_ctx: int = 4096
    num_threads: int = 0
    num_gpu: int = 0


class OllamaProvider(_LLMAdapter):
    provider_name = "ollama"

    def __init__(self, config: OllamaConfig):
        from ayeneh.llm.providers.openai_provider import OpenAIProvider

        super().__init__(
            OpenAIProvider(
                api_key="ollama", model=config.model, base_url=config.base_url.rstrip("/") + "/v1"
            ),
            provider_type=ProviderType.LOCAL,
        )

    def get_capabilities(self):
        return CapabilitySet(
            frozenset(
                [
                    Capability.STREAMING,
                    Capability.EXTRACTION,
                    Capability.CLASSIFICATION,
                    Capability.SUMMARIZATION,
                    Capability.MULTILINGUAL,
                    Capability.LOW_COST,
                    Capability.LOCAL_ONLY,
                    Capability.OFFLINE,
                    Capability.DETERMINISTIC,
                ]
            )
        )
