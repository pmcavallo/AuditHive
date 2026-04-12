"""Governance report generator — Jinja2 HTML with optional PDF."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.assessment.engine import run_assessment
from audithive.assessment.gaps import detect_gaps
from audithive.db.models import (
    AuditLog,
    Customer,
    CustomerProfile,
    ExaminerReport,
    PolicyConfig,
)
from audithive.examiner.agent import ExaminerContext, generate_examiner_report

TEMPLATES_DIR = Path(__file__).parent / "templates"

_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


async def _gather_context(
    db: AsyncSession,
    customer_id: UUID,
    period_days: int,
) -> dict:
    """Gather all data needed for the report."""
    # Customer
    cust_result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = cust_result.scalar_one()

    # Profile
    prof_result = await db.execute(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id))
    profile = prof_result.scalar_one_or_none()

    # Policies
    pol_result = await db.execute(
        select(PolicyConfig).where(PolicyConfig.customer_id == customer_id, PolicyConfig.is_active.is_(True))
    )
    policies = list(pol_result.scalars().all())

    # Assessment
    assessment = None
    if profile:
        assessment = await run_assessment(db, customer_id, profile, policies)

    # Gaps
    gaps_data = await detect_gaps(db, customer_id, policies)

    # Audit stats
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    from sqlalchemy import case, func
    count_result = await db.execute(
        select(
            func.count(AuditLog.id).label("total"),
            func.count(case((AuditLog.status == "blocked", 1))).label("blocked"),
            func.count(case((AuditLog.status == "flagged", 1))).label("flagged"),
        ).where(AuditLog.customer_id == customer_id, AuditLog.created_at >= since)
    )
    stats_row = count_result.one()

    # Recent violations
    viol_result = await db.execute(
        select(AuditLog).where(
            AuditLog.customer_id == customer_id,
            AuditLog.status.in_(["blocked", "flagged"]),
            AuditLog.created_at >= since,
        ).order_by(AuditLog.created_at.desc()).limit(10)
    )
    violations = viol_result.scalars().all()
    violation_details = []
    for v in violations:
        preview = ""
        if v.request_messages:
            for msg in v.request_messages:
                if msg.get("role") == "user":
                    preview = (msg.get("content") or "")[:100]
                    break
        violation_details.append({"status": v.status, "model": v.request_model, "preview": preview})

    return {
        "customer": customer,
        "profile": profile,
        "policies": policies,
        "assessment": assessment,
        "gaps": gaps_data,
        "stats": {"total": stats_row.total, "blocked": stats_row.blocked, "flagged": stats_row.flagged},
        "violation_details": violation_details,
        "period_days": period_days,
    }


async def generate_governance_report(
    db: AsyncSession,
    customer_id: UUID,
    period_days: int = 30,
    include_examiner: bool = True,
) -> tuple[str, UUID]:
    """Generate a governance report. Returns (html_string, report_id)."""
    ctx = await _gather_context(db, customer_id, period_days)
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=period_days)

    # Examiner simulation
    examiner_data = None
    if include_examiner and ctx["profile"]:
        examiner_ctx = ExaminerContext(
            industry=ctx["profile"].industry or "other",
            jurisdictions=ctx["profile"].jurisdictions or [],
            ai_use_cases=ctx["profile"].ai_use_cases or [],
            coverage_score=ctx["assessment"]["coverage_score"] if ctx["assessment"] else 0,
            maturity_level=ctx["assessment"]["maturity_level"] if ctx["assessment"] else "ungoverned",
            applicable_regulations=ctx["assessment"]["applicable_regulations"] if ctx["assessment"] else [],
            missing_controls=ctx["assessment"]["missing_controls"] if ctx["assessment"] else [],
            gaps=ctx["gaps"].get("gaps", []),
            four_questions=ctx["assessment"]["four_questions"] if ctx["assessment"] else {},
            total_calls=ctx["stats"]["total"],
            total_blocked=ctx["stats"]["blocked"],
            total_flagged=ctx["stats"]["flagged"],
            violation_details=ctx["violation_details"],
            active_policies=[{"name": p.name} for p in ctx["policies"]],
        )
        examiner_data = await generate_examiner_report(examiner_ctx)

    # Render HTML
    template = _jinja_env.get_template("governance_report.html")
    html = template.render(
        customer_name=ctx["customer"].company_name or ctx["customer"].name,
        period_start=period_start.strftime("%B %d, %Y"),
        period_end=now.strftime("%B %d, %Y"),
        generated_at=now.strftime("%B %d, %Y %H:%M UTC"),
        coverage_score=ctx["assessment"]["coverage_score"] if ctx["assessment"] else 0,
        maturity_level=ctx["assessment"]["maturity_level"] if ctx["assessment"] else "ungoverned",
        applicable_regulations=ctx["assessment"]["applicable_regulations"] if ctx["assessment"] else [],
        required_controls=ctx["assessment"]["required_controls"] if ctx["assessment"] else [],
        missing_controls=ctx["assessment"]["missing_controls"] if ctx["assessment"] else [],
        gaps=ctx["gaps"].get("gaps", []),
        four_questions=ctx["assessment"]["four_questions"] if ctx["assessment"] else {},
        stats=ctx["stats"],
        examiner=examiner_data,
        recommendations=ctx["assessment"]["recommendations"] if ctx["assessment"] else [],
        policies_count=len(ctx["policies"]),
        regulations_count=len(ctx["assessment"]["applicable_regulations"]) if ctx["assessment"] else 0,
    )

    # Save to database
    report = ExaminerReport(
        customer_id=customer_id,
        report_type="governance_report",
        period_start=period_start,
        period_end=now,
        coverage_score=ctx["assessment"]["coverage_score"] if ctx["assessment"] else None,
        maturity_level=ctx["assessment"]["maturity_level"] if ctx["assessment"] else None,
        regulations_count=len(ctx["assessment"]["applicable_regulations"]) if ctx["assessment"] else 0,
        gaps_count=ctx["gaps"].get("gap_count", 0),
        examiner_narrative=examiner_data.executive_summary if examiner_data else None,
        examiner_questions=examiner_data.questions if examiner_data else [],
        examiner_findings=[asdict(f) for f in examiner_data.findings] if examiner_data else [],
        recommendations=examiner_data.recommendations if examiner_data else [],
        report_html=html,
    )
    db.add(report)
    await db.flush()

    return html, report.id
