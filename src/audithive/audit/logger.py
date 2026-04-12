"""Audit trail logger: records every LLM interaction."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from audithive.core.encryption import encrypt_json
from audithive.db.models import AuditLog


async def log_interaction(
    db: AsyncSession,
    customer_id: UUID,
    api_key_id: UUID,
    request_model: str,
    request_messages: list[dict],
    request_params: dict,
    response_content: dict | None,
    response_tokens_in: int | None,
    response_tokens_out: int | None,
    response_latency_ms: int | None,
    policies_applied: list[dict],
    policies_violated: list[dict],
    action_taken: str,
    status: str,
    error_message: str | None = None,
) -> UUID:
    """Log a full interaction to the audit trail. Returns the log entry ID.

    Sensitive fields (request_messages, response_content) are encrypted at rest
    if AUDITHIVE_ENCRYPTION_KEY is configured. Unencrypted otherwise (backward compat).
    """
    log_entry = AuditLog(
        customer_id=customer_id,
        api_key_id=api_key_id,
        request_model=request_model,
        request_messages=encrypt_json(request_messages),
        request_params=request_params,
        response_content=encrypt_json(response_content),
        response_tokens_in=response_tokens_in,
        response_tokens_out=response_tokens_out,
        response_latency_ms=response_latency_ms,
        policies_applied=policies_applied,
        policies_violated=policies_violated,
        action_taken=action_taken,
        status=status,
        error_message=error_message,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry.id
