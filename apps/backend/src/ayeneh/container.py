"""Dependency injection container using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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

        # LLM providers
        from ayeneh.llm.registry import initialize_providers
        self.provider_registry = initialize_providers(self.settings)
        try:
            self.llm_gateway = self.provider_registry.get_or_default()
        except RuntimeError:
            self.llm_gateway = None
            logger.warning("no_llm_provider_available")

        self.prompt_service = PromptService()

        # Product profiles
        from ayeneh.product.registry import load_default_profiles
        from ayeneh.product.observability import ProductMetrics
        self.product_registry = load_default_profiles()
        self.product_metrics = ProductMetrics()

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

        self.conversation_agent = ConversationAgent(llm=self.llm_gateway)
        self.memory_agent = MemoryAgent()
        self.library_agent = LibraryAgent()
        self.pattern_agent = PatternAgent()
        self.reflection_agent = ReflectionAgent(llm=self.llm_gateway)
        self.blind_spot_agent = BlindSpotAgent(llm=self.llm_gateway)

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
        """Async startup operations (connect to DB, Redis, tracing)."""
        if self.database:
            await self.database.connect()

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
