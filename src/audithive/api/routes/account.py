"""Data lifecycle endpoints: export and delete customer data."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.core.encryption import decrypt_json
from audithive.db.database import get_db
from audithive.db.models import (
    AlertConfig,
    AlertHistory,
    ApiKey,
    AuditLog,
    Customer,
    CustomerImpactAssessment,
    CustomerProfile,
    ExaminerReport,
    GovernanceAssessment,
    PolicyConfig,
)

router = APIRouter(prefix="/v1/account", tags=["account"])

PURGE_ORDER = [
    ("customer_impact_assessments", CustomerImpactAssessment),
    ("alert_history", AlertHistory),
    ("alert_configs", AlertConfig),
    ("examiner_reports", ExaminerReport),
    ("governance_assessments", GovernanceAssessment),
    ("customer_profiles", CustomerProfile),
    ("audit_logs", AuditLog),
    ("policy_configs", PolicyConfig),
    ("api_keys", ApiKey),
]


class DeleteConfirmation(BaseModel):
    confirm: bool = False


@router.delete("")
async def delete_account(
    body: DeleteConfirmation,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Permanently delete ALL data for the authenticated customer (GDPR/CCPA)."""
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="This action permanently deletes all your data. Send {\"confirm\": true} to proceed.",
        )

    cid = customer.customer_id
    tables_purged = []

    for table_name, model in PURGE_ORDER:
        await db.execute(delete(model).where(model.customer_id == cid))
        tables_purged.append(table_name)

    await db.execute(delete(Customer).where(Customer.id == cid))
    tables_purged.append("customers")

    receipt_id = uuid.uuid4()

    return {
        "deleted": True,
        "customer_id": str(cid),
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "receipt_id": str(receipt_id),
        "tables_purged": tables_purged,
    }


@router.get("/export")
async def export_account(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export ALL data for the authenticated customer (GDPR/CCPA)."""
    cid = customer.customer_id

    # Customer
    cust_result = await db.execute(select(Customer).where(Customer.id == cid))
    cust = cust_result.scalar_one()

    # Profile
    prof_result = await db.execute(select(CustomerProfile).where(CustomerProfile.customer_id == cid))
    profile = prof_result.scalar_one_or_none()

    # Policies
    pol_result = await db.execute(select(PolicyConfig).where(PolicyConfig.customer_id == cid))
    policies = pol_result.scalars().all()

    # Audit logs (with decryption)
    log_result = await db.execute(select(AuditLog).where(AuditLog.customer_id == cid))
    logs = log_result.scalars().all()
    exported_logs = []
    for log in logs:
        exported_logs.append({
            "id": str(log.id),
            "request_model": log.request_model,
            "request_messages": decrypt_json(log.request_messages),
            "response_content": decrypt_json(log.response_content),
            "status": log.status,
            "action_taken": log.action_taken,
            "response_latency_ms": log.response_latency_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    # Assessments
    assess_result = await db.execute(select(GovernanceAssessment).where(GovernanceAssessment.customer_id == cid))
    assessments = assess_result.scalars().all()

    # Reports
    report_result = await db.execute(select(ExaminerReport).where(ExaminerReport.customer_id == cid))
    reports = report_result.scalars().all()

    # Alerts
    config_result = await db.execute(select(AlertConfig).where(AlertConfig.customer_id == cid))
    alert_config = config_result.scalar_one_or_none()

    hist_result = await db.execute(select(AlertHistory).where(AlertHistory.customer_id == cid))
    alert_history = hist_result.scalars().all()

    # Regulatory impacts
    impact_result = await db.execute(select(CustomerImpactAssessment).where(CustomerImpactAssessment.customer_id == cid))
    impacts = impact_result.scalars().all()

    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "customer": {
            "id": str(cust.id), "name": cust.name, "email": cust.email,
            "company_name": cust.company_name, "plan": cust.plan,
            "created_at": cust.created_at.isoformat() if cust.created_at else None,
        },
        "profile": {
            "industry": profile.industry, "jurisdictions": profile.jurisdictions,
            "ai_use_cases": profile.ai_use_cases, "audience_types": profile.audience_types,
        } if profile else None,
        "policies": [{"id": str(p.id), "name": p.name, "config": p.config} for p in policies],
        "audit_logs": exported_logs,
        "assessments": [
            {"id": str(a.id), "coverage_score": a.coverage_score, "maturity_level": a.maturity_level}
            for a in assessments
        ],
        "reports": [
            {"id": str(r.id), "report_type": r.report_type, "coverage_score": r.coverage_score,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in reports
        ],
        "alerts": {
            "config": {
                "on_block": alert_config.on_block, "on_flag": alert_config.on_flag,
                "email_addresses": alert_config.email_addresses, "webhook_urls": alert_config.webhook_urls,
            } if alert_config else None,
            "history": [
                {"trigger_type": h.trigger_type, "status": h.status,
                 "created_at": h.created_at.isoformat() if h.created_at else None}
                for h in alert_history
            ],
        },
        "regulatory_impacts": [
            {"id": str(i.id), "impact_level": i.impact_level, "is_affected": i.is_affected}
            for i in impacts
        ],
    }
