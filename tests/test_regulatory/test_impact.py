"""Tests for the regulatory impact assessment engine."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest_helpers import seed_regulatory_mappings

PROFILE = {
    "ai_use_cases": ["customer_chatbot"],
    "audience_types": ["customers"],
    "industry": "ecommerce",
    "jurisdictions": ["california", "colorado"],
}

PROFILE_NO_MATCH = {
    "ai_use_cases": ["data_analysis"],
    "audience_types": ["employees"],
    "industry": "other",
    "jurisdictions": ["uk"],
}


async def _seed_updates(engine) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from scripts.seed_regulatory_updates import seed as seed_updates
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed_updates(session)
        await session.commit()


@pytest.mark.asyncio
async def test_affected_customer_identified(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_affecting"] > 0


@pytest.mark.asyncio
async def test_non_affected_customer_excluded(engine, client: AsyncClient, test_api_key: dict) -> None:
    """A customer with non-matching jurisdictions should have fewer impacts."""
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE_NO_MATCH, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    # UK customer should see EU regulations but not US state ones
    jurisdictions = [i["regulatory_update"]["jurisdiction"] for i in data["impacts"]]
    assert "colorado" not in jurisdictions
    assert "california" not in jurisdictions


@pytest.mark.asyncio
async def test_us_federal_affects_us_customers(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    jurisdictions = [i["regulatory_update"]["jurisdiction"] for i in resp.json()["impacts"]]
    assert "us_federal" in jurisdictions


@pytest.mark.asyncio
async def test_impact_level_computed(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    for impact in resp.json()["impacts"]:
        assert impact["impact_level"] in ("critical", "high", "medium", "low", "none")


@pytest.mark.asyncio
async def test_controls_missing_vs_in_place(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    for impact in resp.json()["impacts"]:
        # audit_logging and monitoring should be in_place (always on)
        in_place_controls = [c["control"] for c in impact["controls_in_place"]]
        if "audit_logging" in [c["control"] for c in impact["controls_missing"]] + in_place_controls:
            assert "audit_logging" in in_place_controls


@pytest.mark.asyncio
async def test_impact_assessment_saved(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_updates(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    for impact in resp.json()["impacts"]:
        assert "id" in impact


@pytest.mark.asyncio
async def test_wildcard_industry_matching(engine, client: AsyncClient, test_api_key: dict) -> None:
    """Regulations with industry='any' should affect all industries."""
    await _seed_updates(engine)
    # Ecommerce is not listed explicitly in any update, but 'any' should match
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/regulatory/impact", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.json()["summary"]["total_affecting"] >= 3
