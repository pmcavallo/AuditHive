"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.core.encryption import get_encryption_key

router = APIRouter()

VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict:
    """Public health check — no auth required."""
    return {
        "status": "healthy",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "security": {
            "encryption_enabled": get_encryption_key() is not None,
        },
    }


@router.get("/v1/health")
async def authenticated_health_check(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
) -> dict:
    """Authenticated health check — requires valid API key."""
    return {
        "status": "healthy",
        "version": VERSION,
        "customer_id": str(customer.customer_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "security": {
            "encryption_enabled": get_encryption_key() is not None,
        },
    }
