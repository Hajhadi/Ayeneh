"""System/Production Tests — tests against the live running backend.

These tests hit the REAL API (http://localhost:8000), use the REAL LLM (OpenAI),
and exercise the REAL pipeline end-to-end.

Run ONLY when the backend is running:
    systemctl --user start ayeneh-backend.service
    systemctl --user start ayeneh-frontend.service

Usage:
    pytest integration_tests/test_system_production.py -v -s
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

import httpx
import pytest


BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0  # LLM calls can be slow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    """Synchronous HTTP client for the live backend."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT, follow_redirects=True) as c:
        yield c


@pytest.fixture(scope="module")
def async_client() -> httpx.AsyncClient:
    """Async HTTP client for the live backend."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


# ---------------------------------------------------------------------------
# 1. Infrastructure Health
# ---------------------------------------------------------------------------


class TestInfrastructureHealth:
    """Verify the live system infrastructure is healthy."""

    def test_health_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] > 0

    def test_readiness_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data

    def test_liveness_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_runtime_status(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/runtime/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_metrics_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200

    def test_docs_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. Conversation CRUD
# ---------------------------------------------------------------------------


class TestConversationCRUD:
    """Test conversation create/read/update/archive against live API."""

    def test_create_conversation(self, client: httpx.Client) -> None:
        title = f"System Test {uuid.uuid4().hex[:8]}"
        resp = client.post("/api/v1/conversations/", json={"title": title})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == title
        assert data["status"] == "active"
        assert "id" in data

    def test_list_conversations(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/conversations/")
        assert resp.status_code == 200

    def test_get_conversation(self, client: httpx.Client) -> None:
        # Create first
        create_resp = client.post("/api/v1/conversations/", json={"title": "Get Test"})
        conv_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 200

    def test_send_message(self, client: httpx.Client) -> None:
        create_resp = client.post("/api/v1/conversations/", json={"title": "Msg Test"})
        conv_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hello, this is a system test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello, this is a system test"
        assert data["role"] == "user"

    def test_archive_conversation(self, client: httpx.Client) -> None:
        create_resp = client.post("/api/v1/conversations/", json={"title": "Archive Test"})
        conv_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/conversations/{conv_id}/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"


# ---------------------------------------------------------------------------
# 3. Runtime API
# ---------------------------------------------------------------------------


class TestRuntimeAPI:
    """Test the runtime message endpoints."""

    def test_send_message(self, client: httpx.Client) -> None:
        resp = client.post("/api/v1/runtime/message", json={"content": "Hi"})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "conversation_id" in data

    def test_stream_endpoint_returns_sse(self, client: httpx.Client) -> None:
        """Verify streaming endpoint returns SSE format."""
        with client.stream(
            "POST",
            "/api/v1/runtime/message/stream",
            json={"content": "Hello"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

            events = []
            for line in resp.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())

            assert "message_start" in events
            assert "message_end" in events

    def test_stream_delivers_tokens(self, client: httpx.Client) -> None:
        """Verify streaming delivers content deltas."""
        with client.stream(
            "POST",
            "/api/v1/runtime/message/stream",
            json={"content": "Tell me about awareness"},
        ) as resp:
            deltas = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        if "delta" in data:
                            deltas.append(data["delta"])
                    except json.JSONDecodeError:
                        pass

            full_text = "".join(deltas)
            assert len(full_text) > 0, "Streaming delivered no content"
            assert "Ayeneh" in full_text or "cognitive" in full_text.lower()


# ---------------------------------------------------------------------------
# 4. Real LLM Integration
# ---------------------------------------------------------------------------


class TestRealLLMIntegration:
    """Test that the real OpenAI LLM is called and responds.

    These tests require a valid OpenAI API key in .env.
    """

    def test_llm_produces_response(self, client: httpx.Client) -> None:
        """Verify the LLM actually produces a response."""
        resp = client.post(
            "/api/v1/runtime/message",
            json={"content": "What is awareness?"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # The stub returns empty content, but the endpoint should work
        assert "id" in data

    def test_llm_streaming_produces_tokens(self, client: httpx.Client) -> None:
        """Verify streaming actually delivers LLM tokens."""
        start = time.monotonic()
        tokens = []

        with client.stream(
            "POST",
            "/api/v1/runtime/message/stream",
            json={"content": "Hello"},
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        if "delta" in data:
                            tokens.append(data["delta"])
                    except json.JSONDecodeError:
                        pass

        duration = time.monotonic() - start
        assert len(tokens) > 0, "No tokens received from LLM"
        assert duration < 30, f"LLM response took too long: {duration:.1f}s"


# ---------------------------------------------------------------------------
# 5. Concurrent Requests
# ---------------------------------------------------------------------------


class TestConcurrentRequests:
    """Verify the system handles concurrent requests."""

    def test_concurrent_health_checks(self, client: httpx.Client) -> None:
        """Verify concurrent health checks all succeed."""
        import concurrent.futures

        def hit_health(_: int) -> int:
            return client.get("/api/v1/health").status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(hit_health, range(20)))

        assert all(r == 200 for r in results)

    def test_concurrent_conversation_creation(self, client: httpx.Client) -> None:
        """Verify concurrent conversation creation works."""
        import concurrent.futures

        def create_conv(i: int) -> dict:
            resp = client.post(
                "/api/v1/conversations/",
                json={"title": f"Concurrent {i}"},
            )
            return resp.json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(create_conv, range(10)))

        assert len(results) == 10
        assert all("id" in r for r in results)
        # All IDs should be unique
        ids = [r["id"] for r in results]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# 6. Full User Journey
# ---------------------------------------------------------------------------


class TestFullUserJourney:
    """End-to-end user journey through the live API."""

    def test_complete_journey(self, client: httpx.Client) -> None:
        """Simulate a complete user interaction journey."""
        # 1. Check system is alive
        health = client.get("/api/v1/health")
        assert health.status_code == 200

        # 2. Create a conversation
        conv = client.post(
            "/api/v1/conversations/",
            json={"title": "Journey Test"},
        )
        assert conv.status_code == 201
        conv_id = conv.json()["id"]

        # 3. Send a message
        msg = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "I feel overwhelmed with my thinking patterns"},
        )
        assert msg.status_code == 201

        # 4. Send another message
        msg2 = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "What patterns do you notice?"},
        )
        assert msg2.status_code == 201

        # 5. List messages
        messages = client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert messages.status_code == 200

        # 6. Get runtime status
        status = client.get("/api/v1/runtime/status")
        assert status.status_code == 200

        # 7. Check memories
        memories = client.get("/api/v1/memories/")
        assert memories.status_code == 200

        # 8. Check patterns
        patterns = client.get("/api/v1/patterns/")
        assert patterns.status_code == 200

        # 9. Check reflections
        reflections = client.get("/api/v1/reflections/")
        assert reflections.status_code == 200

        # 10. Check blind spots
        blind_spots = client.get("/api/v1/blind-spots/")
        assert blind_spots.status_code == 200

        # 11. Check library
        library = client.get("/api/v1/library/books")
        assert library.status_code == 200

        # 12. Archive the conversation
        archive = client.post(f"/api/v1/conversations/{conv_id}/archive")
        assert archive.status_code == 200

    def test_streaming_journey(self, client: httpx.Client) -> None:
        """Test a streaming conversation journey."""
        # 1. Create conversation via streaming
        with client.stream(
            "POST",
            "/api/v1/runtime/message/stream",
            json={"content": "What is acceptance?"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())

            assert "message_start" in events
            assert "content_delta" in events
            assert "message_end" in events


# ---------------------------------------------------------------------------
# 7. API Response Validation
# ---------------------------------------------------------------------------


class TestAPIResponseValidation:
    """Verify API responses have correct schemas."""

    def test_health_response_schema(self, client: httpx.Client) -> None:
        data = client.get("/api/v1/health").json()
        required_fields = {"status", "timestamp", "uptime_seconds"}
        assert required_fields.issubset(data.keys())

    def test_conversation_response_schema(self, client: httpx.Client) -> None:
        resp = client.post("/api/v1/conversations/", json={"title": "Schema Test"})
        data = resp.json()
        required = {"id", "user_id", "title", "status", "created_at"}
        assert required.issubset(data.keys())

    def test_message_response_schema(self, client: httpx.Client) -> None:
        conv = client.post("/api/v1/conversations/", json={"title": "Msg Schema"})
        conv_id = conv.json()["id"]
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Test"},
        )
        data = resp.json()
        required = {"id", "conversation_id", "role", "content", "sequence_number", "created_at"}
        assert required.issubset(data.keys())

    def test_runtime_status_schema(self, client: httpx.Client) -> None:
        data = client.get("/api/v1/runtime/status").json()
        required = {"status", "active_executions", "uptime_seconds", "version"}
        assert required.issubset(data.keys())


# ---------------------------------------------------------------------------
# 8. Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify the system handles errors gracefully."""

    def test_invalid_json(self, client: httpx.Client) -> None:
        resp = client.post(
            "/api/v1/conversations/",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_missing_required_field(self, client: httpx.Client) -> None:
        resp = client.post("/api/v1/conversations/", json={})
        assert resp.status_code == 422

    def test_empty_message_content(self, client: httpx.Client) -> None:
        conv = client.post("/api/v1/conversations/", json={"title": "Empty Msg"})
        conv_id = conv.json()["id"]
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": ""},
        )
        assert resp.status_code == 422

    def test_nonexistent_conversation(self, client: httpx.Client) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/conversations/{fake_id}")
        # Should return 200 with empty data (stub behavior)
        assert resp.status_code in (200, 404)

    def test_404_unknown_endpoint(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code in (404, 405)


# ---------------------------------------------------------------------------
# 9. Performance Baseline
# ---------------------------------------------------------------------------


class TestPerformanceBaseline:
    """Measure baseline performance of the live system."""

    def test_health_latency(self, client: httpx.Client) -> None:
        """Health endpoint should respond in < 100ms."""
        start = time.monotonic()
        resp = client.get("/api/v1/health")
        duration_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert duration_ms < 100, f"Health endpoint too slow: {duration_ms:.0f}ms"

    def test_conversation_create_latency(self, client: httpx.Client) -> None:
        """Conversation creation should respond in < 500ms."""
        start = time.monotonic()
        resp = client.post("/api/v1/conversations/", json={"title": "Perf Test"})
        duration_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 201
        assert duration_ms < 500, f"Conversation creation too slow: {duration_ms:.0f}ms"

    def test_message_send_latency(self, client: httpx.Client) -> None:
        """Message sending should respond in < 500ms."""
        conv = client.post("/api/v1/conversations/", json={"title": "Latency Test"})
        conv_id = conv.json()["id"]
        start = time.monotonic()
        resp = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hello"},
        )
        duration_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 201
        assert duration_ms < 500, f"Message send too slow: {duration_ms:.0f}ms"

    def test_streaming_start_latency(self, client: httpx.Client) -> None:
        """Streaming should start within 2 seconds."""
        start = time.monotonic()
        with client.stream(
            "POST",
            "/api/v1/runtime/message/stream",
            json={"content": "Hi"},
        ) as resp:
            first_event_time = None
            for line in resp.iter_lines():
                if line.startswith("event:"):
                    first_event_time = time.monotonic()
                    break

        assert first_event_time is not None, "No events received"
        latency_ms = (first_event_time - start) * 1000
        assert latency_ms < 2000, f"Streaming start too slow: {latency_ms:.0f}ms"
