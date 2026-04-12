"""Report generation and download endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.db.database import get_db
from audithive.db.models import ExaminerReport
from audithive.reports.generator import generate_governance_report
from audithive.schemas.reports import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportListResponse,
)

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse, status_code=201)
async def generate_report(
    body: ReportGenerateRequest,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a governance report on demand."""
    html, report_id = await generate_governance_report(
        db=db,
        customer_id=customer.customer_id,
        period_days=body.period_days,
        include_examiner=body.include_examiner_simulation,
    )

    # Fetch saved report for response data
    result = await db.execute(select(ExaminerReport).where(ExaminerReport.id == report_id))
    report = result.scalar_one()

    return {
        "report_id": report.id,
        "status": report.status,
        "coverage_score": report.coverage_score,
        "maturity_level": report.maturity_level,
        "findings_count": len(report.examiner_findings),
        "download_url": f"/v1/reports/{report.id}/download",
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Download a generated report as HTML."""
    result = await db.execute(
        select(ExaminerReport).where(
            ExaminerReport.id == report_id,
            ExaminerReport.customer_id == customer.customer_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return HTMLResponse(
        content=report.report_html or "<p>Report content not available.</p>",
        headers={
            "Content-Disposition": f'inline; filename="audithive-report-{report_id}.html"',
        },
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all generated reports for the customer."""
    result = await db.execute(
        select(ExaminerReport)
        .where(ExaminerReport.customer_id == customer.customer_id)
        .order_by(ExaminerReport.created_at.desc())
    )
    reports = result.scalars().all()
    return {"reports": reports}


@router.post("/weekly-digest", status_code=201)
async def weekly_digest(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a weekly digest (examiner simulation for last 7 days)."""
    html, report_id = await generate_governance_report(
        db=db,
        customer_id=customer.customer_id,
        period_days=7,
        include_examiner=True,
    )

    result = await db.execute(select(ExaminerReport).where(ExaminerReport.id == report_id))
    report = result.scalar_one()
    report.report_type = "weekly_digest"

    return {
        "report_id": str(report.id),
        "executive_summary": report.examiner_narrative or "",
        "risk_rating": "medium",
        "findings": report.examiner_findings,
        "questions": report.examiner_questions,
        "recommendations": report.recommendations,
    }
