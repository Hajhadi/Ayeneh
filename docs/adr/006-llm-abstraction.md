# LLM Abstraction via LiteLLM

## Status

Accepted

## Context

Ayeneh relies on LLMs for conversation, memory extraction, pattern detection, and reflection generation. Hard-coding a single LLM provider (e.g., OpenAI) would create vendor lock-in, prevent users from choosing their preferred provider, and make the project vulnerable to provider-specific API changes, pricing shifts, or outages. The system needs a provider-agnostic interface.

## Decision

Use LiteLLM as the universal LLM gateway. All LLM calls — chat completions, embeddings, and model parameter configuration — go through LiteLLM's unified interface. Providers are configured at deployment time via environment variables or configuration files. No application code references a provider-specific SDK.

The LLMService wraps LiteLLM and provides:
- A uniform call interface for all model types (chat, embedding).
- Model selection routing based on task type (conversation vs. extraction vs. reflection).
- Configurable parameters (temperature, max tokens, etc.) per task.
- Fallback and retry logic across providers.

## Consequences

### Positive
- Zero application code changes when switching or adding providers.
- Users can self-host with local models (Ollama, vLLM) or use commercial APIs.
- LiteLLM handles provider-specific quirks, rate limiting, and error translation.
- Fallback chains (e.g., try OpenAI, fall back to Anthropic) are configurable without code changes.

### Negative
- Dependency on LiteLLM as middleware — its API changes or bugs affect the entire system.
- Provider-specific features (e.g., Anthropic's extended thinking, OpenAI's structured outputs) are only accessible if LiteLLM exposes them.
- Additional network hop if LiteLLM runs as a proxy; can be mitigated by using it as a library.

## Alternatives Considered

- **Direct provider SDK integration**: Rejected — creates tight coupling to each provider; switching providers requires code changes in every consumer.
- **Custom abstraction layer**: Rejected — would reimplement what LiteLLM already provides; maintaining provider compatibility is a significant ongoing effort.
- **Multiple conditional branches per provider**: Rejected — does not scale; each new provider requires changes throughout the codebase.
- **No abstraction (single provider lock-in)**: Rejected — contradicts the project's goals of modularity and user choice.
