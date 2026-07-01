"""Job system API endpoints — list, get, retry, cancel, status."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["jobs"])


class EnqueueRequest(BaseModel):
    job_type: str
    payload: dict[str, Any] = {}
    priority: str = "normal"


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    priority: str
    attempt: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float | None = None


class QueueStatusResponse(BaseModel):
    depth: int
    throughput_per_second: float
    success_rate: float
    retry_rate: float
    avg_latency_ms: float


class WorkerStatusResponse(BaseModel):
    worker_id: str
    hostname: str
    pid: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    status: str


@router.post("/jobs", status_code=201)
async def enqueue_job(request: Request, body: EnqueueRequest) -> dict[str, str]:
    from ayeneh.jobs.types import Job, JobPriority

    job = Job(
        job_type=body.job_type,
        payload=body.payload,
        priority=body.priority,
    )

    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")

    job_id = await queue.enqueue(job)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str) -> JobResponse:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")

    job = await queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id, job_type=job.job_type, status=job.status,
        priority=job.priority, attempt=job.attempt,
        created_at=job.created_at, started_at=job.started_at,
        completed_at=job.completed_at, result=job.result,
        error=job.error, duration_ms=job.duration_ms(),
    )


@router.post("/jobs/{job_id}/retry", status_code=202)
async def retry_job(request: Request, job_id: str) -> dict[str, str]:
    from ayeneh.jobs.types import JobStatus

    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")

    job = await queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.FAILED, JobStatus.DEAD_LETTER):
        raise HTTPException(status_code=400, detail="Job is not retryable")

    job.status = JobStatus.QUEUED
    job.attempt = 0
    job.error = None
    job.worker_id = None
    await queue.requeue(job)
    return {"job_id": job_id, "status": "requeued"}


@router.post("/jobs/{job_id}/cancel", status_code=202)
async def cancel_job(request: Request, job_id: str) -> dict[str, str]:
    from ayeneh.jobs.types import JobStatus

    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")

    job = await queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Job is not cancellable")

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(UTC).isoformat()
    await queue.update_job(job)
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/queue/status")
async def queue_status(request: Request) -> QueueStatusResponse:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")

    metrics = await queue.get_metrics()
    return QueueStatusResponse(
        depth=metrics.depth,
        throughput_per_second=metrics.throughput_per_second,
        success_rate=metrics.success_rate,
        retry_rate=metrics.retry_rate,
        avg_latency_ms=metrics.avg_latency_ms,
    )


@router.get("/workers")
async def worker_status(request: Request) -> list[WorkerStatusResponse]:
    workers = getattr(request.app.state, "workers", [])
    return [
        WorkerStatusResponse(
            worker_id=w.worker_id, hostname=w.hostname, pid=w.pid,
            active_jobs=w.active_jobs, completed_jobs=w.completed_jobs,
            failed_jobs=w.failed_jobs, status=w.status,
        )
        for w in workers
    ]
