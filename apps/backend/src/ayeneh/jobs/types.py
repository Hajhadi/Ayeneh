"""Distributed job system — types, status, priorities, policies."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable, Awaitable


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class JobPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base_ms: float = 1000.0
    backoff_max_ms: float = 60000.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: tuple[str, ...] = ("TimeoutError", "ConnectionError", "OSError")

    def get_delay(self, attempt: int) -> float:
        import random
        delay = min(
            self.backoff_base_ms * (self.backoff_multiplier ** attempt),
            self.backoff_max_ms,
        )
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay


@dataclass
class DeadLetterPolicy:
    enabled: bool = True
    max_size: int = 10000
    ttl_seconds: int = 86400 * 30


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = JobStatus.PENDING
    priority: str = JobPriority.NORMAL
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    worker_id: str | None = None
    attempt: int = 0
    max_attempts: int = 3

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    queued_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    result: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None

    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def payload_hash(self) -> str:
        raw = json.dumps(self.payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def duration_ms(self) -> float | None:
        if not self.started_at:
            return None
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at) if self.completed_at else datetime.now(UTC)
        return (end - start).total_seconds() * 1000


@dataclass
class JobContext:
    job: Job
    worker_id: str
    heartbeat_fn: Callable[[], Awaitable[None]] | None = None
    cancel_requested: bool = False

    async def heartbeat(self) -> None:
        if self.heartbeat_fn:
            await self.heartbeat_fn()

    def check_cancel(self) -> bool:
        return self.cancel_requested


@dataclass
class JobResult:
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class WorkerInfo:
    worker_id: str
    hostname: str
    pid: int
    started_at: str
    heartbeat_at: str
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    status: str = "running"


@dataclass
class QueueMetrics:
    depth: int = 0
    throughput_per_second: float = 0.0
    success_rate: float = 0.0
    retry_rate: float = 0.0
    avg_latency_ms: float = 0.0
    worker_count: int = 0
