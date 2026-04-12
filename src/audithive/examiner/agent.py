"""Examiner simulation agent — LLM-powered with static fallback."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from audithive.core.config import settings
from audithive.examiner.prompts import EXAMINER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class ExaminerFinding:
    title: str
    severity: str
    description: str
    evidence: str
    regulation: str
    remediation: str


@dataclass
class ExaminerReportData:
    executive_summary: str
    risk_rating: str
    findings: list[ExaminerFinding] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ExaminerContext:
    industry: str
    jurisdictions: list[str]
    ai_use_cases: list[str]
    coverage_score: float
    maturity_level: str
    applicable_regulations: list[dict]
    missing_controls: list[dict]
    gaps: list[dict]
    four_questions: dict
    total_calls: int
    total_blocked: int
    total_flagged: int
    violation_details: list[dict]
    active_policies: list[dict]


def _build_user_message(ctx: ExaminerContext) -> str:
    """Build the user message containing all governance data for the LLM."""
    return json.dumps({
        "company_profile": {
            "industry": ctx.industry,
            "jurisdictions": ctx.jurisdictions,
            "ai_use_cases": ctx.ai_use_cases,
        },
        "assessment": {
            "coverage_score": ctx.coverage_score,
            "maturity_level": ctx.maturity_level,
            "applicable_regulations": ctx.applicable_regulations[:10],
            "missing_controls": ctx.missing_controls[:10],
        },
        "gaps": ctx.gaps[:5],
        "four_questions": ctx.four_questions,
        "audit_summary": {
            "total_calls": ctx.total_calls,
            "total_blocked": ctx.total_blocked,
            "total_flagged": ctx.total_flagged,
            "recent_violations": ctx.violation_details[:5],
        },
        "active_policies_count": len(ctx.active_policies),
    }, indent=2)


def _generate_static_report(ctx: ExaminerContext) -> ExaminerReportData:
    """Generate a template-based report without LLM. Used as fallback."""
    findings: list[ExaminerFinding] = []

    if ctx.coverage_score < 50:
        findings.append(ExaminerFinding(
            title="Governance Coverage Below Threshold",
            severity="high",
            description=f"The institution's AI governance coverage score is {ctx.coverage_score}%, below the recommended 50% minimum.",
            evidence=f"Assessment identified {len(ctx.missing_controls)} missing controls.",
            regulation="NIST AI RMF",
            remediation="Apply recommended policy templates to close control gaps.",
        ))

    for mc in ctx.missing_controls[:5]:
        findings.append(ExaminerFinding(
            title=f"Missing Control: {mc['control']}",
            severity="medium",
            description=f"The required control '{mc['control']}' is not implemented.",
            evidence=f"Required by: {', '.join(mc.get('required_by', []))}",
            regulation=mc.get("required_by", ["General"])[0],
            remediation=mc.get("fix", "Enable this control in your policy configuration."),
        ))

    for gap in ctx.gaps[:3]:
        findings.append(ExaminerFinding(
            title=f"Gap: {gap.get('gap_type', 'Unknown')}",
            severity="high" if gap.get("risk") == "high" else "medium",
            description=gap.get("description", ""),
            evidence="Detected by described-vs-established gap analysis.",
            regulation="Internal governance standards",
            remediation=gap.get("fix", "Review and align policy configuration."),
        ))

    risk_rating = "high" if ctx.coverage_score < 40 else "medium" if ctx.coverage_score < 70 else "low"

    summary = (
        f"The institution operates {len(ctx.ai_use_cases)} AI use case(s) "
        f"with a governance coverage score of {ctx.coverage_score}% "
        f"({ctx.maturity_level} maturity). "
        f"{len(ctx.missing_controls)} required controls are not implemented."
    )

    questions = [
        f"How does the institution plan to address the {len(ctx.missing_controls)} missing governance controls?",
        "What is the timeline for achieving full regulatory compliance for AI systems?",
    ]

    recommendations = [
        f"Close {len(ctx.missing_controls)} control gaps to improve coverage score.",
    ]
    if ctx.gaps:
        recommendations.append(f"Remediate {len(ctx.gaps)} described-vs-established gap(s).")

    return ExaminerReportData(
        executive_summary=summary,
        risk_rating=risk_rating,
        findings=findings,
        questions=questions,
        recommendations=recommendations,
    )


async def generate_examiner_report(
    context: ExaminerContext,
    api_key: str | None = None,
) -> ExaminerReportData:
    """Generate an examiner report. Uses Claude if API key available, otherwise static."""
    key = api_key or settings.ANTHROPIC_API_KEY
    if not key:
        return _generate_static_report(context)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=EXAMINER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_message(context)}],
        )

        raw = message.content[0].text
        data = json.loads(raw)

        findings = [
            ExaminerFinding(**f) for f in data.get("findings", [])
        ]
        return ExaminerReportData(
            executive_summary=data.get("executive_summary", ""),
            risk_rating=data.get("risk_rating", "medium"),
            findings=findings,
            questions=data.get("questions", []),
            recommendations=data.get("recommendations", []),
        )
    except Exception as e:
        logger.warning("LLM examiner failed, falling back to static: %s", e)
        return _generate_static_report(context)
