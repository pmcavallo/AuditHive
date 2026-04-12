"""Seed the regulatory_mappings table with the initial knowledge base."""

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from audithive.core.config import settings
from audithive.db.models import RegulatoryMapping

MAPPINGS = [
    {
        "regulation_name": "FTC Chatbot Guidance",
        "regulation_short": "FTC-Chat",
        "jurisdiction": "us_federal",
        "industry": "any",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_disclosure", "reason": "FTC treats chatbot outputs as company representations"},
            {"control": "content_accuracy", "reason": "Deceptive statements by chatbot = company liability"},
            {"control": "audit_logging", "reason": "Must demonstrate compliance upon investigation"},
        ],
    },
    {
        "regulation_name": "Colorado AI Act",
        "regulation_short": "CO-AI",
        "jurisdiction": "colorado",
        "industry": "any",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_disclosure", "reason": "Colorado AI Act requires chatbot disclosure regardless of risk level"},
            {"control": "impact_assessment", "reason": "High-risk deployers must conduct impact assessments"},
        ],
        "enforcement_date": date(2026, 2, 1),
    },
    {
        "regulation_name": "California SB 243",
        "regulation_short": "CA-SB243",
        "jurisdiction": "california",
        "industry": "any",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_disclosure", "reason": "Disclosure required for AI interactions"},
            {"control": "minor_protection", "reason": "Additional protections for users under 18"},
            {"control": "crisis_referral", "reason": "Must detect crisis language and route to human"},
        ],
    },
    {
        "regulation_name": "California AI Transparency Act",
        "regulation_short": "CA-AIT",
        "jurisdiction": "california",
        "industry": "any",
        "use_case": "any",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_content_marking", "reason": "AI-generated content must be identifiable"},
        ],
    },
    {
        "regulation_name": "Utah AI Policy Act",
        "regulation_short": "UT-AI",
        "jurisdiction": "utah",
        "industry": "any",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_disclosure_on_request", "reason": "Must disclose AI use when consumer asks"},
        ],
    },
    {
        "regulation_name": "EU AI Act Article 52",
        "regulation_short": "EU-AI-52",
        "jurisdiction": "eu",
        "industry": "any",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "ai_disclosure", "reason": "Transparency obligation for AI-human interaction"},
            {"control": "transparency", "reason": "Users must be informed they are interacting with AI"},
        ],
    },
    {
        "regulation_name": "California Consumer Privacy Act",
        "regulation_short": "CCPA",
        "jurisdiction": "california",
        "industry": "any",
        "use_case": "any",
        "audience": "customers",
        "required_controls": [
            {"control": "pii_detection", "reason": "CCPA requires protection of personal information"},
            {"control": "data_protection", "reason": "Reasonable security for consumer data"},
            {"control": "audit_logging", "reason": "Must respond to consumer access/deletion requests"},
        ],
    },
    {
        "regulation_name": "General Data Protection Regulation",
        "regulation_short": "GDPR",
        "jurisdiction": "eu",
        "industry": "any",
        "use_case": "any",
        "audience": "any",
        "required_controls": [
            {"control": "pii_detection", "reason": "GDPR requires protection of personal data"},
            {"control": "data_protection", "reason": "Data protection by design and default"},
            {"control": "consent_management", "reason": "Lawful basis required for data processing"},
            {"control": "audit_logging", "reason": "Accountability principle requires processing records"},
        ],
    },
    {
        "regulation_name": "CAN-SPAM Act",
        "regulation_short": "CAN-SPAM",
        "jurisdiction": "us_federal",
        "industry": "any",
        "use_case": "email_automation",
        "audience": "customers",
        "required_controls": [
            {"control": "unsubscribe_mechanism", "reason": "Must include opt-out mechanism in commercial email"},
            {"control": "sender_identification", "reason": "Accurate From/Reply-To and physical address required"},
        ],
    },
    {
        "regulation_name": "SR 11-7: Guidance on Model Risk Management",
        "regulation_short": "SR 11-7",
        "jurisdiction": "us_federal",
        "industry": "financial_services",
        "use_case": "any",
        "audience": "any",
        "required_controls": [
            {"control": "model_documentation", "reason": "All models must be documented with intended use and limitations"},
            {"control": "validation", "reason": "Independent validation of model performance"},
            {"control": "monitoring", "reason": "Ongoing monitoring of model outcomes"},
            {"control": "audit_logging", "reason": "Examination readiness requires complete audit trail"},
        ],
    },
    {
        "regulation_name": "FINRA Rule 3110 (Supervision)",
        "regulation_short": "FINRA-3110",
        "jurisdiction": "us_federal",
        "industry": "financial_services",
        "use_case": "email_automation",
        "audience": "customers",
        "required_controls": [
            {"control": "supervision", "reason": "Supervisory review of client communications"},
            {"control": "retention_3yr", "reason": "Client communications retained for 3 years"},
            {"control": "audit_logging", "reason": "Must produce communications for examination"},
        ],
    },
    {
        "regulation_name": "FINRA Regulation Best Interest",
        "regulation_short": "FINRA-RegBI",
        "jurisdiction": "us_federal",
        "industry": "financial_services",
        "use_case": "customer_chatbot",
        "audience": "customers",
        "required_controls": [
            {"control": "suitability_controls", "reason": "Recommendations must be in client's best interest"},
            {"control": "disclosure", "reason": "Must disclose material facts about recommendation"},
        ],
    },
    {
        "regulation_name": "NYC Local Law 144 (Automated Employment Decision Tools)",
        "regulation_short": "NYC-LL144",
        "jurisdiction": "new_york",
        "industry": "any",
        "use_case": "hr_recruitment",
        "audience": "any",
        "required_controls": [
            {"control": "bias_audit", "reason": "Annual bias audit required for automated hiring tools"},
            {"control": "transparency", "reason": "Candidates must be notified of AI use"},
        ],
    },
    {
        "regulation_name": "Illinois AI Video Interview Act",
        "regulation_short": "IL-AIVIA",
        "jurisdiction": "illinois",
        "industry": "any",
        "use_case": "hr_recruitment",
        "audience": "any",
        "required_controls": [
            {"control": "consent", "reason": "Applicant consent required before AI analysis of video interview"},
            {"control": "data_retention_limits", "reason": "Video must be destroyed within 30 days of request"},
        ],
    },
    {
        "regulation_name": "NIST AI Risk Management Framework",
        "regulation_short": "NIST-RMF",
        "jurisdiction": "us_federal",
        "industry": "any",
        "use_case": "any",
        "audience": "any",
        "required_controls": [
            {"control": "risk_assessment", "reason": "AI systems must undergo risk assessment"},
            {"control": "monitoring", "reason": "Continuous monitoring for performance and compliance"},
            {"control": "governance_documentation", "reason": "Document governance processes and decisions"},
        ],
    },
]


async def seed(db: AsyncSession) -> int:
    """Insert regulatory mappings. Returns count of inserted rows."""
    existing = await db.execute(select(RegulatoryMapping.regulation_short))
    existing_shorts = {r[0] for r in existing.all()}

    count = 0
    for m in MAPPINGS:
        if m["regulation_short"] in existing_shorts:
            continue
        row = RegulatoryMapping(
            regulation_name=m["regulation_name"],
            regulation_short=m["regulation_short"],
            jurisdiction=m["jurisdiction"],
            industry=m.get("industry", "any"),
            use_case=m.get("use_case", "any"),
            audience=m.get("audience", "any"),
            required_controls=m["required_controls"],
            enforcement_date=m.get("enforcement_date"),
        )
        db.add(row)
        count += 1

    await db.flush()
    return count


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        count = await seed(session)
        await session.commit()
    await engine.dispose()
    print(f"Seeded {count} regulatory mappings ({len(MAPPINGS)} total defined, skipped existing).")


if __name__ == "__main__":
    asyncio.run(main())
