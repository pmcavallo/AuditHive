"""Regulatory update, impact assessment, and timeline endpoints."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.alerts.dispatcher import dispatch_alert
from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db
from audithive.db.models import CustomerImpactAssessment, RegulatoryUpdate
from audithive.regulatory.impact import (
    assess_all_customers,
    assess_impact,
    check_upcoming_deadlines,
)
from audithive.schemas.regulatory import (
    ImpactListResponse,
    RegulatoryUpdateCreate,
    RegulatoryUpdateListResponse,
    TimelineResponse,
)

router = APIRouter(prefix="/v1/regulatory", tags=["regulatory"])


# ── Updates ───────────────────────────────────────────────────��────


@router.get("/updates", response_model=RegulatoryUpdateListResponse)
async def list_updates(
    _customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    jurisdiction: str | None = Query(default=None),
) -> dict:
    """List all active regulatory updates."""
    query = select(RegulatoryUpdate).where(RegulatoryUpdate.is_active.is_(True))
    if jurisdiction:
        query = query.where(RegulatoryUpdate.jurisdiction == jurisdiction)
    query = query.order_by(RegulatoryUpdate.deadline.asc().nulls_last())

    result = await db.execute(query)
    updates = result.scalars().all()
    return {"updates": updates}


@router.post("/updates", status_code=201)
async def create_update(
    body: RegulatoryUpdateCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a new regulatory update. Auto-assesses all customers."""
    update = RegulatoryUpdate(
        title=body.title,
        summary=body.summary,
        regulation_short=body.regulation_short,
        regulation_name=body.regulation_name,
        update_type=body.update_type,
        jurisdiction=body.jurisdiction,
        industries=body.industries,
        use_cases=body.use_cases,
        audiences=body.audiences,
        required_actions=body.required_actions,
        affected_controls=body.affected_controls,
        severity=body.severity,
        effective_date=body.effective_date,
        enforcement_date=body.enforcement_date,
        deadline=body.deadline,
        source_name=body.source_name,
        source_url=body.source_url,
    )
    db.add(update)
    await db.flush()

    # Auto-assess all customers
    affected = await assess_all_customers(db, update.id)

    # Dispatch alerts for critical/high impact
    for impact in affected:
        if impact.impact_level in ("critical", "high"):
            await dispatch_alert(
                db=db,
                customer_id=impact.customer_id,
                trigger_type="gap_detected",
                trigger_details={
                    "regulation": body.title,
                    "impact_level": impact.impact_level,
                    "missing_controls": [c["control"] for c in impact.controls_missing],
                },
            )

    return {
        "id": str(update.id),
        "title": update.title,
        "affected_customers": len(affected),
    }


# ── Impact ─────────────────────────────────────────────────────────


@router.get("/impact", response_model=ImpactListResponse)
async def get_impact(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    severity: str | None = Query(default=None),
    days_ahead: int = Query(default=90),
) -> dict:
    """Get personalized impact assessments for the customer."""
    # First ensure assessments exist for all updates
    updates_result = await db.execute(
        select(RegulatoryUpdate).where(RegulatoryUpdate.is_active.is_(True))
    )
    all_updates = updates_result.scalars().all()

    for update in all_updates:
        # Check if assessment already exists
        existing = await db.execute(
            select(CustomerImpactAssessment).where(
                CustomerImpactAssessment.customer_id == customer.customer_id,
                CustomerImpactAssessment.regulatory_update_id == update.id,
            )
        )
        if not existing.scalar_one_or_none():
            await assess_impact(db, customer.customer_id, update.id)

    # Now fetch all assessments
    query = (
        select(CustomerImpactAssessment, RegulatoryUpdate)
        .join(RegulatoryUpdate, CustomerImpactAssessment.regulatory_update_id == RegulatoryUpdate.id)
        .where(
            CustomerImpactAssessment.customer_id == customer.customer_id,
            CustomerImpactAssessment.is_affected.is_(True),
        )
    )
    if severity:
        query = query.where(CustomerImpactAssessment.impact_level == severity)

    result = await db.execute(query)
    rows = result.all()

    impacts = []
    counts = {"critical": 0, "high": 0, "medium": 0}
    total_actions = 0
    nearest_deadline = None
    nearest_reg = None

    for impact, update in rows:
        days_until = None
        if update.deadline:
            dl = update.deadline
            if isinstance(dl, datetime):
                dl = dl.date()
            days_until = (dl - date.today()).days

            if nearest_deadline is None or dl < nearest_deadline:
                nearest_deadline = dl
                nearest_reg = update.regulation_name or update.title

        if impact.impact_level in counts:
            counts[impact.impact_level] += 1
        total_actions += len(impact.required_actions)

        impacts.append({
            "id": impact.id,
            "regulatory_update": {
                "id": update.id,
                "title": update.title,
                "summary": update.summary,
                "jurisdiction": update.jurisdiction,
                "severity": update.severity,
                "enforcement_date": update.enforcement_date,
                "deadline": update.deadline,
                "update_type": update.update_type,
                "source_name": update.source_name,
            },
            "impact_level": impact.impact_level,
            "is_affected": True,
            "reasons": impact.reasons,
            "controls_in_place": impact.controls_in_place,
            "controls_missing": impact.controls_missing,
            "required_actions": impact.required_actions,
            "days_until_deadline": days_until,
            "acknowledged": impact.acknowledged,
        })

    return {
        "impacts": impacts,
        "summary": {
            "total_affecting": len(impacts),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "actions_required": total_actions,
            "next_deadline": str(nearest_deadline) if nearest_deadline else None,
            "next_deadline_regulation": nearest_reg,
        },
    }


@router.post("/impact/{impact_id}/acknowledge")
async def acknowledge_impact(
    impact_id: UUID,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Acknowledge a regulatory impact assessment."""
    result = await db.execute(
        select(CustomerImpactAssessment).where(
            CustomerImpactAssessment.id == impact_id,
            CustomerImpactAssessment.customer_id == customer.customer_id,
        )
    )
    impact = result.scalar_one_or_none()
    if not impact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Impact assessment not found.")

    impact.acknowledged = True
    impact.acknowledged_at = datetime.now(timezone.utc)
    return {"acknowledged": True, "acknowledged_at": impact.acknowledged_at.isoformat()}


# ── Timeline ───────────────────────────────────────────────────────


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
    days_ahead: int = Query(default=180),
) -> dict:
    """Get chronological timeline of regulatory deadlines affecting this customer."""
    # Ensure assessments are computed
    updates_result = await db.execute(
        select(RegulatoryUpdate).where(RegulatoryUpdate.is_active.is_(True))
    )
    for update in updates_result.scalars().all():
        existing = await db.execute(
            select(CustomerImpactAssessment).where(
                CustomerImpactAssessment.customer_id == customer.customer_id,
                CustomerImpactAssessment.regulatory_update_id == update.id,
            )
        )
        if not existing.scalar_one_or_none():
            await assess_impact(db, customer.customer_id, update.id)

    timeline = await check_upcoming_deadlines(db, customer.customer_id, days_ahead)
    return {"timeline": timeline}
