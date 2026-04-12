"""Seed regulatory_updates table with known upcoming regulatory changes."""

import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from audithive.core.config import settings
from audithive.db.models import RegulatoryUpdate

UPDATES = [
    {
        "title": "Colorado AI Act enforcement begins",
        "summary": "The Colorado AI Act (SB 25B-004) becomes enforceable. Companies deploying AI that interacts with Colorado consumers must provide AI disclosure regardless of risk classification.",
        "regulation_short": "CO-AI",
        "regulation_name": "Colorado AI Act",
        "update_type": "enforcement_start",
        "jurisdiction": "colorado",
        "industries": ["any"],
        "use_cases": ["customer_chatbot"],
        "audiences": ["customers"],
        "required_actions": [
            {"action": "Enable AI disclosure in customer-facing chatbot", "control": "ai_disclosure", "effort": "one_click", "deadline": "2026-06-30"},
            {"action": "Conduct impact assessment for high-risk AI deployments", "control": "impact_assessment", "effort": "multi_step", "deadline": "2026-06-30"},
        ],
        "affected_controls": ["ai_disclosure", "impact_assessment"],
        "severity": "high",
        "effective_date": date(2025, 5, 17),
        "enforcement_date": date(2026, 6, 30),
        "deadline": date(2026, 6, 30),
        "source_name": "Colorado Legislature",
    },
    {
        "title": "EU AI Act high-risk AI system rules take effect",
        "summary": "Rules for high-risk AI systems under the EU AI Act become applicable. Providers and deployers must implement risk management, data governance, technical documentation, transparency, human oversight, and accuracy requirements.",
        "regulation_short": "EU-AI-HR",
        "regulation_name": "EU AI Act (High-Risk Systems)",
        "update_type": "enforcement_start",
        "jurisdiction": "eu",
        "industries": ["any"],
        "use_cases": ["any"],
        "audiences": ["any"],
        "required_actions": [
            {"action": "Assess whether your AI system qualifies as high-risk under EU AI Act", "control": "risk_assessment", "effort": "multi_step", "deadline": "2026-08-02"},
            {"action": "Implement risk management system per Article 9", "control": "governance_documentation", "effort": "multi_step", "deadline": "2026-08-02"},
            {"action": "Ensure AI-generated content is identifiable", "control": "ai_content_marking", "effort": "one_click", "deadline": "2026-08-02"},
        ],
        "affected_controls": ["risk_assessment", "governance_documentation", "ai_content_marking", "transparency", "monitoring"],
        "severity": "critical",
        "enforcement_date": date(2026, 8, 2),
        "deadline": date(2026, 8, 2),
        "source_name": "European Commission",
    },
    {
        "title": "California AI Transparency Act enforcement begins",
        "summary": "California's AI Transparency Act (SB 942, AB 853) becomes enforceable. Large generative AI providers must implement AI detection tools and content disclosures. Violations carry $5,000 daily penalties.",
        "regulation_short": "CA-AIT",
        "regulation_name": "California AI Transparency Act",
        "update_type": "enforcement_start",
        "jurisdiction": "california",
        "industries": ["any"],
        "use_cases": ["any"],
        "audiences": ["customers"],
        "required_actions": [
            {"action": "Implement AI-generated content marking", "control": "ai_content_marking", "effort": "one_click", "deadline": "2026-08-02"},
        ],
        "affected_controls": ["ai_content_marking"],
        "severity": "high",
        "enforcement_date": date(2026, 8, 2),
        "deadline": date(2026, 8, 2),
        "source_name": "California Legislature",
    },
    {
        "title": "New York RAISE Act expected approval",
        "summary": "New York's RAISE Act introduces AI governance requirements including transparency and safety provisions.",
        "regulation_short": "NY-RAISE",
        "regulation_name": "New York RAISE Act",
        "update_type": "new_law",
        "jurisdiction": "new_york",
        "industries": ["any"],
        "use_cases": ["any"],
        "audiences": ["customers"],
        "required_actions": [
            {"action": "Monitor for final passage and implementation timeline", "control": "governance_documentation", "effort": "monitor"},
        ],
        "affected_controls": ["ai_disclosure", "governance_documentation"],
        "severity": "medium",
        "source_name": "New York Legislature",
    },
    {
        "title": "FTC intensifies AI chatbot scrutiny for minors",
        "summary": "The FTC launched an inquiry into companies operating consumer-facing AI chatbots, seeking information about chatbot interactions with children and teens. Enforcement actions expected.",
        "regulation_short": "FTC-Minors",
        "regulation_name": "FTC AI Chatbot Inquiry (Minors)",
        "update_type": "guidance",
        "jurisdiction": "us_federal",
        "industries": ["any"],
        "use_cases": ["customer_chatbot"],
        "audiences": ["customers"],
        "required_actions": [
            {"action": "Review chatbot for minor interaction safeguards", "control": "minor_protection", "effort": "multi_step"},
            {"action": "Implement age-appropriate content filtering", "control": "content_accuracy", "effort": "multi_step"},
        ],
        "affected_controls": ["minor_protection", "content_accuracy"],
        "severity": "medium",
        "source_name": "Federal Trade Commission",
    },
    {
        "title": "NIST releases AI RMF Profile for Critical Infrastructure",
        "summary": "NIST released a concept note for an AI RMF Profile on Trustworthy AI in Critical Infrastructure. Signals future expectations for organizations in financial services, healthcare, and energy.",
        "regulation_short": "NIST-CI",
        "regulation_name": "NIST AI RMF Critical Infrastructure Profile",
        "update_type": "guidance",
        "jurisdiction": "us_federal",
        "industries": ["financial_services", "healthcare"],
        "use_cases": ["any"],
        "audiences": ["any"],
        "required_actions": [
            {"action": "Review AI RMF Critical Infrastructure profile for applicability", "control": "risk_assessment", "effort": "multi_step"},
            {"action": "Ensure governance documentation aligns with NIST recommendations", "control": "governance_documentation", "effort": "multi_step"},
        ],
        "affected_controls": ["risk_assessment", "governance_documentation", "monitoring"],
        "severity": "low",
        "effective_date": date(2026, 4, 7),
        "source_name": "NIST",
    },
    {
        "title": "White House National AI Policy Framework released",
        "summary": "The White House released a National Policy Framework for AI with legislative recommendations. Signals intent toward federal AI standards that could preempt state laws.",
        "regulation_short": "WH-Framework",
        "regulation_name": "White House National AI Policy Framework",
        "update_type": "guidance",
        "jurisdiction": "us_federal",
        "industries": ["any"],
        "use_cases": ["any"],
        "audiences": ["any"],
        "required_actions": [
            {"action": "Monitor for federal legislation based on framework recommendations", "control": "governance_documentation", "effort": "monitor"},
        ],
        "affected_controls": ["governance_documentation"],
        "severity": "low",
        "effective_date": date(2026, 3, 20),
        "source_name": "White House",
    },
]


async def seed(db: AsyncSession) -> int:
    """Insert regulatory updates. Returns count of inserted rows."""
    existing = await db.execute(select(RegulatoryUpdate.regulation_short))
    existing_shorts = {r[0] for r in existing.all() if r[0]}

    count = 0
    for u in UPDATES:
        if u.get("regulation_short") and u["regulation_short"] in existing_shorts:
            continue
        row = RegulatoryUpdate(
            title=u["title"],
            summary=u["summary"],
            regulation_short=u.get("regulation_short"),
            regulation_name=u.get("regulation_name"),
            update_type=u["update_type"],
            jurisdiction=u["jurisdiction"],
            industries=u.get("industries", ["any"]),
            use_cases=u.get("use_cases", ["any"]),
            audiences=u.get("audiences", ["any"]),
            required_actions=u.get("required_actions", []),
            affected_controls=u.get("affected_controls", []),
            severity=u.get("severity", "medium"),
            effective_date=u.get("effective_date"),
            enforcement_date=u.get("enforcement_date"),
            deadline=u.get("deadline"),
            source_name=u.get("source_name"),
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
    print(f"Seeded {count} regulatory updates ({len(UPDATES)} total defined).")


if __name__ == "__main__":
    asyncio.run(main())
