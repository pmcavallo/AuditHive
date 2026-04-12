"""Described-vs-Established Gap Detector."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.db.models import AuditLog, PolicyConfig, PolicyTemplate


async def detect_gaps(
    db: AsyncSession,
    customer_id,
    policies: list[PolicyConfig],
) -> dict:
    """Compare policy config against enforcement data and template defaults."""
    gaps: list[dict] = []

    for policy in policies:
        config = policy.config
        pre_call = config.get("pre_call", config)

        # 1. Check for action mismatches: some PII types block while others only flag
        pii_cfg = pre_call.get("pii_detection", {})
        if pii_cfg.get("enabled"):
            types_field = pii_cfg.get("types", {})
            if isinstance(types_field, dict):
                has_block = any(
                    isinstance(tc, dict) and tc.get("action") == "block"
                    for tc in types_field.values()
                )
                for pii_type, type_cfg in types_field.items():
                    if isinstance(type_cfg, dict) and type_cfg.get("enabled") and type_cfg.get("action") == "flag" and has_block:
                        gaps.append({
                            "gap_type": "action_mismatch",
                            "description": f"PII type '{pii_type}' is set to 'flag' while other PII types are set to 'block'. Flagged content passes through instead of being blocked.",
                            "risk": "medium",
                            "fix": f"Change {pii_type} PII action from 'flag' to 'block'",
                            "effort": "one_click",
                        })

        # 2. Check for weakened template controls
        if policy.template_id:
            result = await db.execute(
                select(PolicyTemplate).where(PolicyTemplate.id == policy.template_id)
            )
            template = result.scalar_one_or_none()
            if template:
                tmpl_config = template.config
                tmpl_pre = tmpl_config.get("pre_call", tmpl_config)
                for check_name in ("injection_detection", "content_filter", "scope_enforcement"):
                    tmpl_check = tmpl_pre.get(check_name, {})
                    policy_check = pre_call.get(check_name, {})
                    tmpl_action = tmpl_check.get("action")
                    policy_action = policy_check.get("action")
                    if tmpl_action == "block" and policy_action == "flag":
                        gaps.append({
                            "gap_type": "weakened_template",
                            "description": f"Template '{policy.template_id}' recommends '{check_name}' action='block', but your policy uses 'flag'.",
                            "risk": "high",
                            "fix": f"Restore {check_name} to 'block' (template default)",
                            "effort": "one_click",
                        })

    gap_count = len(gaps)
    if gap_count == 0:
        if not policies:
            alignment = "none"
        else:
            alignment = "full"
    elif gap_count <= 2:
        alignment = "partial"
    else:
        alignment = "poor"

    return {"gaps": gaps, "gap_count": gap_count, "overall_alignment": alignment}
