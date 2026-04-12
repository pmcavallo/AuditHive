"""Policy template browsing and application endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.core.utils import deep_merge
from audithive.db.database import get_db
from audithive.db.models import PolicyConfig, PolicyTemplate
from audithive.schemas.template import (
    TemplateApplyRequest,
    TemplateApplyResponse,
    TemplateDetailResponse,
    TemplateListItem,
    TemplateListResponse,
)

router = APIRouter(prefix="/v1/templates", tags=["templates"])


def _template_to_list_item(t: PolicyTemplate) -> TemplateListItem:
    """Extract metadata from a template (no full config)."""
    return TemplateListItem(
        id=t.id,
        name=t.name,
        description=t.description or "",
        use_case=t.use_case,
        risk_level=t.config.get("risk_level", "medium"),
        version=t.version,
        regulatory_grounding=t.config.get("regulatory_grounding", []),
    )


def _template_to_detail(t: PolicyTemplate) -> TemplateDetailResponse:
    """Full template detail including config."""
    # Return config without the metadata keys that are surfaced at top level
    config = {k: v for k, v in t.config.items() if k not in ("risk_level", "regulatory_grounding")}
    return TemplateDetailResponse(
        id=t.id,
        name=t.name,
        description=t.description or "",
        use_case=t.use_case,
        risk_level=t.config.get("risk_level", "medium"),
        version=t.version,
        regulatory_grounding=t.config.get("regulatory_grounding", []),
        config=config,
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    _customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all available policy templates (metadata only, no full config)."""
    result = await db.execute(select(PolicyTemplate).order_by(PolicyTemplate.name))
    templates = result.scalars().all()
    return {"templates": [_template_to_list_item(t) for t in templates]}


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: str,
    _customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> TemplateDetailResponse:
    """Get full template detail including the complete config."""
    result = await db.execute(
        select(PolicyTemplate).where(PolicyTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    return _template_to_detail(template)


@router.post("/{template_id}/apply", response_model=TemplateApplyResponse, status_code=201)
async def apply_template(
    template_id: str,
    body: TemplateApplyRequest,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a policy configuration from a template with optional customizations."""
    result = await db.execute(
        select(PolicyTemplate).where(PolicyTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    # Extract the policy config (without metadata keys)
    base_config = {k: v for k, v in template.config.items() if k not in ("risk_level", "regulatory_grounding")}

    # Deep merge customizations over template defaults
    merged_config = deep_merge(base_config, body.customizations) if body.customizations else base_config

    policy_name = body.name or template.name

    policy = PolicyConfig(
        customer_id=customer.customer_id,
        name=policy_name,
        template_id=template.id,
        config=merged_config,
    )
    db.add(policy)
    await db.flush()

    return {
        "policy_id": policy.id,
        "template_id": template.id,
        "name": policy_name,
        "config": merged_config,
        "message": "Policy created from template. Active on your next API call.",
    }
