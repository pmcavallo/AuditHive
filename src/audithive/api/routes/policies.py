"""Policy configuration CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db
from audithive.db.models import PolicyConfig
from audithive.schemas.policy import (
    PolicyCreate,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdate,
)

router = APIRouter(prefix="/v1/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List the customer's active policy configurations."""
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        ).order_by(PolicyConfig.created_at.desc())
    )
    policies = result.scalars().all()
    return {"policies": policies}


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> PolicyConfig:
    """Create a new policy configuration."""
    policy = PolicyConfig(
        customer_id=customer.customer_id,
        name=body.name,
        config=body.config,
    )
    db.add(policy)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A policy with this name already exists.")
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    body: PolicyUpdate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> PolicyConfig:
    """Update an existing policy configuration."""
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.id == policy_id,
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    if body.name is not None:
        policy.name = body.name
    if body.config is not None:
        policy.config = body.config
    return policy


@router.delete("/{policy_id}")
async def deactivate_policy(
    policy_id: UUID,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a policy configuration (soft delete)."""
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.id == policy_id,
            PolicyConfig.customer_id == customer.customer_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    policy.is_active = False
    return {"status": "deactivated"}
