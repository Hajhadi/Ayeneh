"""E2E test configuration for Playwright."""

from __future__ import annotations

import pytest

from httpx import ASGITransport, AsyncClient

from ayeneh.main import app


@pytest.fixture(scope="session")
def base_url() -> str:
    return "http://localhost:8000"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
