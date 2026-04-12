"""Tests for regulatory update CRUD and auto-assessment."""

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
    from scripts.seed_regulatory_updates import seed as seed_updates
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed_updates(session)
        await session.commit()


@pytest.mark.asyncio
async def test_seed_loads_all_updates(engine) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from scripts.seed_regulatory_updates import seed, UPDATES
    from audithive.db.models import RegulatoryUpdate

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        count = await seed(session)
        await session.commit()
    assert count == len(UPDATES)


@pytest.mark.asyncio
async def test_list_updates(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    resp = await client.get("/v1/regulatory/updates", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    assert len(resp.json()["updates"]) >= 7


@pytest.mark.asyncio
async def test_create_update_triggers_assessment(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.post("/v1/regulatory/updates", json={
        "title": "Test Regulation",
        "summary": "A test regulatory update.",
        "update_type": "new_law",
        "jurisdiction": "california",
        "industries": ["any"],
        "use_cases": ["customer_chatbot"],
        "audiences": ["customers"],
        "affected_controls": ["ai_disclosure"],
        "severity": "high",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["affected_customers"] >= 1


@pytest.mark.asyncio
async def test_create_update_does_not_assess_unaffected(engine, client: AsyncClient, test_api_key: dict) -> None:
    # Create a customer with UK jurisdiction
    c2 = await client.post("/v1/customers", json={"name": "UK Co", "email": "uk-reg@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    await client.post("/v1/profile", json={
        "ai_use_cases": ["data_analysis"], "audience_types": ["employees"],
        "industry": "other", "jurisdictions": ["uk"],
    }, headers={"Authorization": f"Bearer {k2.json()['key']}"})

    # Create a California-only regulation
    resp = await client.post("/v1/regulatory/updates", json={
        "title": "CA Only Reg",
        "summary": "Only affects California.",
        "update_type": "new_law",
        "jurisdiction": "california",
        "industries": ["any"],
        "use_cases": ["customer_chatbot"],
        "audiences": ["customers"],
        "severity": "high",
    })
    # UK customer should not be affected
    impact_resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    ca_impacts = [i for i in impact_resp.json()["impacts"] if i["regulatory_update"]["title"] == "CA Only Reg"]
    assert len(ca_impacts) == 0
