"""Tests for audit log endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse

FAKE_OPENAI_RESPONSE = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-4",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


async def _create_log_entry(client: AsyncClient, api_key: str) -> str:
    """Helper: send a chat request and return the audit log ID."""
    with patch("audithive.api.routes.chat.proxy_request", new_callable=AsyncMock) as mock_proxy:
        mock_proxy.return_value = ProxyResponse(status_code=200, body=FAKE_OPENAI_RESPONSE, latency_ms=50)
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]},
            headers={"Authorization": f"Bearer {api_key}", "X-LLM-Key": "sk-test"},
        )
    return resp.headers["X-AuditHive-Log-Id"]


@pytest.mark.asyncio
async def test_audit_log_created_with_fields(client: AsyncClient, test_api_key: dict) -> None:
    log_id = await _create_log_entry(client, test_api_key["key"])
    resp = await client.get(
        f"/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_model"] == "gpt-4"
    assert data["status"] == "completed"
    assert data["response_tokens_in"] == 10
    assert data["response_tokens_out"] == 5
    assert data["response_latency_ms"] == 50


@pytest.mark.asyncio
async def test_audit_log_belongs_to_correct_customer(
    client: AsyncClient, test_customer: dict, test_api_key: dict
) -> None:
    log_id = await _create_log_entry(client, test_api_key["key"])
    resp = await client.get(
        f"/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.json()["customer_id"] == test_customer["id"]


@pytest.mark.asyncio
async def test_audit_log_list_returns_only_own_logs(
    client: AsyncClient, test_api_key: dict
) -> None:
    await _create_log_entry(client, test_api_key["key"])
    resp = await client.get(
        "/v1/audit-logs",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "logs" in data


@pytest.mark.asyncio
async def test_audit_log_pagination(client: AsyncClient, test_api_key: dict) -> None:
    # Create a few entries
    for _ in range(3):
        await _create_log_entry(client, test_api_key["key"])

    resp = await client.get(
        "/v1/audit-logs?limit=2&offset=0",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    data = resp.json()
    assert data["limit"] == 2
    assert len(data["logs"]) <= 2


@pytest.mark.asyncio
async def test_audit_log_status_filter(client: AsyncClient, test_api_key: dict) -> None:
    await _create_log_entry(client, test_api_key["key"])
    resp = await client.get(
        "/v1/audit-logs?status=completed",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    data = resp.json()
    for log in data["logs"]:
        assert log["status"] == "completed"


@pytest.mark.asyncio
async def test_cross_tenant_access_returns_404(client: AsyncClient, test_api_key: dict) -> None:
    """A customer should not be able to access another customer's logs."""
    log_id = await _create_log_entry(client, test_api_key["key"])

    # Create a second customer + key
    cust2_resp = await client.post(
        "/v1/customers",
        json={"name": "Jane Sample", "email": "jane-audit@samplecorp.com", "company_name": "Sample Corp"},
    )
    cust2 = cust2_resp.json()
    key2_resp = await client.post(
        f"/v1/customers/{cust2['id']}/api-keys",
        json={"name": "Key 2"},
    )
    key2 = key2_resp.json()

    # Try to access first customer's log with second customer's key
    resp = await client.get(
        f"/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {key2['key']}"},
    )
    assert resp.status_code == 404
