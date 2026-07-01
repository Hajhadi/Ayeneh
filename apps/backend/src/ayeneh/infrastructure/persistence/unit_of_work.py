"""Unit of Work — coordinates repository access within a single transaction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ayeneh.goal.repos import (
    GoalEvolutionEventRepositoryImpl,
    GoalHistoryRepositoryImpl,
    GoalRepositoryImpl,
    GoalReviewRepositoryImpl,
)
from ayeneh.infrastructure.repositories.agent_run_repo import AgentRunRepositoryImpl
from ayeneh.infrastructure.repositories.book_repo import BookRepositoryImpl
from ayeneh.infrastructure.repositories.conversation_repo import ConversationRepositoryImpl
from ayeneh.infrastructure.repositories.embedding_repo import EmbeddingRepositoryImpl
from ayeneh.infrastructure.repositories.epistemic_profile_repo import EpistemicProfileRepositoryImpl
from ayeneh.infrastructure.repositories.execution_plan_repo import ExecutionPlanRepositoryImpl
from ayeneh.infrastructure.repositories.memory_evolution_repo import (
    MemoryEvolutionEventRepositoryImpl,
    MemoryLineageRepositoryImpl,
)
from ayeneh.infrastructure.repositories.memory_repo import MemoryRepositoryImpl
from ayeneh.infrastructure.repositories.message_repo import MessageRepositoryImpl
from ayeneh.infrastructure.repositories.observation_repo import ObservationRepositoryImpl
from ayeneh.infrastructure.repositories.pattern_repo import PatternRepositoryImpl
from ayeneh.infrastructure.repositories.prompt_template_repo import PromptTemplateRepositoryImpl
from ayeneh.infrastructure.repositories.reflection_repo import ReflectionRepositoryImpl
from ayeneh.infrastructure.repositories.session_repo import SessionRepositoryImpl
from ayeneh.infrastructure.repositories.user_repo import UserRepositoryImpl

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Coordinates all repository access within a single database transaction.

    Usage:
        async with UnitOfWork(session_factory) as uow:
            user = await uow.users.get_by_id(user_id)
            await uow.commit()
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.users: UserRepositoryImpl | None = None
        self.sessions: SessionRepositoryImpl | None = None
        self.conversations: ConversationRepositoryImpl | None = None
        self.messages: MessageRepositoryImpl | None = None
        self.memories: MemoryRepositoryImpl | None = None
        self.books: BookRepositoryImpl | None = None
        self.prompt_templates: PromptTemplateRepositoryImpl | None = None
        self.execution_plans: ExecutionPlanRepositoryImpl | None = None
        self.agent_runs: AgentRunRepositoryImpl | None = None
        self.embeddings: EmbeddingRepositoryImpl | None = None
        self.patterns: PatternRepositoryImpl | None = None
        self.reflections: ReflectionRepositoryImpl | None = None
        self.observations: ObservationRepositoryImpl | None = None
        self.memory_evolution_events: MemoryEvolutionEventRepositoryImpl | None = None
        self.memory_lineage: MemoryLineageRepositoryImpl | None = None
        self.goals: GoalRepositoryImpl | None = None
        self.goal_evolution_events: GoalEvolutionEventRepositoryImpl | None = None
        self.goal_history: GoalHistoryRepositoryImpl | None = None
        self.goal_reviews: GoalReviewRepositoryImpl | None = None
        self.epistemic_profiles: EpistemicProfileRepositoryImpl | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        self.users = UserRepositoryImpl(self._session)
        self.sessions = SessionRepositoryImpl(self._session)
        self.conversations = ConversationRepositoryImpl(self._session)
        self.messages = MessageRepositoryImpl(self._session)
        self.memories = MemoryRepositoryImpl(self._session)
        self.books = BookRepositoryImpl(self._session)
        self.prompt_templates = PromptTemplateRepositoryImpl(self._session)
        self.execution_plans = ExecutionPlanRepositoryImpl(self._session)
        self.agent_runs = AgentRunRepositoryImpl(self._session)
        self.embeddings = EmbeddingRepositoryImpl(self._session)
        self.patterns = PatternRepositoryImpl(self._session)
        self.reflections = ReflectionRepositoryImpl(self._session)
        self.observations = ObservationRepositoryImpl(self._session)
        self.memory_evolution_events = MemoryEvolutionEventRepositoryImpl(self._session)
        self.memory_lineage = MemoryLineageRepositoryImpl(self._session)
        self.goals = GoalRepositoryImpl(self._session)
        self.goal_evolution_events = GoalEvolutionEventRepositoryImpl(self._session)
        self.goal_history = GoalHistoryRepositoryImpl(self._session)
        self.goal_reviews = GoalReviewRepositoryImpl(self._session)
        self.epistemic_profiles = EpistemicProfileRepositoryImpl(self._session)
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session:
            await self._session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        assert self._session is not None, "UnitOfWork not entered"
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        assert self._session is not None, "UnitOfWork not entered"
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        assert self._session is not None, "UnitOfWork not entered"
        await self._session.flush()
