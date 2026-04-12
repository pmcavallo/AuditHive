"""Tests for the Four Questions framework endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_four_questions_returns_maturity(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.post(
        "/v1/assessment/four-questions",
        json={
            "purpose": "Customer support chatbot",
            "working": "Weekly review of flagged interactions",
            "failure": "Alerts to ops team",
            "accountability": "Sarah Chen, VP Ops",
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["maturity_score"] >= 1
    assert data["maturity_level"] in ("mature", "developing", "immature", "ungoverned")


@pytest.mark.asyncio
async def test_four_questions_detects_gap(client: AsyncClient, test_api_key: dict) -> None:
    """Failure answer describes alerts but no alerting is configured — gap."""
    resp = await client.post(
        "/v1/assessment/four-questions",
        json={
            "purpose": "Chatbot",
            "working": "We review logs",
            "failure": "Violations trigger email alerts",
            "accountability": "John Doe",
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    data = resp.json()
    failure_q = data["questions"]["failure"]
    assert failure_q["gap"] is not None
    assert "alert" in failure_q["gap"].lower()


@pytest.mark.asyncio
async def test_maturity_level_correct(client: AsyncClient, test_api_key: dict) -> None:
    # All 4 answered
    r1 = await client.post(
        "/v1/assessment/four-questions",
        json={"purpose": "A", "working": "B", "failure": "C", "accountability": "D"},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert r1.json()["maturity_score"] >= 3

    # Only 1 answered
    r2 = await client.post(
        "/v1/assessment/four-questions",
        json={"purpose": "A"},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert r2.json()["maturity_score"] <= 2


@pytest.mark.asyncio
async def test_partial_answers(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.post(
        "/v1/assessment/four-questions",
        json={"purpose": "Chatbot", "accountability": "Jane"},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    data = resp.json()
    assert data["questions"]["purpose"]["answered"] is True
    assert data["questions"]["working"]["answered"] is False
    assert data["questions"]["accountability"]["answered"] is True
