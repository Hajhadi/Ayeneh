"""In-memory job queue — suitable for testing and single-process deployments."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from ayeneh.jobs.queue import JobQueue
from ayeneh.jobs.types import Job, JobPriority, JobStatus, QueueMetrics


PRIORITY_WEIGHT = {
    JobPriority.CRITICAL: 0,
    JobPriority.HIGH: 1,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 3,
    JobPriority.BACKGROUND: 4,
}


class MemoryQueue(JobQueue):
    """In-memory priority queue with asyncio notification."""

    def __init__(self) -> None:
        self._pending: list[Job] = []
        self._jobs: dict[str, Job] = {}
        self._completed: list[Job] = []
        self._dead_letter: list[Job] = []
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._enqueue_count = 0
        self._start_time = time.time()

    async def enqueue(self, job: Job) -> str:
        async with self._lock:
            job.status = JobStatus.QUEUED
            job.queued_at = job.created_at
            self._jobs[job.id] = job
            self._pending.append(job)
            self._pending.sort(
                key=lambda j: PRIORITY_WEIGHT.get(j.priority, 2)
            )
            self._enqueue_count += 1
            self._event.set()
        return job.id

    async def dequeue(self, worker_id: str, timeout_seconds: float = 5.0) -> Job | None:
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            async with self._lock:
                if self._pending:
                    job = self._pending.pop(0)
                    job.status = JobStatus.RUNNING
                    job.worker_id = worker_id
                    job.started_at = job.created_at
                    job.attempt += 1
                    return job
            try:
                await asyncio.wait_for(self._event.wait(), timeout=0.5)
                self._event.clear()
            except asyncio.TimeoutError:
                continue

        return None

    async def requeue(self, job: Job) -> None:
        async with self._lock:
            job.status = JobStatus.QUEUED
            job.worker_id = None
            self._pending.append(job)
            self._pending.sort(
                key=lambda j: PRIORITY_WEIGHT.get(j.priority, 2)
            )
            self._event.set()

    async def peek(self, limit: int = 10) -> list[Job]:
        async with self._lock:
            return list(self._pending[:limit])

    async def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update_job(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job
            if job.status == JobStatus.COMPLETED:
                self._completed.append(job)
            elif job.status == JobStatus.DEAD_LETTER:
                self._dead_letter.append(job)

    async def get_metrics(self) -> QueueMetrics:
        async with self._lock:
            elapsed = time.time() - self._start_time
            throughput = self._enqueue_count / max(elapsed, 1)
            completed = sum(
                1 for j in self._jobs.values()
                if j.status == JobStatus.COMPLETED
            )
            failed = sum(
                1 for j in self._jobs.values()
                if j.status in (JobStatus.FAILED, JobStatus.DEAD_LETTER)
            )
            total = completed + failed
            return QueueMetrics(
                depth=len(self._pending),
                throughput_per_second=round(throughput, 2),
                success_rate=completed / max(total, 1),
                retry_rate=sum(1 for j in self._jobs.values() if j.attempt > 1) / max(total, 1),
            )

    async def purge(self) -> int:
        async with self._lock:
            count = len(self._pending)
            self._pending.clear()
            return count

    async def size(self) -> int:
        async with self._lock:
            return len(self._pending)

    def get_dead_letter(self) -> list[Job]:
        return list(self._dead_letter)

    def get_completed(self) -> list[Job]:
        return list(self._completed)
