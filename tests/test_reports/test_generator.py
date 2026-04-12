"""Tests for the report generator and API endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest_helpers import seed_regulatory_mappings

PROFILE = {
    "ai_use_cases": ["customer_chatbot"],
    "audience_types": ["customers"],
    "industry": "ecommerce",
    "jurisdictions": ["california"],
}


@pytest.mark.asyncio
async def test_generate_report(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    resp = await client.post(
        "/v1/reports/generate",
        json={"period_days": 7, "include_examiner_simulation": True},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "report_id" in data
    assert data["download_url"].startswith("/v1/reports/")


@pytest.mark.asyncio
async def test_download_report_returns_html(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    gen = await client.post(
        "/v1/reports/generate",
        json={"period_days": 7},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    report_id = gen.json()["report_id"]

    resp = await client.get(
        f"/v1/reports/{report_id}/download",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    assert "AuditHive" in resp.text
    assert "Governance Report" in resp.text


@pytest.mark.asyncio
async def test_report_contains_key_sections(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    gen = await client.post(
        "/v1/reports/generate", json={"period_days": 7},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.get(
        f"/v1/reports/{gen.json()['report_id']}/download",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    html = resp.text
    assert "Coverage Score" in html
    assert "Controls Assessment" in html
    assert "Audit Trail Summary" in html


@pytest.mark.asyncio
async def test_report_saved_to_database(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    await client.post(
        "/v1/reports/generate", json={"period_days": 7},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.get("/v1/reports", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    assert len(resp.json()["reports"]) >= 1


@pytest.mark.asyncio
async def test_report_list_scoped_to_customer(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    await client.post("/v1/reports/generate", json={"period_days": 7}, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "reports-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    resp = await client.get("/v1/reports", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    assert len(resp.json()["reports"]) == 0
