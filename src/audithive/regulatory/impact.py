"""Proactive Regulatory Impact Assessment Engine."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.assessment.engine import _extract_controls_from_policy
from audithive.db.models import (
    CustomerImpactAssessment,
    CustomerProfile,
    PolicyConfig,
    RegulatoryUpdate,
)

US_JURISDICTIONS = {
    "california", "colorado", "utah", "new_york", "illinois",
    "texas", "florida", "us_federal",
}


def _is_affected(profile: CustomerProfile, update: RegulatoryUpdate) -> bool:
    """Determine if a customer is affected by a regulatory update."""
    # Jurisdiction match
    profile_jurisdictions = profile.jurisdictions or []
    if update.jurisdiction == "us_federal":
        jurisdiction_match = any(j in US_JURISDICTIONS for j in profile_jurisdictions)
    elif update.jurisdiction == "eu":
        jurisdiction_match = "eu" in profile_jurisdictions or "uk" in profile_jurisdictions
    else:
        jurisdiction_match = update.jurisdiction in profile_jurisdictions

    if not jurisdiction_match:
        return False

    # Industry match
    update_industries = update.industries or ["any"]
    if "any" not in update_industries and profile.industry not in update_industries:
        return False

    # Use case match
    update_use_cases = update.use_cases or ["any"]
    if "any" not in update_use_cases and not any(
        uc in update_use_cases for uc in (profile.ai_use_cases or [])
    ):
        return False

    # Audience match
    update_audiences = update.audiences or ["any"]
    if "any" not in update_audiences and not any(
        at in update_audiences for at in (profile.audience_types or [])
    ):
        return False

    return True


def _build_reasons(profile: CustomerProfile, update: RegulatoryUpdate) -> list[str]:
    """Generate human-readable reasons why this customer is affected."""
    reasons = []
    reasons.append(f"Your operations include the '{update.jurisdiction}' jurisdiction")

    matching_use_cases = [uc for uc in (profile.ai_use_cases or []) if uc in (update.use_cases or []) or "any" in (update.use_cases or [])]
    if matching_use_cases:
        reasons.append(f"You operate: {', '.join(matching_use_cases)}")

    matching_audiences = [at for at in (profile.audience_types or []) if at in (update.audiences or []) or "any" in (update.audiences or [])]
    if matching_audiences:
        reasons.append(f"Your audience includes: {', '.join(matching_audiences)}")

    return reasons


def _compute_impact_level(
    update_severity: str,
    controls_missing: list,
    controls_in_place: list,
    days_until_deadline: int | None,
) -> str:
    """Compute personalized impact level."""
    if not controls_missing:
        return "low"

    if update_severity == "critical" and controls_missing and (days_until_deadline is not None and days_until_deadline <= 90):
        return "critical"
    if update_severity in ("critical", "high") and controls_missing:
        return "high" if (days_until_deadline is not None and days_until_deadline <= 180) else "medium"
    if controls_missing:
        return "medium"
    return "low"


async def assess_impact(
    db: AsyncSession,
    customer_id: UUID,
    regulatory_update_id: UUID,
) -> CustomerImpactAssessment | None:
    """Assess the impact of a regulatory update on a specific customer."""
    # Load update
    result = await db.execute(select(RegulatoryUpdate).where(RegulatoryUpdate.id == regulatory_update_id))
    update = result.scalar_one_or_none()
    if not update:
        return None

    # Load profile
    result = await db.execute(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id))
    profile = result.scalar_one_or_none()
    if not profile:
        return None

    # Check if affected
    affected = _is_affected(profile, update)
    if not affected:
        return None

    # Load customer's active policies to check controls
    result = await db.execute(
        select(PolicyConfig).where(PolicyConfig.customer_id == customer_id, PolicyConfig.is_active.is_(True))
    )
    policies = list(result.scalars().all())

    current_controls: set[str] = set()
    for p in policies:
        current_controls |= _extract_controls_from_policy(p.config)

    affected_controls = update.affected_controls or []
    controls_in_place = [{"control": c} for c in affected_controls if c in current_controls]
    controls_missing = [{"control": c} for c in affected_controls if c not in current_controls]

    # Days until deadline
    days_until = None
    if update.deadline:
        dl = update.deadline if isinstance(update.deadline, date) else update.deadline.date() if hasattr(update.deadline, 'date') else update.deadline
        days_until = (dl - date.today()).days

    impact_level = _compute_impact_level(update.severity, controls_missing, controls_in_place, days_until)
    reasons = _build_reasons(profile, update)

    # Determine estimated effort
    efforts = [a.get("effort", "multi_step") for a in (update.required_actions or [])]
    if all(e == "one_click" for e in efforts):
        estimated_effort = "one_click"
    elif any(e == "monitor" for e in efforts):
        estimated_effort = "monitor"
    else:
        estimated_effort = "multi_step"

    # Upsert
    result = await db.execute(
        select(CustomerImpactAssessment).where(
            CustomerImpactAssessment.customer_id == customer_id,
            CustomerImpactAssessment.regulatory_update_id == regulatory_update_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.impact_level = impact_level
        existing.is_affected = True
        existing.reasons = reasons
        existing.controls_in_place = controls_in_place
        existing.controls_missing = controls_missing
        existing.required_actions = update.required_actions or []
        existing.estimated_effort = estimated_effort
        assessment = existing
    else:
        assessment = CustomerImpactAssessment(
            customer_id=customer_id,
            regulatory_update_id=regulatory_update_id,
            impact_level=impact_level,
            is_affected=True,
            reasons=reasons,
            controls_in_place=controls_in_place,
            controls_missing=controls_missing,
            required_actions=update.required_actions or [],
            estimated_effort=estimated_effort,
        )
        db.add(assessment)

    await db.flush()
    return assessment


async def assess_all_customers(
    db: AsyncSession,
    regulatory_update_id: UUID,
) -> list[CustomerImpactAssessment]:
    """Assess impact for ALL customers with profiles."""
    result = await db.execute(select(CustomerProfile))
    profiles = result.scalars().all()

    affected = []
    for profile in profiles:
        assessment = await assess_impact(db, profile.customer_id, regulatory_update_id)
        if assessment:
            affected.append(assessment)

    return affected


async def check_upcoming_deadlines(
    db: AsyncSession,
    customer_id: UUID,
    days_ahead: int = 90,
) -> list[dict]:
    """Get regulatory deadlines within the next N days that affect this customer."""
    today = date.today()
    cutoff = date(today.year, today.month, today.day)

    # Get all impact assessments for this customer
    result = await db.execute(
        select(CustomerImpactAssessment, RegulatoryUpdate)
        .join(RegulatoryUpdate, CustomerImpactAssessment.regulatory_update_id == RegulatoryUpdate.id)
        .where(
            CustomerImpactAssessment.customer_id == customer_id,
            CustomerImpactAssessment.is_affected.is_(True),
            RegulatoryUpdate.deadline.isnot(None),
        )
    )
    rows = result.all()

    deadlines = []
    for impact, update in rows:
        dl = update.deadline
        if isinstance(dl, datetime):
            dl = dl.date()
        days_away = (dl - today).days
        if 0 <= days_away <= days_ahead:
            actions_required = len(update.required_actions or [])
            actions_completed = len(impact.controls_in_place)
            deadlines.append({
                "date": str(dl),
                "regulation": update.regulation_name or update.title,
                "impact_level": impact.impact_level,
                "actions_required": actions_required,
                "actions_completed": actions_completed,
                "days_away": days_away,
            })

    deadlines.sort(key=lambda d: d["date"])
    return deadlines
