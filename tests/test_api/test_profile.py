"""Tests for customer profile endpoints."""

import pytest
from httpx import AsyncClient


PROFILE_DATA = {
    "ai_use_cases": ["customer_chatbot", "email_automation"],
    "audience_types": ["customers"],
    "industry": "ecommerce",
    "jurisdictions": ["california", "colorado"],
}


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.post(
        "/v1/profile",
        json=PROFILE_DATA,
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["industry"] == "ecommerce"
    assert "customer_chatbot" in data["ai_use_cases"]
    assert "profile_id" in data


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, test_api_key: dict) -> None:
    await client.post("/v1/profile", json=PROFILE_DATA, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/profile", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    assert resp.json()["industry"] == "ecommerce"


@pytest.mark.asyncio
async def test_update_profile_overwrites(client: AsyncClient, test_api_key: dict) -> None:
    await client.post("/v1/profile", json=PROFILE_DATA, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    updated = {**PROFILE_DATA, "industry": "financial_services"}
    resp = await client.post("/v1/profile", json=updated, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 201
    assert resp.json()["industry"] == "financial_services"


@pytest.mark.asyncio
async def test_profile_scoped_to_customer(client: AsyncClient, test_api_key: dict) -> None:
    await client.post("/v1/profile", json=PROFILE_DATA, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    # Second customer
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "profile-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    resp = await client.get("/v1/profile", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    assert resp.status_code == 404
