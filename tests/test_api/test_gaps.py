"""Tests for the gap detector endpoint."""

import pytest
from httpx import AsyncClient

from tests.conftest_helpers import seed_regulatory_mappings


@pytest.mark.asyncio
async def test_gap_detected_action_mismatch(engine, client: AsyncClient, test_api_key: dict) -> None:
    """If some PII types block while others flag, detect the config inconsistency."""
    await seed_regulatory_mappings(engine)

    # Create template-format policy: SSN=block but email=flag (inconsistency)
    await client.post(
        "/v1/policies",
        json={"name": "Gap Test", "config": {
            "pre_call": {
                "pii_detection": {
                    "enabled": True,
                    "types": {"ssn": {"enabled": True, "action": "block"}, "email": {"enabled": True, "action": "flag"}},
                },
                "injection_detection": {"enabled": False},
                "content_filter": {"enabled": False},
                "scope_enforcement": {"enabled": False},
            }
        }},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )

    resp = await client.get("/v1/assessment/gaps", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    assert resp.status_code == 200
    data = resp.json()
    action_gaps = [g for g in data["gaps"] if g["gap_type"] == "action_mismatch"]
    assert len(action_gaps) >= 1
    assert "email" in action_gaps[0]["description"]


@pytest.mark.asyncio
async def test_gap_detected_weakened_template(engine, client: AsyncClient, test_api_key: dict) -> None:
    """If a template control was weakened from block to flag, detect the gap."""
    await seed_regulatory_mappings(engine)

    # Seed templates
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from audithive.policy.templates.loader import load_templates_from_definitions
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await load_templates_from_definitions(session)
        await session.commit()

    # Apply chatbot template then weaken injection detection
    await client.post(
        "/v1/templates/customer_chatbot/apply",
        json={
            "name": "Weakened Policy",
            "customizations": {
                "pre_call": {"injection_detection": {"action": "flag"}}
            }
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )

    resp = await client.get("/v1/assessment/gaps", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    weak_gaps = [g for g in data["gaps"] if g["gap_type"] == "weakened_template"]
    assert len(weak_gaps) >= 1


@pytest.mark.asyncio
async def test_no_gaps_when_policy_matches(client: AsyncClient, test_api_key: dict) -> None:
    # Create simple flat policy (no template, no mismatch)
    await client.post(
        "/v1/policies",
        json={"name": "Clean Policy", "config": {
            "pii_detection": {"enabled": True, "types": ["ssn"], "action": "block"},
            "injection_detection": {"enabled": True, "action": "block"},
            "content_filter": {"enabled": False},
            "scope_enforcement": {"enabled": False},
        }},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    resp = await client.get("/v1/assessment/gaps", headers={"Authorization": f"Bearer {test_api_key['key']}"})
    data = resp.json()
    assert data["gap_count"] == 0
    assert data["overall_alignment"] == "full"


@pytest.mark.asyncio
async def test_gaps_scoped_to_customer(client: AsyncClient, test_api_key: dict) -> None:
    c2 = await client.post("/v1/customers", json={"name": "Other", "email": "gaps-scope@test.com"})
    k2 = await client.post(f"/v1/customers/{c2.json()['id']}/api-keys", json={"name": "K"})
    resp = await client.get("/v1/assessment/gaps", headers={"Authorization": f"Bearer {k2.json()['key']}"})
    assert resp.status_code == 200
    assert resp.json()["overall_alignment"] == "none"
