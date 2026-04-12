"""Tests for regulatory API endpoints (impact, acknowledge, scoping)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

PROFILE = {
    "ai_use_cases": ["customer_chatbot"],
    "audience_types": ["customers"],
    "industry": "ecommerce",
    "jurisdictions": ["california", "colorado"],
}


async def _seed_updates(engine) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from scripts.seed_regulatory_updates import seed
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)
        await session.commit()


@pytest.mark.asyncio
async def test_impact_returns_personalized(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    for impact in data["impacts"]:
        assert impact["is_affected"] is True
        assert len(impact["reasons"]) > 0


@pytest.mark.asyncio
async def test_severity_filter(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact?severity=high", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    for impact in resp.json()["impacts"]:
        assert impact["impact_level"] == "high"


@pytest.mark.asyncio
async def test_acknowledge_endpoint(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    # Get an impact to acknowledge
    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    impacts = resp.json()["impacts"]
    assert len(impacts) > 0

    impact_id = impacts[0]["id"]
    ack_resp = await client.post(
        f"/v1/regulatory/impact/{impact_id}/acknowledge",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["acknowledged"] is True


@pytest.mark.asyncio
async def test_impact_scoped_to_customer(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    # Get impacts for first customer
    resp1 = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    impact_ids_1 = {i["id"] for i in resp1.json()["impacts"]}

    # Second customer with different profile
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "reg-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    await client.post("/v1/profile", json={
        "ai_use_cases": ["data_analysis"], "audience_types": ["employees"],
        "industry": "other", "jurisdictions": ["uk"],
    }, headers={"Authorization": f"Bearer {k2.json()['key']}"})

    resp2 = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    impact_ids_2 = {i["id"] for i in resp2.json()["impacts"]}

    # No overlap
    assert impact_ids_1.isdisjoint(impact_ids_2)
