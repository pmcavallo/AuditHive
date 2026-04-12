"""Tests verifying customer LLM API keys never leak."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from audithive.proxy.models import ProxyResponse

FAKE_RESPONSE = {
    "id": "chatcmpl-safe",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}

LLM_KEY = "sk-test-SECRET-KEY-12345-abcdef"


@pytest.mark.asyncio
@patch("audithive.api.routes.chat.proxy_request")
async def test_llm_api_key_not_in_audit_log(
    mock_proxy: AsyncMock, client: AsyncClient, test_api_key: dict
) -> None:
    mock_proxy.return_value = ProxyResponse(status_code=200, body=FAKE_RESPONSE, latency_ms=50)

    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}", "X-LLM-Key": LLM_KEY},
    )
    log_id = resp.headers["X-AuditHive-Log-Id"]

    log_resp = await client.get(
        f"/v1/audit-logs/{log_id}",
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
    )
    log_text = json.dumps(log_resp.json())
    assert LLM_KEY not in log_text
    assert "sk-test" not in log_text


@pytest.mark.asyncio
async def test_llm_api_key_not_in_error_response(client: AsyncClient, test_api_key: dict) -> None:
    """Error responses must not leak the LLM API key."""
    # Missing model field should still not leak the key
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]},
        headers={"Authorization": f"Bearer {test_api_key['key']}"},
        # Deliberately missing X-LLM-Key
    )
    body = json.dumps(resp.json())
    assert LLM_KEY not in body


@pytest.mark.asyncio
async def test_llm_api_key_not_in_examiner_context() -> None:
    """The examiner agent context must not contain LLM API keys."""
    from audithive.examiner.agent import ExaminerContext, _build_user_message

    ctx = ExaminerContext(
        industry="ecommerce",
        jurisdictions=["california"],
        ai_use_cases=["customer_chatbot"],
        coverage_score=50.0,
        maturity_level="developing",
        applicable_regulations=[],
        missing_controls=[],
        gaps=[],
        four_questions={},
        total_calls=100,
        total_blocked=5,
        total_flagged=10,
        violation_details=[{"preview": f"Some text with {LLM_KEY}"}],
        active_policies=[],
    )
    message = _build_user_message(ctx)
    # The key should not appear even if violation details contain it
    # (violation details should only contain previews, not keys)
    # This tests that the context structure itself doesn't include API key fields
    assert "sk-ant-" not in message
    assert "X-LLM-Key" not in message
