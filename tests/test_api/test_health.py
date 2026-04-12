"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_public_health_check(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_authenticated_health_no_key(client: AsyncClient) -> None:
    resp = await client.get("/v1/health")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_health_invalid_key(client: AsyncClient) -> None:
    resp = await client.get(
        "/v1/health",
        headers={"Authorization": "Bearer ah-invalid00000000000000000000000000000000000000000000"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_health_valid_key(
    client: AsyncClient, test_customer: dict, test_api_key: dict
) -> None:
    resp = await client.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["customer_id"] == test_customer["id"]
