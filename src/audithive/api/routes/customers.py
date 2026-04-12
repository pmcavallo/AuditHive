"""Customer and API key management endpoints (admin, no auth for MVP)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.core.security import generate_api_key
from audithive.db.database import get_db
from audithive.db.models import ApiKey, Customer
from audithive.schemas.customer import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    CustomerCreate,
    CustomerResponse,
)

router = APIRouter(prefix="/v1/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    """Create a new customer account."""
    customer = Customer(
        name=body.name,
        email=body.email,
        company_name=body.company_name,
    )
    db.add(customer)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A customer with this email already exists.")
    return customer


@router.post("/{customer_id}/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    customer_id: UUID,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new API key for a customer. The full key is shown only once."""
    # Verify customer exists
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    full_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        customer_id=customer_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
    )
    db.add(api_key)
    await db.flush()

    return {
        "id": api_key.id,
        "key": full_key,
        "key_prefix": key_prefix,
        "name": api_key.name,
        "created_at": api_key.created_at,
        "warning": "Save this key now. It will not be shown again.",
    }


@router.get("/{customer_id}/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all API keys for a customer (prefix only, never the full key)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.customer_id == customer_id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return {"keys": keys}


@router.delete("/{customer_id}/api-keys/{key_id}")
async def deactivate_api_key(
    customer_id: UUID,
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate an API key (soft delete)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.customer_id == customer_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found.")

    api_key.is_active = False
    return {"status": "deactivated"}
