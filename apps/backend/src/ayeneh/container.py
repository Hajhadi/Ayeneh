"""Dependency injection container using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

from ayeneh.config import Settings, get_settings
import structlog

if TYPE_CHECKING:
    from ayeneh.agents.blind_spot import BlindSpotAgent
    from ayeneh.agents.conversation import ConversationAgent
    from ayeneh.agents.library import LibraryAgent
    from ayeneh.agents.memory import MemoryAgent
    from ayeneh.agents.pattern import PatternAgent
    from ayeneh.agents.reflection import ReflectionAgent
    from ayeneh.application.ports.event_bus import EventBus
    from ayeneh.infrastructure.persistence.database import Database
    from ayeneh.prompts.prompt_service import PromptService
    from ayeneh.runtime.executor import ExecutionExecutor
    from ayeneh.runtime.planner import ExecutionPlanner


logger = structlog.get_logger(__name__)


class ProviderGatewayAdapter:
    """Adapts OpenAIProvider (LLMConfig interface) to LLMGateway (dict interface).

    ConversationAgent expects: chat(messages, model=, temperature=, max_tokens=)
    OpenAIProvider expects: chat(messages, config=LLMConfig)
    """

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict[str, Any]:
        from ayeneh.llm.types import LLMConfig, LLMMessage

        llm_messages = [LLMMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]
        config = LLMConfig(
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = await self._provider.chat(llm_messages, config=config)

        return {
            "choices": [
                {
                    "message": {"content": result.content},
                    "finish_reason": result.finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
            },
        }

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[dict[str, Any]]:
        from ayeneh.llm.types import LLMConfig, LLMMessage

        llm_messages = [LLMMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]
        config = LLMConfig(
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async for chunk in self._provider.chat_stream(llm_messages, config=config):
            if chunk.delta:
                yield {"choices": [{"delta": {"content": chunk.delta}}]}
            if chunk.finish_reason:
                yield {"choices": [{"delta": {}, "finish_reason": chunk.finish_reason}]}

logger = structlog.get_logger(__name__)


@dataclass
class Container:
    """Central dependency container. All collaborators are wired here."""

    settings: Settings = field(init=False)

    # Infrastructure
    database: Database | None = field(default=None, init=False)
    event_bus: EventBus | None = field(default=None, init=False)
    redis: Any = field(default=None, init=False)

    # Production infrastructure
    cache: Any = field(default=None, init=False)
    rate_limiter: Any = field(default=None, init=False)
    circuit_breakers: Any = field(default=None, init=False)
    retry_policies: Any = field(default=None, init=False)
    audit_logger: Any = field(default=None, init=False)
    metrics: Any = field(default=None, init=False)
    tracing_tracer: Any = field(default=None, init=False)

    # Prompt framework
    prompt_service: PromptService | None = field(default=None, init=False)

    # LLM
    llm_gateway: Any = field(default=None, init=False)
    provider_registry: Any = field(default=None, init=False)

    # Product profiles
    product_registry: Any = field(default=None, init=False)
    product_metrics: Any = field(default=None, init=False)

    # Runtime
    planner: ExecutionPlanner | None = field(default=None, init=False)
    executor: ExecutionExecutor | None = field(default=None, init=False)

    # Agents
    conversation_agent: ConversationAgent | None = field(default=None, init=False)
    memory_agent: MemoryAgent | None = field(default=None, init=False)
    library_agent: LibraryAgent | None = field(default=None, init=False)
    pattern_agent: PatternAgent | None = field(default=None, init=False)
    reflection_agent: ReflectionAgent | None = field(default=None, init=False)
    blind_spot_agent: BlindSpotAgent | None = field(default=None, init=False)

    # Goal engine
    goal_service: Any = field(default=None, init=False)
    goal_evolution: Any = field(default=None, init=False)
    goal_retrieval: Any = field(default=None, init=False)
    goal_context_builder: Any = field(default=None, init=False)
    goal_metrics: Any = field(default=None, init=False)
    goal_events: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.settings = get_settings()

    def initialize(self) -> None:
        """Wire all dependencies. Called once at application startup."""
        from ayeneh.agents.blind_spot import BlindSpotAgent
        from ayeneh.agents.conversation import ConversationAgent
        from ayeneh.agents.library import LibraryAgent
        from ayeneh.agents.memory import MemoryAgent
        from ayeneh.agents.pattern import PatternAgent
        from ayeneh.agents.reflection import ReflectionAgent
        from ayeneh.infrastructure.audit import AuditLogger
        from ayeneh.infrastructure.cache import DistributedCache
        from ayeneh.infrastructure.circuit_breaker import CircuitBreakerRegistry
        from ayeneh.infrastructure.observability import PrometheusMetrics
        from ayeneh.infrastructure.persistence.database import Database
        from ayeneh.infrastructure.rate_limiter import RateLimiter
        from ayeneh.infrastructure.repositories.event_bus import InMemoryEventBus
        from ayeneh.infrastructure.retry import RetryPolicyRegistry
        from ayeneh.prompts.prompt_service import PromptService
        from ayeneh.runtime.executor import ExecutionExecutor
        from ayeneh.runtime.failure import FailureManager
        from ayeneh.runtime.planner import ExecutionPlanner, LLMPlanner, RulePlanner

        self.database = Database(self.settings.database_url)
        self.event_bus = InMemoryEventBus()

        # Production infrastructure
        self.cache = DistributedCache(default_ttl=300)
        self.rate_limiter = RateLimiter()
        self.circuit_breakers = CircuitBreakerRegistry()
        self.retry_policies = RetryPolicyRegistry()
        self.audit_logger = AuditLogger()
        self.metrics = PrometheusMetrics()

        # Observability layer
        from ayeneh.observability.config import ObservabilityConfig
        from ayeneh.observability.diagnostics import DiagnosticsCollector
        self.observability_config = ObservabilityConfig()
        self.diagnostics = DiagnosticsCollector()

        # LLM providers
        from ayeneh.llm.registry import initialize_providers
        self.provider_registry = initialize_providers(self.settings)
        try:
            self.llm_gateway = self.provider_registry.get_or_default()
        except RuntimeError:
            self.llm_gateway = None
            logger.warning("no_llm_provider_available")

        # AI Router — single entry point for all AI requests
        from ayeneh.ai_router import AIRouter
        from ayeneh.ai_router.providers import OpenAIProvider, AnthropicProvider, LMStudioProvider
        from ayeneh.ai_router.providers.ollama import OllamaProvider, OllamaConfig
        from ayeneh.ai_router.registry import ProviderRegistry as AIProviderRegistry
        from ayeneh.ai_router.policies import PolicyEngine

        self.ai_provider_registry = AIProviderRegistry()

        # Register cloud providers
        if self.settings.llm_openai_api_key:
            base_url = self.settings.llm_openai_base_url or "https://api.openai.com/v1"
            self.ai_provider_registry.register("openai", OpenAIProvider(
                api_key=self.settings.llm_openai_api_key,
                model=self.settings.llm_default_model,
                base_url=base_url,
            ))

        # Register local providers (Ollama) with production config
        if self.settings.local_enabled:
            ollama_config = OllamaConfig(
                base_url=self.settings.local_ollama_url,
                model=self.settings.local_model_name,
                timeout=self.settings.local_timeout,
                max_tokens=self.settings.local_max_tokens,
                temperature=self.settings.local_temperature,
                top_p=self.settings.local_top_p,
                top_k=self.settings.local_top_k,
                num_ctx=self.settings.local_num_ctx,
                num_threads=self.settings.local_num_threads,
                num_gpu=self.settings.local_num_gpu,
            )
            ollama_provider = OllamaProvider(config=ollama_config)

            # Register provider (health check will run at startup)
            self.ai_provider_registry.register("ollama", ollama_provider)
            logger.info("ollama_provider_registered", model=ollama_config.model)

        self.ai_provider_registry.set_fallback_chain(["ollama", "openai"])
        self.ai_router = AIRouter(registry=self.ai_provider_registry, policy_engine=PolicyEngine())

        self.prompt_service = PromptService()

        # Product profiles
        from ayeneh.product.registry import load_default_profiles
        from ayeneh.product.observability import ProductMetrics
        self.product_registry = load_default_profiles()
        self.product_metrics = ProductMetrics()

        # Application services
        uow_factory = self._make_uow_factory()

        from ayeneh.application.services.library import LibraryService
        self.library_service = LibraryService(uow_factory=uow_factory) if uow_factory else None

        from ayeneh.application.services.pattern import PatternService
        self.pattern_service = PatternService(uow_factory=uow_factory) if uow_factory else None

        from ayeneh.application.services.reflection import ReflectionService
        self.reflection_service = ReflectionService(uow_factory=uow_factory) if uow_factory else None

        from ayeneh.application.services.memory import MemoryService
        self.memory_service = MemoryService(uow_factory=uow_factory) if uow_factory else None

        # Goal engine
        from ayeneh.goal.service import GoalService
        from ayeneh.goal.evolution import GoalEvolutionService
        from ayeneh.goal.retrieval import GoalRetrievalService
        from ayeneh.goal.context import GoalContextBuilder
        self.goal_service = GoalService(uow_factory=self._make_uow_factory())
        self.goal_evolution = GoalEvolutionService(self.goal_service)
        self.goal_retrieval = GoalRetrievalService(self.goal_service)
        self.goal_context_builder = GoalContextBuilder(self.goal_retrieval, self.goal_service)

        from ayeneh.goal.observability import GoalMetrics, GoalEventPublisher
        self.goal_metrics = GoalMetrics()
        self.goal_events = GoalEventPublisher(self.event_bus)

        # Wrap provider with adapter to match ConversationAgent's LLMGateway interface
        adapted_llm = ProviderGatewayAdapter(self.llm_gateway) if self.llm_gateway else None

        self.conversation_agent = ConversationAgent(llm=adapted_llm, ai_router=self.ai_router)
        self.memory_agent = MemoryAgent()
        self.library_agent = LibraryAgent()
        self.pattern_agent = PatternAgent()
        self.reflection_agent = ReflectionAgent(llm=adapted_llm)
        self.blind_spot_agent = BlindSpotAgent(llm=adapted_llm)

        agent_names = {
            "conversation", "memory", "library",
            "pattern", "reflection", "blind_spot",
        }

        self.planner = ExecutionPlanner(
            rule_planner=RulePlanner(),
            llm_planner=LLMPlanner(),
            confidence_threshold=self.settings.runtime_planner_confidence_threshold,
            registered_agents=agent_names,
        )

        self.executor = ExecutionExecutor(
            agents={
                "conversation": self.conversation_agent,
                "memory": self.memory_agent,
                "library": self.library_agent,
                "pattern": self.pattern_agent,
                "reflection": self.reflection_agent,
                "blind_spot": self.blind_spot_agent,
            },
            failure_manager=FailureManager(),
        )

    async def startup(self) -> None:
        """Async startup operations (connect to DB, Redis, tracing, health checks)."""
        if self.database:
            await self.database.connect()

        # Ollama health check at startup
        if hasattr(self, "ai_provider_registry"):
            ollama_provider = self.ai_provider_registry.get("ollama")
            if ollama_provider:
                try:
                    healthy = await ollama_provider.health_check()
                    if healthy:
                        logger.info("ollama_healthy", model=ollama_provider.config.model)
                    else:
                        logger.warning("ollama_unavailable_at_startup", model=ollama_provider.config.model)
                except Exception as exc:
                    logger.warning("ollama_startup_check_failed", error=str(exc))

        if self.settings.redis_url:
            try:
                import redis.asyncio as aioredis
                self.redis = await aioredis.from_url(
                    self.settings.redis_url, decode_responses=True,
                )
                self.cache._redis = self.redis
                self.rate_limiter._redis = self.redis
            except ImportError:
                pass
            except Exception:
                pass

        if self.settings.otel_enabled:
            from ayeneh.infrastructure.observability import TracingConfig, setup_tracing
            self.tracing_tracer = setup_tracing(TracingConfig(
                enabled=True,
                service_name=self.settings.otel_service_name,
                endpoint=self.settings.otel_endpoint,
            ))

        # Register subsystem health checks for DiagnosticsCollector
        self._register_diagnostics()

    async def shutdown(self) -> None:
        """Graceful shutdown — disconnect DB, Redis, flush tracing."""
        if self.database:
            await self.database.disconnect()

        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass

        try:
            from opentelemetry import trace
            provider = trace.get_tracer_provider()
            if hasattr(provider, "shutdown"):
                provider.shutdown()
        except Exception:
            pass

    def _make_uow_factory(self) -> Any:
        """Create a UoW factory from the database session factory."""
        from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork
        if self.database and self.database._session_factory:
            sf = self.database._session_factory
            def factory() -> UnitOfWork:
                return UnitOfWork(sf)
            return factory
        return None

    def _register_diagnostics(self) -> None:
        """Register subsystem health checks with DiagnosticsCollector."""
        from ayeneh.observability.diagnostics import SubsystemHealth
        import time

        def check_database() -> SubsystemHealth:
            return SubsystemHealth(
                name="database",
                status="healthy" if self.database else "not_configured",
                version="sqlite",
            )

        def check_ai_router() -> SubsystemHealth:
            return SubsystemHealth(
                name="ai_router",
                status="healthy" if self.ai_router else "not_configured",
            )

        def check_llm_gateway() -> SubsystemHealth:
            return SubsystemHealth(
                name="llm_gateway",
                status="healthy" if self.llm_gateway else "not_configured",
            )

        def check_metrics() -> SubsystemHealth:
            snap = self.metrics.snapshot()
            return SubsystemHealth(
                name="metrics",
                status="healthy",
                counters=snap.counters,
            )

        self.diagnostics.register("database", check_database)
        self.diagnostics.register("ai_router", check_ai_router)
        self.diagnostics.register("llm_gateway", check_llm_gateway)
        self.diagnostics.register("metrics", check_metrics)
