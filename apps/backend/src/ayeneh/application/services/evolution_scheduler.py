"""Evolution scheduler — triggers memory evolution jobs on schedule.

Integrates MemoryEvolutionService with the application lifecycle.
Provides startup hooks and job runners for daily, weekly, and monthly
evolution cycles.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SchedulerConfig:
    daily_interval_hours: float = 24.0
    weekly_interval_hours: float = 168.0
    monthly_interval_hours: float = 720.0
    enabled: bool = True


@dataclass
class ScheduleResult:
    job_type: str
    user_id: str
    success: bool = True
    duration_ms: float = 0.0
    error: str | None = None


class EvolutionScheduler:
    """Runs memory evolution jobs on configurable schedules.

    Usage:
        scheduler = EvolutionScheduler(evolution_service)
        await scheduler.start(user_ids=["user1", "user2"])
        ...
        await scheduler.stop()
    """

    def __init__(
        self,
        evolution_service: Any,
        config: SchedulerConfig | None = None,
        event_publisher: Any | None = None,
    ) -> None:
        self._evolution = evolution_service
        self._config = config or SchedulerConfig()
        self._events = event_publisher
        self._running = False
        self._tasks: list[asyncio.Task[None]] = []
        self._results: list[ScheduleResult] = []

    async def start(self, user_ids: list[str]) -> None:
        if not self._config.enabled:
            return
        self._running = True
        self._tasks.append(
            asyncio.create_task(self._daily_loop(user_ids))
        )
        self._tasks.append(
            asyncio.create_task(self._weekly_loop(user_ids))
        )
        self._tasks.append(
            asyncio.create_task(self._monthly_loop(user_ids))
        )
        logger.info("evolution_scheduler_started", user_count=len(user_ids))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("evolution_scheduler_stopped")

    async def trigger_daily(self, user_id: str) -> ScheduleResult:
        return await self._run_job("daily_consolidation", user_id)

    async def trigger_weekly(self, user_id: str) -> ScheduleResult:
        return await self._run_job("weekly_strengthening", user_id)

    async def trigger_monthly(self, user_id: str) -> ScheduleResult:
        return await self._run_job("monthly_archival", user_id)

    def get_recent_results(self, limit: int = 50) -> list[ScheduleResult]:
        return self._results[-limit:]

    async def _run_job(self, job_type: str, user_id: str) -> ScheduleResult:
        start = time.monotonic()
        try:
            if job_type == "daily_consolidation":
                metrics = await self._evolution.run_consolidation(user_id)
                result = ScheduleResult(
                    job_type=job_type, user_id=user_id,
                    duration_ms=(time.monotonic() - start) * 1000,
                )
            elif job_type == "weekly_strengthening":
                await self._evolution.detect_and_merge_similar(user_id)
                result = ScheduleResult(
                    job_type=job_type, user_id=user_id,
                    duration_ms=(time.monotonic() - start) * 1000,
                )
            elif job_type == "monthly_archival":
                await self._evolution.run_consolidation(user_id)
                result = ScheduleResult(
                    job_type=job_type, user_id=user_id,
                    duration_ms=(time.monotonic() - start) * 1000,
                )
            else:
                result = ScheduleResult(
                    job_type=job_type, user_id=user_id,
                    success=False, error=f"Unknown job type: {job_type}",
                )
        except Exception as exc:
            result = ScheduleResult(
                job_type=job_type, user_id=user_id,
                success=False, error=str(exc),
                duration_ms=(time.monotonic() - start) * 1000,
            )
            logger.exception("evolution_job_failed", job_type=job_type, user_id=user_id)

        self._results.append(result)

        if self._events and result.success:
            await self._events.publish(f"Evolution_{job_type}_Completed", {
                "user_id": user_id, "duration_ms": result.duration_ms,
            })

        return result

    async def _daily_loop(self, user_ids: list[str]) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._config.daily_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            for uid in user_ids:
                await self._run_job("daily_consolidation", uid)

    async def _weekly_loop(self, user_ids: list[str]) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._config.weekly_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            for uid in user_ids:
                await self._run_job("weekly_strengthening", uid)

    async def _monthly_loop(self, user_ids: list[str]) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._config.monthly_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            for uid in user_ids:
                await self._run_job("monthly_archival", uid)
