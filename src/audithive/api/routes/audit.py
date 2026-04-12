"""Audit log query endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db
from audithive.db.models import AuditLog, PolicyConfig
from audithive.schemas.audit import AuditLogListResponse, AuditLogResponse, AuditLogStatsResponse

router = APIRouter(prefix="/v1/audit-logs", tags=["audit"])


@router.get("/stats", response_model=AuditLogStatsResponse)
async def audit_log_stats(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    """Aggregated stats for the Overview dashboard."""
    cid = customer.customer_id

    # Total counts by status
    count_result = await db.execute(
        select(
            func.count(AuditLog.id).label("total"),
            func.count(case((AuditLog.status == "blocked", 1))).label("blocked"),
            func.count(case((AuditLog.status == "flagged", 1))).label("flagged"),
            func.count(case((AuditLog.status == "completed", 1))).label("completed"),
        ).where(AuditLog.customer_id == cid)
    )
    row = count_result.one()
    total_calls = row.total
    total_blocked = row.blocked
    total_flagged = row.flagged
    total_completed = row.completed

    # Active policies count
    pol_result = await db.execute(
        select(func.count(PolicyConfig.id)).where(
            PolicyConfig.customer_id == cid,
            PolicyConfig.is_active.is_(True),
        )
    )
    active_policies = pol_result.scalar_one()

    # Calls by day
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day_result = await db.execute(
        select(
            func.date(AuditLog.created_at).label("day"),
            func.count(AuditLog.id).label("total"),
            func.count(
                case((AuditLog.status.in_(["blocked", "flagged"]), 1))
            ).label("violations"),
        )
        .where(AuditLog.customer_id == cid, AuditLog.created_at >= since)
        .group_by(func.date(AuditLog.created_at))
        .order_by(func.date(AuditLog.created_at))
    )
    calls_by_day = [
        {"date": str(r.day), "total": r.total, "violations": r.violations}
        for r in day_result.all()
    ]

    # Recent violations (blocked or flagged), last 5
    viol_result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.customer_id == cid,
            AuditLog.status.in_(["blocked", "flagged"]),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )
    violations = viol_result.scalars().all()
    recent_violations = []
    for v in violations:
        preview = ""
        if v.request_messages:
            for msg in v.request_messages:
                if msg.get("role") == "user":
                    preview = (msg.get("content") or "")[:100]
                    break
        recent_violations.append({
            "id": v.id,
            "created_at": v.created_at,
            "status": v.status,
            "request_model": v.request_model,
            "message_preview": preview,
            "policies_violated": v.policies_violated or [],
        })

    return {
        "total_calls": total_calls,
        "total_blocked": total_blocked,
        "total_flagged": total_flagged,
        "total_completed": total_completed,
        "active_policies": active_policies,
        "calls_by_day": calls_by_day,
        "recent_violations": recent_violations,
    }


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
) -> dict:
    """List the customer's audit logs with pagination and filters."""
    base_query = select(AuditLog).where(AuditLog.customer_id == customer.customer_id)
    count_query = select(func.count(AuditLog.id)).where(AuditLog.customer_id == customer.customer_id)

    if status:
        base_query = base_query.where(AuditLog.status == status)
        count_query = count_query.where(AuditLog.status == status)
    if start_date:
        base_query = base_query.where(AuditLog.created_at >= start_date)
        count_query = count_query.where(AuditLog.created_at >= start_date)
    if end_date:
        base_query = base_query.where(AuditLog.created_at <= end_date)
        count_query = count_query.where(AuditLog.created_at <= end_date)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(
        base_query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    logs = result.scalars().all()

    return {"logs": logs, "total": total, "limit": limit, "offset": offset}


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> AuditLog:
    """Get a single audit log entry. Must belong to the authenticated customer."""
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == log_id,
            AuditLog.customer_id == customer.customer_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found.")
    return log
