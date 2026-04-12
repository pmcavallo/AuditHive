"""Tests for data lifecycle endpoints (export and delete)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse

FAKE_RESPONSE = {
    "choices": [{"message": {"role": "assistant", "content": "Hi"}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
}


@pytest.mark.asyncio
async def test_delete_without_confirm_returns_400(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.request(
        "DELETE", "/v1/account",
        json={"confirm": False},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_with_confirm_deletes_all(client: AsyncClient, test_customer: dict, test_api_key: dict) -> None:
    # Create some data first
    await client.post("/v1/profile", json={
        "ai_use_cases": ["customer_chatbot"], "audience_types": ["customers"],
        "industry": "ecommerce", "jurisdictions": ["california"],
    }, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.request(
        "DELETE", "/v1/account",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert "customers" in data["tables_purged"]


@pytest.mark.asyncio
@patch("audithive.api.routes.chat.proxy_request")
async def test_export_returns_all_data(
    mock_proxy: AsyncMock, client: AsyncClient, test_api_key: dict
) -> None:
    mock_proxy.return_value = ProxyResponse(status_code=200, body=FAKE_RESPONSE, latency_ms=50)

    # Create some data
    await client.post("/v1/profile", json={
        "ai_use_cases": ["customer_chatbot"], "audience_types": ["customers"],
        "industry": "ecommerce", "jurisdictions": ["california"],
    }, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": "sk-test"},
    )

    resp = await client.get("/v1/account/export", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "customer" in data
    assert "profile" in data
    assert "audit_logs" in data
    assert len(data["audit_logs"]) >= 1


@pytest.mark.asyncio
async def test_export_scoped_to_customer(client: AsyncClient, test_api_key: dict) -> None:
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "export-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})

    resp = await client.get("/v1/account/export", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["audit_logs"]) == 0
    assert data["profile"] is None


@pytest.mark.asyncio
async def test_deleted_data_not_accessible(client: AsyncClient) -> None:
    # Create a fresh customer
    c = await client.post("/v1/customers", json={"name": "Delete Me", "email": "delete-test@test.com"})
    k = await client.post(f"/v1/customers/{c.json()['id']}/api-keys", json={"name": "K"})
    key = k.json()["key"]

    # Delete
    await client.request("DELETE", "/v1/account", json={"confirm": True},
                         headers={"Authorization": f"Bearer {key}"})

    # Key should no longer work
    resp = await client.get("/v1/health", headers={"Authorization": f"Bearer {key}"})
    # Might be 401 or health is public — check auth endpoint
    resp2 = await client.get("/v1/audit-logs", headers={"Authorization": f"Bearer {key}"})
    assert resp2.status_code == 401
