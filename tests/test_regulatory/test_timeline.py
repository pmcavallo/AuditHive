"""Tests for the regulatory timeline endpoint."""

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
async def test_timeline_sorted_by_date(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/timeline?days_ahead=365", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    timeline = resp.json()["timeline"]
    dates = [t["date"] for t in timeline]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_timeline_filtered_to_customer(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    # UK-only customer
    c2 = await client.post("/v1/customers", json={"name": "UK", "email": "uk-timeline@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    await client.post("/v1/profile", json={
        "ai_use_cases": ["data_analysis"], "audience_types": ["employees"],
        "industry": "other", "jurisdictions": ["uk"],
    }, headers={"Authorization": f"Bearer {k2.json()['key']}"})

    resp = await client.get("/v1/regulatory/timeline?days_ahead=365", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    # UK customer should not see Colorado deadlines
    for item in resp.json()["timeline"]:
        assert "Colorado" not in item["regulation"]


@pytest.mark.asyncio
async def test_timeline_days_ahead_filter(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    # Very short window
    resp = await client.get("/v1/regulatory/timeline?days_ahead=1", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    short = resp.json()["timeline"]

    # Longer window
    resp2 = await client.get("/v1/regulatory/timeline?days_ahead=365", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    long = resp2.json()["timeline"]

    assert len(long) >= len(short)
