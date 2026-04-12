"""API key authentication middleware."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.core.config import settings
from audithive.core.security import verify_api_key
from audithive.db.database import get_db
from audithive.db.models import ApiKey


class AuthenticatedCustomer:
    """Holds the authenticated customer context."""

    def __init__(self, customer_id: UUID, api_key_id: UUID) -> None:
        self.customer_id = customer_id
        self.api_key_id = api_key_id


def _extract_bearer_token(request: Request) -> str:
    """Extract the API key from Authorization: Bearer header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key", "message": "The API key provided is invalid or inactive."},
        )
    return auth_header[7:]  # Strip "Bearer "


async def get_current_customer(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedCustomer:
    """FastAPI dependency: validate API key and return customer context."""
    token = _extract_bearer_token(request)
    prefix = settings.API_KEY_PREFIX

    if not token.startswith(prefix):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_api_key", "message": "The API key provided is invalid or inactive."},
        )

    # Extract the prefix portion for lookup (first 8 chars after "ah-")
    key_prefix_value = token[len(prefix): len(prefix) + 8]

    # Find active keys matching this prefix
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_prefix == key_prefix_value,
            ApiKey.is_active.is_(True),
        )
    )
    candidate_keys = result.scalars().all()

    # Check expiration and verify hash
    now = datetime.now(timezone.utc)
    for api_key in candidate_keys:
        if api_key.expires_at:
            # Normalize to UTC-aware for comparison (SQLite returns naive datetimes)
            exp = api_key.expires_at if api_key.expires_at.tzinfo else api_key.expires_at.replace(tzinfo=timezone.utc)
            if exp < now:
                continue
        if verify_api_key(token, api_key.key_hash):
            # Update last_used_at (non-blocking best-effort)
            await db.execute(
                update(ApiKey)
                .where(ApiKey.id == api_key.id)
                .values(last_used_at=now)
            )
            return AuthenticatedCustomer(
                customer_id=api_key.customer_id,
                api_key_id=api_key.id,
            )

    raise HTTPException(
        status_code=401,
        detail={"error": "invalid_api_key", "message": "The API key provided is invalid or inactive."},
    )
