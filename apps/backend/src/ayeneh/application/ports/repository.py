"""Repository port interfaces — abstract contracts for data access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T")


class BaseRepository[T](ABC):
    """Abstract base repository with generic CRUD operations."""

    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> T | None:
        """Retrieve a single entity by its primary key."""

    @abstractmethod
    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[T]:
        """List entities with optional filtering and pagination."""

    @abstractmethod
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching optional filters."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity and return it."""

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity and return it."""

    @abstractmethod
    async def delete(self, entity_id: Any) -> None:
        """Soft-delete an entity by setting deleted_at."""


class UserRepository(BaseRepository[T], ABC):
    """User-specific repository operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> T | None:
        """Find a user by email (active users only)."""


class ConversationRepository(BaseRepository[T], ABC):
    """Conversation-specific repository operations."""

    @abstractmethod
    async def get_active_by_user(self, user_id: Any) -> T | None:
        """Find the active conversation for a user."""


class MemoryRepository(BaseRepository[T], ABC):
    """Memory-specific repository operations."""

    @abstractmethod
    async def list_by_type(self, user_id: Any, memory_type: str) -> Sequence[T]:
        """List memories of a specific type for a user."""


class BookRepository(BaseRepository[T], ABC):
    """Book-specific repository operations."""

    @abstractmethod
    async def get_with_chapters(self, book_id: Any) -> T | None:
        """Load a book with its chapters."""


class PromptTemplateRepository(BaseRepository[T], ABC):
    """Prompt template-specific repository operations."""

    @abstractmethod
    async def get_active_by_task_type(self, task_type: str) -> T | None:
        """Get the active template for a task type."""


class ExecutionPlanRepository(BaseRepository[T], ABC):
    """Execution plan-specific repository operations."""

    pass


class AgentRunRepository(BaseRepository[T], ABC):
    """Agent run-specific repository operations."""

    @abstractmethod
    async def list_by_plan(self, plan_id: Any) -> Sequence[T]:
        """List all runs for a given plan."""


class EpistemicProfileRepository(BaseRepository[T], ABC):
    """Epistemic profile-specific repository operations."""

    @abstractmethod
    async def get_by_book_id(self, book_id: Any) -> T | None:
        """Load the epistemic profile for a specific book."""

    @abstractmethod
    async def list_by_user(self, user_id: Any) -> Sequence[T]:
        """List all epistemic profiles for a user."""

    @abstractmethod
    async def list_by_domain(self, user_id: Any, domain: str) -> Sequence[T]:
        """List profiles filtered by knowledge domain."""
