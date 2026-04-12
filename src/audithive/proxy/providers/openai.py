"""OpenAI provider: forward requests to OpenAI's chat completions API."""

from __future__ import annotations

import time

import httpx

from audithive.proxy.models import ProxyResponse

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
TIMEOUT_SECONDS = 30.0


async def forward_to_openai(
    api_key: str,
    request_body: dict,
) -> ProxyResponse:
    """Send a chat completion request to OpenAI and return the response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(OPENAI_CHAT_URL, json=request_body, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
    except httpx.TimeoutException:
        latency_ms = int((time.monotonic() - start) * 1000)
        return ProxyResponse(
            status_code=504,
            body={"error": "llm_provider_timeout", "message": "The LLM provider did not respond in time."},
            latency_ms=latency_ms,
            error="llm_provider_timeout",
        )
    except httpx.RequestError:
        latency_ms = int((time.monotonic() - start) * 1000)
        return ProxyResponse(
            status_code=502,
            body={"error": "llm_provider_error", "message": "Failed to connect to the LLM provider."},
            latency_ms=latency_ms,
            error="llm_provider_error",
        )

    if resp.status_code == 200:
        return ProxyResponse(
            status_code=200,
            body=resp.json(),
            latency_ms=latency_ms,
        )

    # Map provider errors to AuditHive error responses
    if resp.status_code == 401:
        return ProxyResponse(
            status_code=502,
            body={"error": "llm_provider_auth_failed", "message": "The LLM provider rejected the API key. Check your X-LLM-Key."},
            latency_ms=latency_ms,
            error="llm_provider_auth_failed",
        )
    if resp.status_code == 429:
        return ProxyResponse(
            status_code=502,
            body={"error": "llm_provider_rate_limited", "message": "The LLM provider rate-limited the request. Try again shortly."},
            latency_ms=latency_ms,
            error="llm_provider_rate_limited",
        )

    # 500, 503, or other errors
    return ProxyResponse(
        status_code=502,
        body={"error": "llm_provider_error", "message": "The LLM provider returned an error."},
        latency_ms=latency_ms,
        error="llm_provider_error",
    )
