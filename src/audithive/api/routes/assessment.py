"""Assessment endpoints: profile, governance assessment, gaps, four questions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.assessment.engine import run_assessment
from audithive.assessment.gaps import detect_gaps
from audithive.db.database import get_db
from audithive.db.models import CustomerProfile, GovernanceAssessment, PolicyConfig
from audithive.schemas.assessment import (
    AssessmentResponse,
    FourQuestionsRequest,
    FourQuestionsResponse,
    GapsResponse,
    ProfileCreate,
    ProfileResponse,
)

router = APIRouter(tags=["assessment"])


# ── Profile ────────────────────────────────────────────────────────


@router.post("/v1/profile", response_model=ProfileResponse, status_code=201)
async def create_or_update_profile(
    body: ProfileCreate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create or update the customer's onboarding profile."""
    result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.customer_id == customer.customer_id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile.ai_use_cases = body.ai_use_cases
        profile.audience_types = body.audience_types
        profile.industry = body.industry
        profile.jurisdictions = body.jurisdictions
        profile.ai_features_enabled = body.ai_features_enabled
    else:
        profile = CustomerProfile(
            customer_id=customer.customer_id,
            ai_use_cases=body.ai_use_cases,
            audience_types=body.audience_types,
            industry=body.industry,
            jurisdictions=body.jurisdictions,
            ai_features_enabled=body.ai_features_enabled,
        )
        db.add(profile)

    await db.flush()

    disclosure = None
    if profile.ai_features_enabled:
        disclosure = (
            "AI-powered examiner reports use the Anthropic Claude API. When enabled, "
            "anonymized summary statistics (violation counts, policy names, coverage scores) "
            "are sent to Anthropic. Raw conversation content is never sent. "
            "You can disable this at any time."
        )

    return {
        "profile_id": profile.id,
        "ai_use_cases": profile.ai_use_cases,
        "audience_types": profile.audience_types,
        "industry": profile.industry,
        "jurisdictions": profile.jurisdictions,
        "ai_features_enabled": profile.ai_features_enabled,
        "ai_features_disclosure": disclosure,
        "message": "Profile saved. Run GET /v1/assessment to see your governance gaps.",
    }


@router.get("/v1/profile")
async def get_profile(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the customer's onboarding profile."""
    result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.customer_id == customer.customer_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found. POST /v1/profile to create one.")
    return {
        "profile_id": profile.id,
        "ai_use_cases": profile.ai_use_cases,
        "audience_types": profile.audience_types,
        "industry": profile.industry,
        "jurisdictions": profile.jurisdictions,
    }


# ── Assessment ─────────────────────────────────────────────────────


@router.get("/v1/assessment", response_model=AssessmentResponse)
async def get_assessment(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a full governance gap analysis based on the customer's profile."""
    # Load profile
    result = await db.execute(
        select(CustomerProfile).where(CustomerProfile.customer_id == customer.customer_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="No profile found. POST /v1/profile first to enable assessment.",
        )

    # Load active policies
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        )
    )
    policies = list(result.scalars().all())

    return await run_assessment(db, customer.customer_id, profile, policies)


# ── Gaps ───────────────────────────────────────────────────────────


@router.get("/v1/assessment/gaps", response_model=GapsResponse)
async def get_gaps(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Detect described-vs-established gaps between policy config and enforcement."""
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        )
    )
    policies = list(result.scalars().all())
    return await detect_gaps(db, customer.customer_id, policies)


# ── Four Questions ─────────────────────────────────────────────────


@router.post("/v1/assessment/four-questions", response_model=FourQuestionsResponse)
async def submit_four_questions(
    body: FourQuestionsRequest,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit answers to the Four Questions framework and get maturity score."""
    # Load active policies to cross-reference
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        )
    )
    policies = list(result.scalars().all())
    has_policies = len(policies) > 0

    questions = {}
    answered_count = 0
    controls_match = 0

    # Purpose
    if body.purpose:
        answered_count += 1
        controls_match += 1  # having a stated purpose = match
        questions["purpose"] = {
            "answered": True,
            "answer": body.purpose,
            "assessment": "Well-defined purpose statement.",
        }
    else:
        questions["purpose"] = {
            "answered": False,
            "recommendation": "Define the intended purpose and scope of your AI system",
        }

    # Working — cross-reference with monitoring controls
    if body.working:
        answered_count += 1
        if has_policies:
            controls_match += 1
            questions["working"] = {
                "answered": True,
                "answer": body.working,
                "assessment": "Monitoring process described and AuditHive policies are active.",
            }
        else:
            questions["working"] = {
                "answered": True,
                "answer": body.working,
                "assessment": "Monitoring process described but no AuditHive policies are active.",
                "gap": "Described-vs-established gap: you describe monitoring but have no active policies.",
            }
    else:
        questions["working"] = {
            "answered": False,
            "recommendation": "Enable hallucination detection or quality scoring for continuous monitoring",
        }

    # Failure — cross-reference with alerting (not yet built)
    if body.failure:
        answered_count += 1
        # Alerting not implemented yet, so always flag as gap
        questions["failure"] = {
            "answered": True,
            "answer": body.failure,
            "assessment": "Escalation process described.",
            "gap": "No alerting is currently configured in AuditHive. Configure alerts to match this answer.",
        }
    else:
        questions["failure"] = {
            "answered": False,
            "recommendation": "Configure violation alerts via email or Slack",
        }

    # Accountability
    if body.accountability:
        answered_count += 1
        controls_match += 1
        questions["accountability"] = {
            "answered": True,
            "answer": body.accountability,
            "assessment": "AI system owner designated.",
        }
    else:
        questions["accountability"] = {
            "answered": False,
            "recommendation": "Designate an AI system owner in Settings",
        }

    # Maturity scoring
    if answered_count == 4 and controls_match >= 3:
        maturity_level = "mature"
        maturity_score = 4
    elif answered_count >= 3 or (answered_count == 4 and controls_match < 3):
        maturity_level = "developing"
        maturity_score = 3
    elif answered_count == 2:
        maturity_level = "immature"
        maturity_score = 2
    else:
        maturity_level = "ungoverned"
        maturity_score = 1

    gaps_found = sum(1 for q in questions.values() if q.get("gap"))
    breakdown = f"{answered_count}/4 questions answered. {controls_match}/4 have matching controls."
    if gaps_found:
        breakdown += f" {gaps_found} described-vs-established gap(s) detected."

    return {
        "maturity_level": maturity_level,
        "maturity_score": maturity_score,
        "questions": questions,
        "maturity_breakdown": breakdown,
    }
