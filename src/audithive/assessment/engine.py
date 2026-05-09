"""Governance Assessment Engine — the core differentiator."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.db.models import (
    CustomerProfile,
    GovernanceAssessment,
    PolicyConfig,
    RegulatoryMapping,
)

# Controls that AuditHive can detect from policy config
DETECTABLE_CONTROLS = {
    "pii_detection",
    "injection_detection",
    "content_filter",
    "scope_enforcement",
    "ai_disclosure",
    "bias_detection",      # NIST AI RMF Manage 4.1, EU AI Act Art 10, FHFA AB 2022-02
    "audit_logging",       # always on — we ARE the audit log
    "monitoring",          # having AuditHive = monitoring
}

EXAMINER_TEMPLATES: dict[str, str] = {
    "ai_disclosure": "How do you disclose to users that they are interacting with AI?",
    "pii_detection": "What controls do you have in place to prevent PII leakage through AI systems?",
    "audit_logging": "Can you produce a complete audit trail of all AI interactions upon examination?",
    "monitoring": "How do you monitor AI system outputs for quality and compliance?",
    "minor_protection": "What controls protect minors using your AI-facing systems?",
    "crisis_referral": "How does your AI system detect crisis language and escalate to a human?",
    "impact_assessment": "Have you conducted a risk/impact assessment of your AI deployments?",
    "content_accuracy": "How do you ensure the accuracy of AI-generated content delivered to customers?",
    "bias_audit": "Have you conducted a bias audit of your AI systems?",
    "consent": "How do you obtain informed consent before AI processes personal data?",
    "data_protection": "What technical and organizational measures protect data processed by AI?",
    "model_documentation": "Is each AI model documented with intended use, limitations, and known risks?",
    "validation": "Has your AI system undergone independent validation?",
    "governance_documentation": "Do you have documented governance processes for AI decision-making?",
    "risk_assessment": "Have you mapped and assessed the risks of each AI use case?",
    "transparency": "Can stakeholders understand how your AI system works and makes decisions?",
    "ai_content_marking": "How is AI-generated content identified and marked for recipients?",
    "suitability_controls": "What controls ensure AI recommendations are suitable for the customer?",
    "disclosure": "How do you disclose material facts about AI-generated recommendations?",
    "supervision": "How are AI-generated communications supervised before delivery?",
    "retention_3yr": "Can you retain and produce AI-generated communications for 3+ years?",
    "unsubscribe_mechanism": "Do AI-generated emails include a working opt-out mechanism?",
    "sender_identification": "Do AI-generated emails correctly identify the sender?",
    "consent_management": "How do you manage and record consent for AI data processing?",
    "data_retention_limits": "Do you enforce data retention limits for AI-processed information?",
    "ai_disclosure_on_request": "Can you disclose AI involvement to consumers when they ask?",
}

FIX_SUGGESTIONS: dict[str, tuple[str, str]] = {
    "ai_disclosure": ("Enable AI disclosure in your chatbot policy template", "one_click"),
    "pii_detection": ("Enable PII detection in your policy configuration", "one_click"),
    "injection_detection": ("Enable prompt injection detection", "one_click"),
    "content_filter": ("Enable content filtering with prohibited topics", "one_click"),
    "scope_enforcement": ("Enable scope enforcement with allowed topics", "one_click"),
    "audit_logging": ("Audit logging is automatic with AuditHive", "already_active"),
    "monitoring": ("Monitoring is active through your AuditHive dashboard", "already_active"),
    "minor_protection": ("Configure minor protection controls in your policy", "configuration"),
    "crisis_referral": ("Add crisis detection patterns to your content filter", "configuration"),
    "impact_assessment": ("Document an AI impact assessment (template available in docs)", "documentation"),
    "content_accuracy": ("Enable hallucination detection in your policy", "one_click"),
    "model_documentation": ("Document your AI models using AuditHive's assessment framework", "documentation"),
    "validation": ("Schedule independent validation of your AI outputs", "documentation"),
    "governance_documentation": ("Document governance processes using the Four Questions framework", "documentation"),
    "risk_assessment": ("Complete the AuditHive onboarding profile to map risks", "one_click"),
    "bias_detection": ("Enable bias detection in your policy to flag protected class, proxy variable, and stereotype indicators", "one_click"),
    "bias_audit": ("Conduct a bias audit using AuditHive's bias detection logs and demographic analysis", "documentation"),
}


def _extract_controls_from_policy(config: dict) -> set[str]:
    """Extract enabled control names from a policy config (flat or template format)."""
    controls: set[str] = set()
    # Always-on controls
    controls.add("audit_logging")
    controls.add("monitoring")

    pre_call = config.get("pre_call", config)  # template or flat

    for check_name in ("pii_detection", "injection_detection", "content_filter", "scope_enforcement", "bias_detection"):
        cfg = pre_call.get(check_name, {})
        if isinstance(cfg, dict) and cfg.get("enabled"):
            controls.add(check_name)

    if pre_call.get("ai_disclosure", {}).get("enabled"):
        controls.add("ai_disclosure")

    return controls


async def run_assessment(
    db: AsyncSession,
    customer_id,
    profile: CustomerProfile,
    policies: list[PolicyConfig],
) -> dict:
    """Run the full governance assessment. Returns the response dict."""

    # 1. Query matching regulations
    conditions = [
        RegulatoryMapping.jurisdiction.in_(profile.jurisdictions + ["us_federal"]),
    ]
    result = await db.execute(select(RegulatoryMapping).where(or_(*conditions)))
    all_regs = result.scalars().all()

    # 2. Filter by profile match (industry, use_case, audience wildcards)
    matched_regs = []
    for reg in all_regs:
        industry_match = reg.industry == "any" or reg.industry == profile.industry
        use_case_match = reg.use_case == "any" or reg.use_case in profile.ai_use_cases
        audience_match = reg.audience == "any" or reg.audience in profile.audience_types
        if industry_match and use_case_match and audience_match:
            matched_regs.append(reg)

    # 3. Collect required controls
    control_to_regs: dict[str, list[str]] = {}
    applicable_regulations = []
    for reg in matched_regs:
        applicable_regulations.append({
            "regulation": reg.regulation_name,
            "jurisdiction": reg.jurisdiction,
            "why": f"Applicable based on your profile ({reg.jurisdiction}, {reg.use_case}, {reg.audience})",
        })
        for c in reg.required_controls:
            ctrl = c["control"]
            control_to_regs.setdefault(ctrl, []).append(reg.regulation_name)

    # 4. Determine current controls from policies
    current_controls: set[str] = set()
    for p in policies:
        current_controls |= _extract_controls_from_policy(p.config)

    # 5. Compare
    required_controls_list = []
    missing_controls_list = []
    examiner_questions = []

    for ctrl, regs in sorted(control_to_regs.items()):
        status = "covered" if ctrl in current_controls else "missing"
        required_controls_list.append({"control": ctrl, "required_by": regs, "status": status})
        if status == "missing":
            fix, effort = FIX_SUGGESTIONS.get(ctrl, ("Configure this control in your policy", "configuration"))
            missing_controls_list.append({"control": ctrl, "required_by": regs, "fix": fix, "effort": effort})
            q_template = EXAMINER_TEMPLATES.get(ctrl)
            if q_template:
                examiner_questions.append(f"{q_template} (Required by {', '.join(regs)})")

    # 6. Coverage score
    total_required = len(control_to_regs)
    covered_count = sum(1 for rc in required_controls_list if rc["status"] == "covered")
    coverage_score = round((covered_count / total_required * 100) if total_required else 0.0, 1)

    # 7. Maturity level from coverage
    if coverage_score >= 80:
        maturity_level = "mature"
    elif coverage_score >= 50:
        maturity_level = "developing"
    elif coverage_score > 0:
        maturity_level = "immature"
    else:
        maturity_level = "ungoverned"

    # 8. Four Questions status (auto-detected)
    four_questions = {
        "purpose": {"answered": bool(profile.ai_use_cases), "recommendation": None},
        "working": {"answered": "monitoring" in current_controls, "recommendation": "Enable hallucination detection or quality scoring"},
        "failure": {"answered": False, "recommendation": "Configure violation alerts via email or Slack"},
        "accountability": {"answered": False, "recommendation": "Designate an AI system owner in Settings"},
    }

    # 9. Recommendations
    recommendations = []
    if missing_controls_list:
        one_click = [m for m in missing_controls_list if m["effort"] == "one_click"]
        if one_click:
            recommendations.append(f"Enable {len(one_click)} missing controls with one-click fixes to improve coverage")
    if not policies:
        recommendations.append("Apply a policy template to activate governance immediately")
    if coverage_score < 50:
        recommendations.append("Complete the Four Questions framework to understand your governance gaps")

    # 10. Save assessment
    assessment = GovernanceAssessment(
        customer_id=customer_id,
        applicable_regulations=applicable_regulations,
        required_controls=required_controls_list,
        current_controls=list(current_controls),
        missing_controls=missing_controls_list,
        coverage_score=coverage_score,
        maturity_level=maturity_level,
        four_questions=four_questions,
        examiner_questions=examiner_questions,
    )
    db.add(assessment)
    await db.flush()

    # 11. Upcoming deadlines
    from audithive.regulatory.impact import check_upcoming_deadlines
    try:
        upcoming_deadlines = await check_upcoming_deadlines(db, customer_id, days_ahead=180)
    except Exception:
        upcoming_deadlines = []

    return {
        "assessment_id": assessment.id,
        "coverage_score": coverage_score,
        "maturity_level": maturity_level,
        "applicable_regulations": applicable_regulations,
        "required_controls": required_controls_list,
        "missing_controls": missing_controls_list,
        "examiner_questions": examiner_questions,
        "four_questions": four_questions,
        "recommendations": recommendations,
        "upcoming_deadlines": upcoming_deadlines,
    }
