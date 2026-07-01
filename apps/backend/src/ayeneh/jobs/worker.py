"""Worker runtime — processes jobs from the queue with lifecycle management."""

from __future__ import annotations

import asyncio
import os
import signal
import time
import traceback
from typing import Any, Awaitable, Callable

import structlog

from ayeneh.jobs.queue import JobQueue
from ayeneh.jobs.types import (
    Job,
    JobContext,
    JobPriority,
    JobResult,
    JobStatus,
    WorkerInfo,
)

logger = structlog.get_logger(__name__)

JobHandler = Callable[[JobContext], Awaitable[dict[str, Any]]]


class Worker:
    """Distributed job worker with lifecycle management.

    Supports: graceful startup/shutdown, heartbeat, concurrency,
    cancellation, health reporting, worker registration.
    """

    def __init__(
        self,
        queue: JobQueue,
        handlers: dict[str, JobHandler],
        worker_id: str | None = None,
        concurrency: int = 1,
        heartbeat_interval: float = 15.0,
        shutdown_timeout: float = 30.0,
    ) -> None:
        self._queue = queue
        self._handlers = handlers
        self._worker_id = worker_id or f"worker-{os.getpid()}"
        self._concurrency = concurrency
        self._heartbeat_interval = heartbeat_interval
        self._shutdown_timeout = shutdown_timeout

        self._running = False
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._info = WorkerInfo(
            worker_id=self._worker_id,
            hostname=os.uname().nodename,
            pid=os.getpid(),
            started_at="",
            heartbeat_at="",
        )
        self._completion_count = 0
        self._failure_count = 0

    @property
    def info(self) -> WorkerInfo:
        self._info.active_jobs = len(self._active_tasks)
        self._info.completed_jobs = self._completion_count
        self._info.failed_jobs = self._failure_count
        return self._info

    async def start(self) -> None:
        self._running = True
        self._info.started_at = self._info.heartbeat_at = self._timestamp()
        self._info.status = "running"
        logger.info("worker_started", worker_id=self._worker_id, concurrency=self._concurrency)

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        worker_tasks = [
            asyncio.create_task(self._process_loop(i))
            for i in range(self._concurrency)
        ]

        try:
            await asyncio.gather(heartbeat_task, *worker_tasks)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            self._info.status = "stopped"
            logger.info("worker_stopped", worker_id=self._worker_id)

    async def stop(self) -> None:
        self._running = False
        logger.info("worker_stopping", worker_id=self._worker_id, active=len(self._active_tasks))
        if self._active_tasks:
            await asyncio.wait_for(
                asyncio.gather(*self._active_tasks.values(), return_exceptions=True),
                timeout=self._shutdown_timeout,
            )
        self._active_tasks.clear()

    async def _process_loop(self, slot: int) -> None:
        while self._running:
            try:
                job = await self._queue.dequeue(self._worker_id, timeout_seconds=1.0)
                if job is None:
                    continue

                task = asyncio.create_task(self._execute_job(job))
                self._active_tasks[job.id] = task
                task.add_done_callback(lambda t, jid=job.id: self._active_tasks.pop(jid, None))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("worker_loop_error", slot=slot, error=str(exc))

    async def _execute_job(self, job: Job) -> None:
        handler = self._handlers.get(job.job_type)
        if handler is None:
            job.status = JobStatus.FAILED
            job.error = f"No handler for job_type: {job.job_type}"
            job.completed_at = self._timestamp()
            await self._queue.update_job(job)
            self._failure_count += 1
            logger.warning("no_handler", job_id=job.id, job_type=job.job_type)
            return

        ctx = JobContext(job=job, worker_id=self._worker_id)

        try:
            result = await asyncio.wait_for(
                handler(ctx),
                timeout=300.0,
            )
            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = self._timestamp()
            await self._queue.update_job(job)
            self._completion_count += 1
            logger.info("job_completed", job_id=job.id, job_type=job.job_type, attempt=job.attempt)

        except asyncio.TimeoutError:
            await self._handle_failure(job, "Job execution timed out")

        except Exception as exc:
            await self._handle_failure(job, str(exc))

    async def _handle_failure(self, job: Job, error_msg: str) -> None:
        job.error = error_msg
        job.error_type = type(error_msg).__name__
        job.completed_at = self._timestamp()

        if job.attempt < job.max_attempts:
            job.status = JobStatus.RETRYING
            await self._queue.update_job(job)

            delay_ms = job.retry_policy.get_delay(job.attempt)
            logger.warning("job_retrying", job_id=job.id, attempt=job.attempt, delay_ms=delay_ms)

            await asyncio.sleep(delay_ms / 1000)
            await self._queue.requeue(job)
        else:
            job.status = JobStatus.DEAD_LETTER
            await self._queue.update_job(job)
            self._failure_count += 1
            logger.error("job_dead_letter", job_id=job.id, error=error_msg)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            self._info.heartbeat_at = self._timestamp()
            self._info.active_jobs = len(self._active_tasks)
            await asyncio.sleep(self._heartbeat_interval)

    @staticmethod
    def _timestamp() -> str:
        return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
