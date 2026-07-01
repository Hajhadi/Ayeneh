"""Comprehensive tests for the distributed job system."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ayeneh.jobs.metrics import JobMetrics
from ayeneh.jobs.providers.memory import MemoryQueue
from ayeneh.jobs.scheduler import JobScheduler
from ayeneh.jobs.types import (
    Job,
    JobContext,
    JobPriority,
    JobStatus,
    RetryPolicy,
    WorkerInfo,
)
from ayeneh.jobs.worker import Worker


# ════════════════════════════════════════════════════════════════════════
# Types tests
# ════════════════════════════════════════════════════════════════════════

class TestJobTypes:
    def test_job_creation(self) -> None:
        job = Job(job_type="test", payload={"key": "value"})
        assert job.id
        assert job.status == JobStatus.PENDING
        assert job.job_type == "test"

    def test_job_payload_hash(self) -> None:
        job1 = Job(job_type="t", payload={"a": 1})
        job2 = Job(job_type="t", payload={"a": 1})
        assert job1.payload_hash() == job2.payload_hash()

    def test_job_duration(self) -> None:
        job = Job(job_type="t", started_at="2024-01-01T00:00:00+00:00", completed_at="2024-01-01T00:00:01+00:00")
        assert job.duration_ms() is not None
        assert job.duration_ms() > 0

    def test_retry_policy_delay(self) -> None:
        policy = RetryPolicy(backoff_base_ms=100, jitter=False)
        assert policy.get_delay(0) == 100.0
        assert policy.get_delay(1) == 200.0
        assert policy.get_delay(2) == 400.0

    def test_retry_policy_max_cap(self) -> None:
        policy = RetryPolicy(backoff_max_ms=500, jitter=False)
        assert policy.get_delay(10) == 500.0


# ════════════════════════════════════════════════════════════════════════
# MemoryQueue tests
# ════════════════════════════════════════════════════════════════════════

class TestMemoryQueue:
    @pytest.mark.asyncio
    async def test_enqueue_and_dequeue(self) -> None:
        queue = MemoryQueue()
        job = Job(job_type="test", payload={"data": 42})
        await queue.enqueue(job)

        dequeued = await queue.dequeue("w1", timeout_seconds=0.1)
        assert dequeued is not None
        assert dequeued.job_type == "test"
        assert dequeued.status == JobStatus.RUNNING
        assert dequeued.worker_id == "w1"

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        queue = MemoryQueue()
        await queue.enqueue(Job(job_type="low", priority=JobPriority.LOW))
        await queue.enqueue(Job(job_type="critical", priority=JobPriority.CRITICAL))
        await queue.enqueue(Job(job_type="normal", priority=JobPriority.NORMAL))

        first = await queue.dequeue("w1", timeout_seconds=0.1)
        assert first is not None
        assert first.job_type == "critical"

    @pytest.mark.asyncio
    async def test_empty_queue_returns_none(self) -> None:
        queue = MemoryQueue()
        result = await queue.dequeue("w1", timeout_seconds=0.05)
        assert result is None

    @pytest.mark.asyncio
    async def test_peek(self) -> None:
        queue = MemoryQueue()
        await queue.enqueue(Job(job_type="a"))
        await queue.enqueue(Job(job_type="b"))
        peeked = await queue.peek(limit=5)
        assert len(peeked) == 2

    @pytest.mark.asyncio
    async def test_get_and_update_job(self) -> None:
        queue = MemoryQueue()
        job = Job(job_type="test")
        await queue.enqueue(job)

        fetched = await queue.get_job(job.id)
        assert fetched is not None
        assert fetched.job_type == "test"

        fetched.status = JobStatus.COMPLETED
        await queue.update_job(fetched)

        updated = await queue.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_purge(self) -> None:
        queue = MemoryQueue()
        await queue.enqueue(Job(job_type="a"))
        await queue.enqueue(Job(job_type="b"))
        count = await queue.purge()
        assert count == 2
        assert await queue.size() == 0

    @pytest.mark.asyncio
    async def test_metrics(self) -> None:
        queue = MemoryQueue()
        await queue.enqueue(Job(job_type="test"))
        metrics = await queue.get_metrics()
        assert metrics.depth == 1


# ════════════════════════════════════════════════════════════════════════
# Worker tests
# ════════════════════════════════════════════════════════════════════════

class TestWorker:
    @pytest.mark.asyncio
    async def test_processes_job(self) -> None:
        queue = MemoryQueue()
        results = []

        async def handler(ctx: JobContext) -> dict[str, Any]:
            results.append(ctx.job.payload)
            return {"done": True}

        worker = Worker(queue, {"test_job": handler}, concurrency=1)
        await queue.enqueue(Job(job_type="test_job", payload={"x": 1}))

        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.3)
        await worker.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(results) == 1
        assert results[0] == {"x": 1}

    @pytest.mark.asyncio
    async def test_failed_job_retries(self) -> None:
        queue = MemoryQueue()
        attempt_count = 0

        async def flaky_handler(ctx: JobContext) -> dict[str, Any]:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError(f"fail attempt {attempt_count}")
            return {"ok": True}

        worker = Worker(queue, {"flaky": flaky_handler}, concurrency=1)
        await queue.enqueue(Job(
            job_type="flaky", max_attempts=3,
            retry_policy=RetryPolicy(backoff_base_ms=10, jitter=False),
        ))

        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)
        await worker.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_concurrency(self) -> None:
        queue = MemoryQueue()
        running = []

        async def slow_handler(ctx: JobContext) -> dict[str, Any]:
            running.append(ctx.job.id)
            await asyncio.sleep(0.1)
            return {"ok": True}

        worker = Worker(queue, {"slow": slow_handler}, concurrency=3)
        for i in range(3):
            await queue.enqueue(Job(job_type="slow", payload={"i": i}))

        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)
        await worker.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(running) == 3

    @pytest.mark.asyncio
    async def test_worker_info(self) -> None:
        queue = MemoryQueue()
        worker = Worker(queue, {})
        info = worker.info
        assert info.worker_id.startswith("worker-")
        assert info.status == "running" or info.status == "stopped"


# ════════════════════════════════════════════════════════════════════════
# Scheduler tests
# ════════════════════════════════════════════════════════════════════════

class TestScheduler:
    @pytest.mark.asyncio
    async def test_trigger_now(self) -> None:
        queue = MemoryQueue()
        scheduler = JobScheduler(queue)
        scheduler.register("test_job", "test_type", 9999)

        job_id = await scheduler.trigger_now("test_job")
        assert job_id is not None
        assert await queue.size() >= 1

    @pytest.mark.asyncio
    async def test_register_defaults(self) -> None:
        queue = MemoryQueue()
        scheduler = JobScheduler(queue)
        scheduler.register_defaults()
        schedules = scheduler.get_schedules()
        assert "daily_consolidation" in schedules
        assert "weekly_strengthening" in schedules
        assert "monthly_archival" in schedules

    @pytest.mark.asyncio
    async def test_get_schedules(self) -> None:
        queue = MemoryQueue()
        scheduler = JobScheduler(queue)
        scheduler.register("job1", "type1", 60)
        schedules = scheduler.get_schedules()
        assert schedules["job1"]["interval_seconds"] == 60


# ════════════════════════════════════════════════════════════════════════
# Metrics tests
# ════════════════════════════════════════════════════════════════════════

class TestJobMetrics:
    def test_record_and_summary(self) -> None:
        m = JobMetrics()
        m.record_enqueue("test")
        m.record_completion("test", 100.0)
        m.record_completion("test", 200.0)
        m.record_failure("test")
        m.record_retry()

        summary = m.get_summary()
        assert summary["total_enqueued"] == 1
        assert summary["total_completed"] == 2
        assert summary["total_failed"] == 1
        assert summary["success_rate"] == pytest.approx(2 / 3)

    def test_percentile(self) -> None:
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert JobMetrics._percentile(values, 0.95) == 100.0
        assert JobMetrics._percentile(values, 0.0) == 10.0
        assert JobMetrics._percentile(values, 1.0) == 100.0
        assert JobMetrics._percentile([], 0.5) == 0.0

    def test_prometheus_export(self) -> None:
        m = JobMetrics()
        m.record_enqueue("test")
        m.record_completion("test", 50.0)
        text = m.export_prometheus_text()
        assert "ayeneh_jobs_enqueued_total 1" in text
        assert "ayeneh_jobs_completed_total 1" in text


# ════════════════════════════════════════════════════════════════════════
# Integration: scheduler → worker → queue
# ════════════════════════════════════════════════════════════════════════

class TestJobIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end(self) -> None:
        queue = MemoryQueue()
        results = []

        async def handler(ctx: JobContext) -> dict[str, Any]:
            results.append(ctx.job.payload)
            return {"processed": True}

        worker = Worker(queue, {"e2e_job": handler}, concurrency=1)
        scheduler = JobScheduler(queue)
        scheduler.register("e2e", "e2e_job", 9999)

        worker_task = asyncio.create_task(worker.start())
        await scheduler.trigger_now("e2e")
        await asyncio.sleep(0.3)
        await worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        assert len(results) == 1
        assert results[0] == {}

    @pytest.mark.asyncio
    async def test_concurrent_workers(self) -> None:
        queue = MemoryQueue()
        completed = []

        async def handler(ctx: JobContext) -> dict[str, Any]:
            completed.append(ctx.job.id)
            return {"ok": True}

        w1 = Worker(queue, {"j": handler}, worker_id="w1", concurrency=2)
        w2 = Worker(queue, {"j": handler}, worker_id="w2", concurrency=2)

        for i in range(4):
            await queue.enqueue(Job(job_type="j", payload={"i": i}))

        t1 = asyncio.create_task(w1.start())
        t2 = asyncio.create_task(w2.start())
        await asyncio.sleep(0.5)
        await w1.stop()
        await w2.stop()
        t1.cancel()
        t2.cancel()
        try:
            await asyncio.gather(t1, t2)
        except asyncio.CancelledError:
            pass

        assert len(completed) == 4
