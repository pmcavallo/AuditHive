"""Tests for the governance assessment endpoint."""

import pytest
from httpx import AsyncClient

from tests.conftest_helpers import seed_regulatory_mappings

PROFILE = {
    "ai_use_cases": ["customer_chatbot"],
    "audience_types": ["customers"],
    "industry": "ecommerce",
    "jurisdictions": ["california", "colorado"],
}


@pytest.mark.asyncio
async def test_assessment_returns_regulations(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["applicable_regulations"]) > 0
    reg_names = [r["regulation"] for r in data["applicable_regulations"]]
    assert any("Colorado" in n for n in reg_names)


@pytest.mark.asyncio
async def test_assessment_identifies_missing_controls(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    assert len(data["missing_controls"]) > 0
    missing_names = [m["control"] for m in data["missing_controls"]]
    assert "ai_disclosure" in missing_names  # no policy configured


@pytest.mark.asyncio
async def test_coverage_score_computed(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    assert isinstance(data["coverage_score"], float)
    # With only audit_logging and monitoring auto-covered, score < 100
    assert data["coverage_score"] < 100


@pytest.mark.asyncio
async def test_assessment_no_profile_returns_400(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_assessment_with_policy_improves_coverage(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})

    # No policy — baseline score
    r1 = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    baseline = r1.json()["coverage_score"]

    # Add a policy with PII and injection enabled
    await client.post(
        "/v1/policies",
        json={"name": "Coverage Test", "config": {
            "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
            "injection_detection": {"enabled": True, "action": "block"},
            "content_filter": {"enabled": False},
            "scope_enforcement": {"enabled": False},
        }},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    r2 = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    improved = r2.json()["coverage_score"]
    assert improved >= baseline


@pytest.mark.asyncio
async def test_examiner_questions_generated(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    assert len(data["examiner_questions"]) > 0


@pytest.mark.asyncio
async def test_assessment_saved_to_database(engine, client: AsyncClient, test_api_key: dict) -> None:
    await seed_regulatory_mappings(engine)
    await client.post("/v1/profile", json=PROFILE, headers={"Authorization": f"Bearer {test_api_key['key']}"})
    resp = await client.get("/v1/assessment", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert "assessment_id" in resp.json()
