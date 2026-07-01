"""Job queue abstraction — pluggable backends for distributed job processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ayeneh.jobs.types import Job, QueueMetrics


class JobQueue(ABC):
    """Abstract job queue interface.

    Implementations: MemoryQueue (testing), RedisQueue (production),
    CeleryQueue, ArqQueue.
    """

    @abstractmethod
    async def enqueue(self, job: Job) -> str:
        """Add a job to the queue. Returns the job ID."""
        ...

    @abstractmethod
    async def dequeue(self, worker_id: str, timeout_seconds: float = 5.0) -> Job | None:
        """Remove and return the next job from the queue. Blocks up to timeout."""
        ...

    @abstractmethod
    async def requeue(self, job: Job) -> None:
        """Return a failed job to the queue for retry."""
        ...

    @abstractmethod
    async def peek(self, limit: int = 10) -> list[Job]:
        """View upcoming jobs without removing them."""
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Job | None:
        """Get a specific job by ID."""
        ...

    @abstractmethod
    async def update_job(self, job: Job) -> None:
        """Persist updated job state."""
        ...

    @abstractmethod
    async def get_metrics(self) -> QueueMetrics:
        """Return current queue metrics."""
        ...

    @abstractmethod
    async def purge(self) -> int:
        """Remove all pending jobs. Returns count removed."""
        ...

    @abstractmethod
    async def size(self) -> int:
        """Return approximate queue depth."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        pass
