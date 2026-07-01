"""Background worker — runs long-running indexing jobs asynchronously."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackgroundJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = ""
    status: str = JobStatus.QUEUED
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0


class IngestionWorker:
    """Background worker that processes ingestion jobs sequentially.

    Prevents concurrent indexing for the same book. Publishes progress
    events and tracks job status.
    """

    def __init__(
        self,
        ingestion_service: Any,
        event_publisher: Any | None = None,
        max_concurrent: int = 1,
    ) -> None:
        self._ingestion = ingestion_service
        self._events = event_publisher
        self._max_concurrent = max_concurrent
        self._jobs: dict[str, BackgroundJob] = {}
        self._active_jobs: set[str] = set()
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        self._running = True
        for _ in range(self._max_concurrent):
            task = asyncio.create_task(self._worker_loop())
            self._workers.append(task)
        logger.info("worker_started", max_concurrent=self._max_concurrent)

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("worker_stopped")

    async def submit(
        self,
        book_id: str,
        content: bytes,
        filename: str,
        *,
        reindex: bool = False,
    ) -> BackgroundJob:
        job = BackgroundJob(
            job_type="reindex" if reindex else "ingest",
            payload={"book_id": book_id, "filename": filename, "reindex": reindex},
        )
        self._jobs[job.id] = job
        await self._queue.put(job.id)

        if self._events:
            await self._events.publish("JobQueued", {
                "job_id": job.id,
                "book_id": book_id,
                "job_type": job.job_type,
            })

        logger.info("job_submitted", job_id=job.id, book_id=book_id)
        return job

    def get_job(self, job_id: str) -> BackgroundJob | None:
        return self._jobs.get(job_id)

    def get_jobs_for_book(self, book_id: str) -> list[BackgroundJob]:
        return [
            j for j in self._jobs.values()
            if j.payload.get("book_id") == book_id
        ]

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            job = self._jobs.get(job_id)
            if job is None:
                continue

            book_id = job.payload.get("book_id", "")
            if book_id in self._active_jobs:
                logger.info("skipping_duplicate_job", job_id=job_id, book_id=book_id)
                job.status = JobStatus.FAILED
                job.error = "Another job for this book is already running"
                job.completed_at = datetime.now(UTC)
                continue

            self._active_jobs.add(book_id)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            start = time.monotonic()

            try:
                result = await self._ingestion.ingest(
                    book_id=book_id,
                    content=b"",
                    filename=job.payload.get("filename", ""),
                )
                job.result = {
                    "total_chunks": result.total_chunks,
                    "chapters_detected": result.chapters_detected,
                    "status": result.status,
                }
                job.status = JobStatus.COMPLETED

                if self._events:
                    await self._events.publish("JobCompleted", {
                        "job_id": job.id,
                        "book_id": book_id,
                    })
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                logger.exception("job_failed", job_id=job_id, error=str(exc))

                if self._events:
                    await self._events.publish("JobFailed", {
                        "job_id": job.id,
                        "book_id": book_id,
                        "error": str(exc),
                    })
            finally:
                job.duration_ms = (time.monotonic() - start) * 1000
                job.completed_at = datetime.now(UTC)
                self._active_jobs.discard(book_id)
