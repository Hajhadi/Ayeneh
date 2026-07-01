"""Load tests — measures throughput and latency under concurrent load."""

from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from ayeneh.main import app


@dataclass
class LoadTestResult:
    operation: str
    total_requests: int
    successful: int
    failed: int
    duration_ms: float
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    throughput_rps: float = 0.0

    def summary(self) -> str:
        return (
            f"{self.operation}: {self.total_requests} reqs, "
            f"{self.successful} ok, {self.failed} fail, "
            f"{self.duration_ms:.0f}ms total, "
            f"{self.throughput_rps:.1f} rps, "
            f"p50={self.p50_ms:.1f}ms p95={self.p95_ms:.1f}ms p99={self.p99_ms:.1f}ms"
        )


async def _benchmark(
    client: AsyncClient,
    method: str,
    path: str,
    body: dict | None = None,
    concurrent: int = 10,
    total: int = 100,
) -> LoadTestResult:
    latencies: list[float] = []
    errors = 0

    sem = asyncio.Semaphore(concurrent)
    start = time.monotonic()

    async def _call() -> None:
        nonlocal errors
        async with sem:
            t0 = time.monotonic()
            try:
                if method == "GET":
                    resp = await client.get(path)
                else:
                    resp = await client.post(path, json=body)
                elapsed = (time.monotonic() - t0) * 1000
                latencies.append(elapsed)
                if resp.status_code >= 500:
                    errors += 1
            except Exception:
                errors += 1
                latencies.append(0)

    await asyncio.gather(*[_call() for _ in range(total)])
    duration = (time.monotonic() - start) * 1000
    latencies.sort()

    return LoadTestResult(
        operation=f"{method} {path}",
        total_requests=total,
        successful=len(latencies) - errors,
        failed=errors,
        duration_ms=duration,
        p50_ms=latencies[len(latencies) // 2] if latencies else 0,
        p95_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0,
        p99_ms=latencies[int(len(latencies) * 0.99)] if latencies else 0,
        throughput_rps=total / (duration / 1000) if duration > 0 else 0,
    )


@pytest.mark.asyncio
async def test_load_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        result = await _benchmark(client, "GET", "/api/v1/health", concurrent=50, total=500)
        assert result.failed == 0
        assert result.p95_ms < 500


@pytest.mark.asyncio
async def test_load_conversations() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        result = await _benchmark(
            client, "POST", "/api/v1/conversations",
            body={"title": "Load Test Conv"}, concurrent=10, total=100,
        )
        assert result.successful > 0


@pytest.mark.asyncio
async def test_load_concurrent_gets() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        results = await asyncio.gather(*[
            _benchmark(client, "GET", "/api/v1/health", concurrent=20, total=200)
            for _ in range(3)
        ])
        for r in results:
            assert r.failed == 0


@pytest.mark.asyncio
async def test_load_runtime() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        result = await _benchmark(
            client, "GET", "/api/v1/runtime/status", concurrent=10, total=100,
        )
        assert result.failed == 0


@pytest.mark.asyncio
async def test_load_jobs() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        result = await _benchmark(
            client, "POST", "/api/v1/jobs",
            body={"job_type": "bench", "payload": {"i": 0}}, concurrent=5, total=50,
        )
        assert result.successful > 0


@pytest.mark.asyncio
async def test_load_mix_report() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await _benchmark(client, "GET", "/api/v1/health", concurrent=20, total=200)
        conv = await _benchmark(client, "POST", "/api/v1/conversations",
                                body={"title": "Mix"}, concurrent=5, total=50)

        lines = ["", "=" * 60, "LOAD TEST REPORT", "=" * 60, health.summary(), conv.summary(), "=" * 60]
        report = "\n".join(lines)
        assert "rps" in report
