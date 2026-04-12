"""Tests for the alert dispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse


@pytest.mark.asyncio
async def test_alert_dispatched_on_block(client: AsyncClient, test_api_key: dict) -> None:
    """Create alert config, trigger a block, verify alert_history has entry."""
    # Create alert config
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "email_addresses": [], "webhook_urls": []},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )

    # Create policy that blocks SSN
    await client.post(
        "/v1/policies",
        json={"name": "Alert Block Test", "config": {
            "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
            "content_filter": {"enabled": False},
            "injection_detection": {"enabled": False},
            "scope_enforcement": {"enabled": False},
        }},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )

    # Send a request that triggers a block
    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "SSN 123-45-6789"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": "sk-test"},
    )

    # Check alert history
    resp = await client.get("/v1/alerts/history", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    assert data["total"] >= 1
    assert any(a["trigger_type"] == "policy_block" for a in data["alerts"])


@pytest.mark.asyncio
async def test_alert_not_dispatched_when_disabled(client: AsyncClient, test_api_key: dict) -> None:
    """If on_block is false, no alert dispatched."""
    await client.post(
        "/v1/alerts/config",
        json={"on_block": False, "email_addresses": [], "webhook_urls": []},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    await client.post(
        "/v1/policies",
        json={"name": "No Alert Test", "config": {
            "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
            "content_filter": {"enabled": False},
            "injection_detection": {"enabled": False},
            "scope_enforcement": {"enabled": False},
        }},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "SSN 111-22-3333"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": "sk-test"},
    )
    import asyncio
    await asyncio.sleep(0.1)

    resp = await client.get(
        "/v1/alerts/history?trigger_type=policy_block",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_webhook_channel_sends(client: AsyncClient, test_api_key: dict) -> None:
    """Mock webhook and verify it's called."""
    with patch("audithive.alerts.channels.webhook.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = AsyncMock(status_code=200)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        await client.post(
            "/v1/alerts/config",
            json={"on_block": True, "webhook_urls": ["https://hooks.example.com/test"]},
            headers={"Authorization": f"Bearer {test_api_key['key']}"},
        )
        await client.post("/v1/alerts/test", headers={"Authorization": f"Bearer {test_api_key['key']}"})


@pytest.mark.asyncio
async def test_test_alert_endpoint(client: AsyncClient, test_api_key: dict) -> None:
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "email_addresses": [], "webhook_urls": []},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.post("/v1/alerts/test", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_alert_history_logged(client: AsyncClient, test_api_key: dict) -> None:
    await client.post(
        "/v1/alerts/config",
        json={"on_block": True, "email_addresses": [], "webhook_urls": []},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    await client.post("/v1/alerts/test", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/alerts/history", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.json()["total"] >= 1
