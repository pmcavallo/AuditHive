"""Tests for customer and API key management."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_customer(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/customers",
        json={
            "name": "Jane Sample",
            "email": "jane@samplecorp.com",
            "company_name": "Sample Corp",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Jane Sample"
    assert data["email"] == "jane@samplecorp.com"
    assert data["plan"] == "free"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_customer_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "name": "Duplicate Person",
        "email": "dup@testcompany.com",
    }
    resp1 = await client.post("/v1/customers", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/v1/customers", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_create_api_key_returns_full_key(
    client: AsyncClient, test_customer: dict
) -> None:
    resp = await client.post(
        f"/v1/customers/{test_customer['id']}/api-keys",
        json={"name": "My Key"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"].startswith("ah-")
    assert len(data["key"]) > 20
    assert data["key_prefix"] == data["key"][3:11]
    assert data["name"] == "My Key"
    assert data["warning"] == "Save this key now. It will not be shown again."


@pytest.mark.asyncio
async def test_list_api_keys_no_full_key(
    client: AsyncClient, test_customer: dict, test_api_key: dict
) -> None:
    resp = await client.get(f"/v1/customers/{test_customer['id']}/api-keys")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["keys"]) >= 1
    for key_info in data["keys"]:
        assert "key" not in key_info  # Full key must never be returned
        assert "key_prefix" in key_info


@pytest.mark.asyncio
async def test_deactivate_api_key_makes_unusable(
    client: AsyncClient, test_customer: dict
) -> None:
    # Create a key
    create_resp = await client.post(
        f"/v1/customers/{test_customer['id']}/api-keys",
        json={"name": "Deactivate Me"},
    )
    key_data = create_resp.json()

    # Verify it works
    health_resp = await client.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {key_data['key']}"},
    )
    assert health_resp.status_code == 200

    # Deactivate it
    del_resp = await client.delete(
        f"/v1/customers/{test_customer['id']}/api-keys/{key_data['id']}"
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deactivated"

    # Verify it no longer works
    health_resp2 = await client.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {key_data['key']}"},
    )
    assert health_resp2.status_code == 401


@pytest.mark.asyncio
async def test_expired_api_key_returns_401(
    client: AsyncClient, test_customer: dict, db_session
) -> None:
    """An expired key should be rejected even if the hash matches."""
    import uuid as uuid_mod
    from datetime import datetime, timedelta, timezone

    from audithive.core.security import generate_api_key
    from audithive.db.models import ApiKey

    full_key, key_hash, key_prefix = generate_api_key()
    expired_key = ApiKey(
        customer_id=uuid_mod.UUID(test_customer["id"]),
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="Already Expired",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(expired_key)
    await db_session.commit()

    resp = await client.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {full_key}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_key_prefix_lookup(
    client: AsyncClient, test_customer: dict, test_api_key: dict
) -> None:
    """The key prefix in the response matches the key's characters."""
    key = test_api_key["key"]
    prefix = test_api_key["key_prefix"]
    # Prefix should be chars 3..11 of the full key (after "ah-")
    assert key[3:11] == prefix
