"""Tests for the audit log stats endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse

FAKE_OPENAI_RESPONSE = {
    "id": "chatcmpl-stats",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-4",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


async def _send_chat(client: AsyncClient, api_key: str, content: str = "Hello") -> None:
    with patch("audithive.api.routes.chat.proxy_request", new_callable=AsyncMock) as m:
        m.return_value = ProxyResponse(status_code=200, body=FAKE_OPENAI_RESPONSE, latency_ms=50)
        await client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4", "messages": [{"role": "user", "content": content}]},
            headers={"Authorization": f"Bearer {api_key}", "X-LLM-Key": "sk-test"},
        )


@pytest.mark.asyncio
async def test_stats_returns_correct_counts(client: AsyncClient, test_api_key: dict) -> None:
    # Create a policy that blocks SSN
    await client.post(
        "/v1/policies",
        json={
            "name": "Stats Block SSN",
            "config": {
                "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
                "content_filter": {"enabled": False},
                "injection_detection": {"enabled": False},
                "scope_enforcement": {"enabled": False},
            },
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )

    # Send clean request (completed)
    await _send_chat(client, test_api_key["key"], "What is the weather?")
    # Send PII request (blocked)
    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "SSN 123-45-6789"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": "sk-test"},
    )

    resp = await client.get(
        "/v1/audit-logs/stats",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] >= 2
    assert data["total_blocked"] >= 1
    assert data["total_completed"] >= 1
    assert data["active_policies"] >= 1


@pytest.mark.asyncio
async def test_stats_calls_by_day(client: AsyncClient, test_api_key: dict) -> None:
    await _send_chat(client, test_api_key["key"])
    resp = await client.get(
        "/v1/audit-logs/stats?days=7",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    data = resp.json()
    assert isinstance(data["calls_by_day"], list)
    if data["calls_by_day"]:
        day = data["calls_by_day"][0]
        assert "date" in day
        assert "total" in day
        assert "violations" in day


@pytest.mark.asyncio
async def test_stats_recent_violations_only_violations(client: AsyncClient, test_api_key: dict) -> None:
    # Create blocking policy
    await client.post(
        "/v1/policies",
        json={
            "name": "Stats Violation Only",
            "config": {
                "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
                "content_filter": {"enabled": False},
                "injection_detection": {"enabled": False},
                "scope_enforcement": {"enabled": False},
            },
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    # Blocked request
    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "SSN 111-22-3333"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": "sk-test"},
    )
    resp = await client.get(
        "/v1/audit-logs/stats",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    for v in resp.json()["recent_violations"]:
        assert v["status"] in ("blocked", "flagged")


@pytest.mark.asyncio
async def test_stats_scoped_to_customer(client: AsyncClient, test_api_key: dict) -> None:
    # Create second customer
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "other-stats@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    # Send a request under first customer
    await _send_chat(client, test_api_key["key"])
    # Stats for second customer should have 0 calls
    resp = await client.get(
        "/v1/audit-logs/stats",
        headers={"Authorization": f"Bearer {k2.json()['key']}"},
    )
    assert resp.json()["total_calls"] == 0


@pytest.mark.asyncio
async def test_stats_empty_state(client: AsyncClient) -> None:
    # Fresh customer with no logs
    c = await client.post("/v1/customers", json={"name": "Empty", "email": "empty-stats@test.com"})
    k = await client.post(f"/v1/customers/{c.json()['id']}/api-keys", json={"name": "K"})
    resp = await client.get(
        "/v1/audit-logs/stats",
        headers={"Authorization": f"Bearer {k.json()['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 0
    assert data["total_blocked"] == 0
    assert data["total_flagged"] == 0
    assert data["calls_by_day"] == []
    assert data["recent_violations"] == []
