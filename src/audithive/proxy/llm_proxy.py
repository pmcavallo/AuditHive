"""LLM proxy: forward requests to the customer's LLM provider."""

from __future__ import annotations

from audithive.proxy.models import ProxyResponse
from audithive.proxy.providers.openai import forward_to_openai


async def proxy_request(
    provider: str,
    llm_api_key: str,
    request_body: dict,
) -> ProxyResponse:
    """Forward a chat completion request to the specified provider.

    Args:
        provider: LLM provider name (currently only "openai")
        llm_api_key: The customer's LLM provider API key
        request_body: The OpenAI-compatible request body

    Returns:
        ProxyResponse with the provider's response or error details.
    """
    if provider == "openai":
        return await forward_to_openai(llm_api_key, request_body)

    return ProxyResponse(
        status_code=400,
        body={"error": "unsupported_provider", "message": f"Provider '{provider}' is not supported."},
        latency_ms=0,
        error="unsupported_provider",
    )
