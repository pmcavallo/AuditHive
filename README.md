# AuditHive

**AI governance middleware for companies that deploy LLMs and need to prove they're working correctly.**

AuditHive sits between your application and your LLM provider. One endpoint change. Every call is intercepted, policies are enforced, and everything is logged to an immutable audit trail. You get governance without rebuilding your stack.

<!-- SCREENSHOT: Place dashboard screenshot here -->
<!-- ![AuditHive Dashboard](docs/images/dashboard-overview.png) -->

> **Live Demo:** [View the dashboard →](https://pmcavallo.github.io/AuditHive/)
>
> The demo uses pre-built example data. No API calls, no backend required.

---

## What It Does

**For the business:** Your chatbot told a customer the wrong refund policy last week. You found out from Twitter. AuditHive catches it before they do.

**For compliance:** Your advisors are using AI to draft client emails. FINRA wants to see your governance framework. AuditHive generates the examiner-ready report.

**For engineering:** Your board is asking about AI governance because enterprise customers are asking about it in security questionnaires. AuditHive gives you the answer.

### Core Capabilities

- **Policy enforcement** — PII detection, prompt injection blocking, content filtering, and scope enforcement run on every LLM call before it reaches the provider
- **Governance assessment** — Answer four questions about your AI setup and get a full gap analysis: which regulations apply, which controls you're missing, and your coverage score
- **Examiner simulation** — Weekly digest that translates your audit data into "if an examiner reviewed this week, here's what they'd ask"
- **Described-vs-established gap detection** — Compares what your policy says it does against what enforcement data shows it actually does
- **Regulatory impact assessment** — When a regulation changes, AuditHive tells you whether it affects your specific setup, what you need to change, and the deadline
- **Governance maturity scoring** — Four questions framework: What is the system's purpose? How do you know it's working? What happens when it breaks? Who is accountable?
- **Alerting** — Email and webhook notifications on policy violations
- **Audit trail** — Every interaction logged with full context, searchable and filterable

---

## Architecture

```
Your App
    │ (one API endpoint change)
    ▼
┌─────────────────────────────────────────┐
│            AUDITHIVE MIDDLEWARE          │
│                                         │
│  Pre-call checks ──► LLM Provider ──►   │
│  (PII, injection,    (pass-through)     │
│   content, scope)         │             │
│         │            Post-call eval     │
│         ▼                 │             │
│  ┌────────────┐    ┌─────────────┐      │
│  │ Policy     │    │ Audit Trail │      │
│  │ Engine     │    │ (immutable) │      │
│  └────────────┘    └─────────────┘      │
│         │                 │             │
│    Assessment    ◄── Regulatory ──►     │
│    Engine            Intelligence       │
└─────────┬───────────────────┬───────────┘
          ▼                   ▼
   Governed response    Dashboard
   back to your app     + Reports
```

### Integration

```python
# Before (direct to OpenAI):
client = OpenAI(api_key="sk-...")

# After (through AuditHive):
client = OpenAI(
    api_key="ah-...",
    base_url="http://localhost:8000/v1",
    default_headers={"X-LLM-Key": "sk-..."}
)
# That's it. Your code doesn't change. Governance is automatic.
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11+, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16+ with Row-Level Security |
| Dashboard | React 18, Tailwind CSS, Recharts, Vite |
| Security | AES-256-GCM encryption at rest, bcrypt API key hashing |
| LLM Integration | Anthropic Claude (examiner simulation), OpenAI-compatible proxy |
| Testing | pytest, 163 tests across 8 phases |

---

## Key Features

### Governance Assessment Engine

Answer four onboarding questions — what your AI does, who uses it, your industry, your jurisdictions — and AuditHive generates:

- Applicable regulations (mapped from a database of 15+ US and international AI laws)
- Required controls vs. what you currently have configured
- Coverage score (percentage of required controls in place)
- Examiner questions (what a regulator would ask about your gaps)
- One-click remediation recommendations

### Policy Templates

Pre-built, regulation-grounded policy templates for common use cases:

| Template | Risk Level | Grounded In |
|----------|-----------|-------------|
| Customer-facing chatbot | High | FTC, Colorado AI Act, CA SB 243, EU AI Act, NIST AI RMF |
| Document generation | Medium | CCPA/GDPR, NIST AI 600-1, ISO 42001 |
| Email automation | Medium | CAN-SPAM, FTC, CA AI Transparency Act |

Each template is customizable. Apply one, adjust thresholds, and governance is active immediately.

### Examiner Simulation

An LLM-powered agent (with static fallback) that reviews your governance data and generates findings in examiner language:

- Executive summary and risk rating
- Structured findings with severity, evidence, and remediation
- Questions an examiner would ask about your specific gaps
- Prioritized recommendations

### Regulatory Timeline

Tracks upcoming regulatory deadlines and assesses their impact on your specific setup:

- Colorado AI Act enforcement (June 2026)
- EU AI Act high-risk rules (August 2026)
- California AI Transparency Act (August 2026)
- And more, continuously updated

Each deadline includes a personalized impact assessment: why it affects you, what controls you're missing, and the fix.

---

## Security

- **Encryption at rest:** AES-256-GCM encryption of audit log content (prompts and responses)
- **Tenant isolation:** PostgreSQL Row-Level Security prevents cross-tenant access at the database level
- **API key security:** Customer LLM keys are pass-through only, never stored, never logged
- **AI opt-in:** Third-party LLM features require explicit customer consent (default: off)
- **Data lifecycle:** Full data export (GDPR Article 20) and permanent deletion (GDPR Article 17) endpoints
- **163 tests** including dedicated security test suite verifying encryption, key safety, and tenant isolation

---

## Project Structure

```
AuditHive/
├── src/audithive/
│   ├── api/            # FastAPI routes (chat, policies, audit, assessment, reports, alerts, regulatory)
│   ├── assessment/     # Governance assessment engine, gap detector
│   ├── policy/         # Policy engine, check functions, templates
│   ├── examiner/       # LLM-powered examiner simulation agent
│   ├── regulatory/     # Regulatory impact assessment engine
│   ├── reports/        # HTML governance report generator
│   ├── alerts/         # Email + webhook alert dispatcher
│   ├── audit/          # Immutable audit trail logger
│   ├── core/           # Config, encryption, security
│   ├── db/             # SQLAlchemy models, migrations
│   └── schemas/        # Pydantic request/response models
├── dashboard/          # React + Tailwind dashboard
├── tests/              # 163 tests across 8 phases
├── scripts/            # Seed data, key generation
└── docs/phases/        # Phase completion summaries (1-8)
```

---

## Build History

Built in 8 phases with comprehensive test coverage and zero regressions across all phases:

| Phase | What | Tests |
|-------|------|-------|
| 1 | Foundation (FastAPI, PostgreSQL, auth, API keys) | 11 |
| 2 | Core middleware (OpenAI proxy, policy engine, audit logging) | 44 |
| 3 | Policy templates (3 templates, deep merge customization) | 22 |
| 4 | React dashboard (overview, audit trail, policies, templates) | 5 |
| 5 | Assessment engine, gap detector, four questions framework | 24 |
| 6 | Examiner simulation, HTML reports, alerting | 20 |
| 7 | Regulatory impact assessment, timeline | 18 |
| 8 | Security hardening (encryption, RLS, data lifecycle) | 19 |
| **Total** | | **163** |

---

## Running Locally

```bash
# Clone and install
git clone https://github.com/pmcavallo/AuditHive.git
cd AuditHive
pip install -e ".[dev]"

# Start PostgreSQL
docker compose up -d

# Run migrations and seed data
py -m alembic upgrade head
py scripts/seed_templates.py
py scripts/seed_regulatory_mappings.py
py scripts/seed_regulatory_updates.py

# Generate encryption key (optional but recommended)
py scripts/generate_encryption_key.py
# Add output to .env as AUDITHIVE_ENCRYPTION_KEY=...

# Start backend
py -m uvicorn src.audithive.api.app:app --reload

# Start dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

## Running Tests

```bash
py -m pytest tests/ -v
# 163 passed, 2 skipped (RLS tests require PostgreSQL)
```

---

## Author

**Paulo Cavallo, Ph.D.**

AI governance and model risk professional with 5+ years developing credit risk models under SR 11-7 in financial services. Author of [AI Under Audit](https://pmcavallo.github.io), a practitioner newsletter on AI governance in regulated industries.

- [Portfolio](https://pmcavallo.github.io)
- [LinkedIn](https://linkedin.com/in/paulocavallo)
- [Newsletter](https://pmcavallo.github.io)

---

## License

This project is proprietary. All rights reserved. See [LICENSE](LICENSE) for details.
