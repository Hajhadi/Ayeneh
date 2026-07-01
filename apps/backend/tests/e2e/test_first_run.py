"""Integration tests for first-run experience: wizard, diagnostics, products."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from ayeneh.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


# ── Wizard tests ──

class TestWizard:
    @pytest.mark.asyncio
    async def test_wizard_status(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/wizard/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_step" in data
        assert "steps" in data
        assert isinstance(data["steps"], list)

    @pytest.mark.asyncio
    async def test_wizard_status_has_steps(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/wizard/status")
        data = resp.json()
        assert len(data["steps"]) >= 4
        step_names = [s["step"] for s in data["steps"]]
        assert "select_profile" in step_names
        assert "configure_llm" in step_names

    @pytest.mark.asyncio
    async def test_validate_llm(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/wizard/validate-llm")
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data

    @pytest.mark.asyncio
    async def test_validate_embeddings(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/wizard/validate-embeddings")
        assert resp.status_code == 200
        assert "valid" in resp.json()

    @pytest.mark.asyncio
    async def test_validate_storage(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/wizard/validate-storage")
        assert resp.status_code == 200
        assert "valid" in resp.json()

    @pytest.mark.asyncio
    async def test_full_health_check(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/wizard/run-full-check")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
        assert "all_healthy" in data
        assert "llm" in data["checks"]
        assert "storage" in data["checks"]


# ── Diagnostics tests ──

class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_diagnostics_endpoint(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_diagnostics_metrics(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/diagnostics/metrics")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_diagnostics_has_all_checks(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/diagnostics")
        data = resp.json()
        checks = data["checks"]
        assert "llm" in checks
        assert "database" in checks
        assert "products" in checks
        assert "goals" in checks


# ── Products tests ──

class TestProducts:
    @pytest.mark.asyncio
    async def test_list_products(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/products/")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_product(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/products/ayeneh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "ayeneh"
        assert data["name"] == "Ayeneh"

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/products/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_product_metrics(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/products/metrics/summary")
        assert resp.status_code == 200


# ── Full first-run journey test ──

class TestFirstRunJourney:
    @pytest.mark.asyncio
    async def test_complete_journey(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/wizard/status")
        assert resp.status_code == 200

        resp = await client.post("/api/v1/wizard/validate-llm")
        assert resp.status_code == 200

        resp = await client.post("/api/v1/wizard/validate-embeddings")
        assert resp.status_code == 200

        resp = await client.post("/api/v1/wizard/validate-storage")
        assert resp.status_code == 200

        resp = await client.post("/api/v1/wizard/run-full-check")
        assert resp.status_code == 200

        resp = await client.get("/api/v1/products/")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

        resp = await client.get("/api/v1/diagnostics")
        assert resp.status_code == 200

        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
