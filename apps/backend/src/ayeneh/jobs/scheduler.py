"""Job scheduler — manages scheduled and periodic jobs."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

from ayeneh.jobs.queue import JobQueue
from ayeneh.jobs.types import Job, JobPriority

logger = structlog.get_logger(__name__)


@dataclass
class ScheduledJob:
    name: str
    job_type: str
    interval_seconds: float
    payload: dict[str, Any] = field(default_factory=dict)
    priority: str = JobPriority.LOW
    enabled: bool = True
    last_run: float = 0.0


class JobScheduler:
    """Manages periodic scheduled jobs by enqueuing them on intervals."""

    def __init__(self, queue: JobQueue) -> None:
        self._queue = queue
        self._schedules: dict[str, ScheduledJob] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    def register(
        self,
        name: str,
        job_type: str,
        interval_seconds: float,
        payload: dict[str, Any] | None = None,
        priority: str = JobPriority.LOW,
    ) -> None:
        self._schedules[name] = ScheduledJob(
            name=name, job_type=job_type,
            interval_seconds=interval_seconds,
            payload=payload or {},
            priority=priority,
        )

    def register_defaults(self) -> None:
        self.register("daily_consolidation", "memory_consolidation", 86400)
        self.register("weekly_strengthening", "memory_strengthening", 604800)
        self.register("monthly_archival", "memory_archival", 2592000)
        self.register("embedding_reindex", "embedding_reindex", 3600)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("scheduler_started", schedules=len(self._schedules))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("scheduler_stopped")

    async def trigger_now(self, name: str) -> str | None:
        schedule = self._schedules.get(name)
        if schedule is None:
            return None

        job = Job(
            job_type=schedule.job_type,
            payload=schedule.payload.copy(),
            priority=schedule.priority,
            tags=[f"scheduled:{name}"],
        )
        job_id = await self._queue.enqueue(job)
        logger.info("scheduled_job_triggered", name=name, job_id=job_id)
        return job_id

    def get_schedules(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "job_type": s.job_type,
                "interval_seconds": s.interval_seconds,
                "enabled": s.enabled,
                "last_run": s.last_run,
            }
            for name, s in self._schedules.items()
        }

    async def _loop(self) -> None:
        while self._running:
            now = time.time()
            for name, schedule in self._schedules.items():
                if not schedule.enabled:
                    continue
                if now - schedule.last_run >= schedule.interval_seconds:
                    await self.trigger_now(name)
                    schedule.last_run = now
            await asyncio.sleep(10)
