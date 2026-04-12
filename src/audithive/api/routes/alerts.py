"""Alert configuration and history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.alerts.dispatcher import dispatch_alert
from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db
from audithive.db.models import AlertConfig, AlertHistory
from audithive.schemas.reports import (
    AlertConfigRequest,
    AlertConfigResponse,
    AlertHistoryResponse,
)

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.get("/config")
async def get_alert_config(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the customer's alert configuration."""
    result = await db.execute(
        select(AlertConfig).where(AlertConfig.customer_id == customer.customer_id).limit(1)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"id": None, "enabled": False, "on_block": True, "on_flag": False,
                "on_gap_detected": True, "on_coverage_change": False,
                "email_addresses": [], "webhook_urls": []}
    return {
        "id": config.id, "enabled": config.enabled,
        "on_block": config.on_block, "on_flag": config.on_flag,
        "on_gap_detected": config.on_gap_detected, "on_coverage_change": config.on_coverage_change,
        "email_addresses": config.email_addresses, "webhook_urls": config.webhook_urls,
    }


@router.post("/config", response_model=AlertConfigResponse, status_code=201)
async def create_or_update_alert_config(
    body: AlertConfigRequest,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> AlertConfig:
    """Create or update alert configuration."""
    result = await db.execute(
        select(AlertConfig).where(AlertConfig.customer_id == customer.customer_id).limit(1)
    )
    config = result.scalar_one_or_none()

    if config:
        config.on_block = body.on_block
        config.on_flag = body.on_flag
        config.on_gap_detected = body.on_gap_detected
        config.on_coverage_change = body.on_coverage_change
        config.email_addresses = body.email_addresses
        config.webhook_urls = body.webhook_urls
        config.enabled = True
    else:
        config = AlertConfig(
            customer_id=customer.customer_id,
            on_block=body.on_block,
            on_flag=body.on_flag,
            on_gap_detected=body.on_gap_detected,
            on_coverage_change=body.on_coverage_change,
            email_addresses=body.email_addresses,
            webhook_urls=body.webhook_urls,
        )
        db.add(config)

    await db.flush()
    return config


@router.get("/history", response_model=AlertHistoryResponse)
async def alert_history(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    trigger_type: str | None = Query(default=None),
) -> dict:
    """List alert history."""
    base = select(AlertHistory).where(AlertHistory.customer_id == customer.customer_id)
    count_q = select(func.count(AlertHistory.id)).where(AlertHistory.customer_id == customer.customer_id)

    if trigger_type:
        base = base.where(AlertHistory.trigger_type == trigger_type)
        count_q = count_q.where(AlertHistory.trigger_type == trigger_type)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(base.order_by(AlertHistory.created_at.desc()).offset(offset).limit(limit))
    alerts = result.scalars().all()

    return {"alerts": alerts, "total": total}


@router.post("/test")
async def test_alert(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a test alert to all configured channels."""
    await dispatch_alert(
        db=db,
        customer_id=customer.customer_id,
        trigger_type="test",
        trigger_details={"message": "This is a test alert from AuditHive."},
    )
    return {"status": "sent", "message": "Test alert dispatched to all configured channels."}
