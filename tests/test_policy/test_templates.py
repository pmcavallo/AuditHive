"""Tests for policy templates: loader, API, and integration with chat."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse

FAKE_OPENAI_RESPONSE = {
    "id": "chatcmpl-tmpl",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-4",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


# ── Helper: seed templates via the loader ──────────────────────────


async def _seed_templates(engine) -> None:
    """Load template definitions into the test database."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from audithive.policy.templates.loader import load_templates_from_definitions

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await load_templates_from_definitions(session)
        await session.commit()


# ── Template Loader Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_templates_loaded_from_json(engine, db_session) -> None:
    from audithive.policy.templates.loader import load_templates_from_definitions

    templates = await load_templates_from_definitions(db_session)
    await db_session.commit()
    assert len(templates) == 3
    ids = {t.id for t in templates}
    assert "customer_chatbot" in ids
    assert "document_generation" in ids
    assert "email_automation" in ids


@pytest.mark.asyncio
async def test_loader_is_idempotent(engine, db_session) -> None:
    from audithive.policy.templates.loader import load_templates_from_definitions

    first = await load_templates_from_definitions(db_session)
    await db_session.commit()
    second = await load_templates_from_definitions(db_session)
    await db_session.commit()
    assert len(first) == len(second)


@pytest.mark.asyncio
async def test_higher_version_updates(engine, db_session) -> None:
    from sqlalchemy import select

    from audithive.db.models import PolicyTemplate
    from audithive.policy.templates.loader import load_templates_from_definitions

    await load_templates_from_definitions(db_session)
    await db_session.commit()

    # Manually bump the version to simulate an outdated row
    result = await db_session.execute(
        select(PolicyTemplate).where(PolicyTemplate.id == "customer_chatbot")
    )
    tmpl = result.scalar_one()
    tmpl.version = 0  # force it below the JSON's version=1
    await db_session.commit()

    # Re-load — should update
    await load_templates_from_definitions(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(PolicyTemplate).where(PolicyTemplate.id == "customer_chatbot")
    )
    tmpl = result.scalar_one()
    assert tmpl.version == 1


@pytest.mark.asyncio
async def test_template_config_matches_json(engine, db_session) -> None:
    from audithive.policy.templates.loader import load_templates_from_definitions

    templates = await load_templates_from_definitions(db_session)
    await db_session.commit()
    chatbot = next(t for t in templates if t.id == "customer_chatbot")
    assert "pre_call" in chatbot.config
    assert "post_call" in chatbot.config
    assert chatbot.config["risk_level"] == "high"


# ── Template API Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_templates(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.get(
        "/v1/templates",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["templates"]) == 3


@pytest.mark.asyncio
async def test_list_templates_no_full_config(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.get(
        "/v1/templates",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    for t in resp.json()["templates"]:
        assert "config" not in t  # list view has no full config
        assert "risk_level" in t
        assert "regulatory_grounding" in t


@pytest.mark.asyncio
async def test_get_template_detail(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.get(
        "/v1/templates/customer_chatbot",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "customer_chatbot"
    assert "config" in data
    assert "pre_call" in data["config"]


@pytest.mark.asyncio
async def test_get_nonexistent_template(client: AsyncClient, test_api_key: dict) -> None:
    resp = await client.get(
        "/v1/templates/nonexistent",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_apply_template_defaults(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.post(
        "/v1/templates/customer_chatbot/apply",
        json={"name": "My Chatbot Policy"},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["template_id"] == "customer_chatbot"
    assert data["name"] == "My Chatbot Policy"
    assert "pre_call" in data["config"]
    assert data["message"] == "Policy created from template. Active on your next API call."


@pytest.mark.asyncio
async def test_apply_template_with_customizations(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.post(
        "/v1/templates/customer_chatbot/apply",
        json={
            "name": "Custom Chatbot",
            "customizations": {
                "pre_call": {
                    "pii_detection": {
                        "types": {
                            "email": {"action": "block"}
                        }
                    },
                    "content_filter": {
                        "prohibited_topics": ["competitor pricing"]
                    }
                },
                "retention": {
                    "days": 180
                }
            },
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    config = resp.json()["config"]
    # Customer override: email action should be "block"
    assert config["pre_call"]["pii_detection"]["types"]["email"]["action"] == "block"
    # Template default preserved: SSN should still be "block"
    assert config["pre_call"]["pii_detection"]["types"]["ssn"]["action"] == "block"
    # Customer added prohibited topics
    assert "competitor pricing" in config["pre_call"]["content_filter"]["prohibited_topics"]
    # Retention overridden
    assert config["retention"]["days"] == 180


@pytest.mark.asyncio
async def test_nested_customization_preserves_defaults(engine, client: AsyncClient, test_api_key: dict) -> None:
    await _seed_templates(engine)
    resp = await client.post(
        "/v1/templates/document_generation/apply",
        json={
            "customizations": {
                "pre_call": {
                    "injection_detection": {
                        "action": "block"
                    }
                }
            }
        },
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert resp.status_code == 201
    config = resp.json()["config"]
    # Customized: injection action changed
    assert config["pre_call"]["injection_detection"]["action"] == "block"
    # Preserved: injection still enabled
    assert config["pre_call"]["injection_detection"]["enabled"] is True
    # Preserved: PII config untouched
    assert config["pre_call"]["pii_detection"]["enabled"] is True


# ── Integration: Template-based policy enforced via chat ───────────


@pytest.mark.asyncio
@patch("audithive.api.routes.chat.proxy_request")
async def test_template_policy_enforcement(
    mock_proxy: AsyncMock,
    engine,
    client: AsyncClient,
    test_api_key: dict,
) -> None:
    """A policy created from the chatbot template should block SSN."""
    mock_proxy.return_value = ProxyResponse(status_code=200, body=FAKE_OPENAI_RESPONSE, latency_ms=50)

    await _seed_templates(engine)

    # Apply chatbot template (SSN action=block by default)
    apply_resp = await client.post(
        "/v1/templates/customer_chatbot/apply",
        json={"name": "Enforce SSN Block"},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    assert apply_resp.status_code == 201

    # Send a chat request with SSN — should be blocked
    chat_resp = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "My SSN is 123-45-6789"}]},
        headers={
            "Authorization": f"Bearer {test_api_key['key']}",
            "X-LLM-Key": "sk-test",
        },
    )
    assert chat_resp.status_code == 403
    assert chat_resp.json()["action"] == "block"
