"""Tests for alert configuration CRUD."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_alert_config(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "on_flag": True, "email_addresses": ["ops@test.com"], "webhook_urls": []},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["on_block"] is True
    assert data["on_flag"] is True
    assert "ops@test.com" in data["email_addresses"]


@pytest.mark.asyncio
async def test_update_alert_config(client: AsyncClient, test_api_key: dict) -> None:
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "email_addresses": ["first@test.com"]},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.post(
        "/v1/alerts/config",
        json={"on_block": False, "email_addresses": ["second@test.com"]},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.json()["on_block"] is False
    assert "second@test.com" in resp.json()["email_addresses"]


@pytest.mark.asyncio
async def test_get_alert_config(client: AsyncClient, test_api_key: dict) -> None:
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "webhook_urls": ["https://hooks.example.com"]},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.get("/v1/alerts/config", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    assert resp.json()["on_block"] is True


@pytest.mark.asyncio
async def test_config_scoped_to_customer(client: AsyncClient, test_api_key: dict) -> None:
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "email_addresses": ["mine@test.com"]},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "alerts-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    resp = await client.get("/v1/alerts/config", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    assert resp.json()["enabled"] is False  # No config = default disabled
