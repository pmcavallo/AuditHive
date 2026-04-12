# PHASE-5-COMPLETE.md — Differentiating Features (Assessment Layer)

## 1. Phase Goal

Build the three features that transform AuditHive from "a proxy with policy enforcement" into "a product that tells you what governance you're missing": the Governance Assessment Engine, the Described-vs-Established Gap Detector, and the Four Questions Framework with Governance Maturity Score. Pure data + logic, no LLM calls.

## 2. What Was Built

### Database Models (1 modified file)
| File | Change |
|------|--------|
| `src/audithive/db/models.py` | Added `CustomerProfile`, `RegulatoryMapping`, `GovernanceAssessment` models |

### Database Migration (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/db/migrations/versions/002_assessment_tables.py` | Creates 3 new tables with indexes |

### Assessment Engine (3 new files)
| File | Purpose |
|------|---------|
| `src/audithive/assessment/__init__.py` | Package init |
| `src/audithive/assessment/engine.py` | Core assessment: regulatory matching, control coverage, examiner questions, maturity scoring |
| `src/audithive/assessment/gaps.py` | Gap detector: action mismatches, weakened template controls |

### API Routes (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/api/routes/assessment.py` | 5 endpoints: profile CRUD, assessment, gaps, four questions |

### Schemas (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/schemas/assessment.py` | Pydantic models for all assessment endpoints |

### Scripts (1 new file)
| File | Purpose |
|------|---------|
| `scripts/seed_regulatory_mappings.py` | Seeds 15 regulatory mappings (FTC, Colorado AI Act, CCPA, GDPR, SR 11-7, FINRA, etc.) |

### Modified Backend Files
| File | Change |
|------|--------|
| `src/audithive/api/app.py` | Registered assessment router |

### Dashboard (2 modified, 1 new)
| File | Change |
|------|--------|
| `dashboard/src/pages/Assessment.jsx` | **New** — Full assessment page: onboarding form, coverage score, regulation list, controls table, examiner questions, gaps, four questions framework |
| `dashboard/src/pages/Overview.jsx` | **Modified** — Added governance coverage score, maturity badge, gaps count; onboarding prompt if no profile |
| `dashboard/src/api.js` | **Modified** — Added profile, assessment, gaps, four-questions API methods |
| `dashboard/src/components/Sidebar.jsx` | **Modified** — Added Assessment nav item |
| `dashboard/src/App.jsx` | **Modified** — Added Assessment route |

### Tests (6 new files)
| File | Tests |
|------|-------|
| `tests/test_api/test_profile.py` | 4 tests |
| `tests/test_api/test_assessment.py` | 7 tests |
| `tests/test_api/test_gaps.py` | 4 tests |
| `tests/test_api/test_four_questions.py` | 4 tests |
| `tests/test_data/test_regulatory_mappings.py` | 5 tests |
| `tests/conftest_helpers.py` | Shared helper for seeding regulatory mappings in tests |

**Total new files: 13. Modified files: 6.**

## 3. Endpoints Added

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/profile` | API key | Create/update customer onboarding profile |
| GET | `/v1/profile` | API key | Get customer profile |
| GET | `/v1/assessment` | API key | Full governance gap analysis with coverage score |
| GET | `/v1/assessment/gaps` | API key | Described-vs-established gap detection |
| POST | `/v1/assessment/four-questions` | API key | Submit four questions, get maturity score |

## 4. Design Decisions

1. **Regulatory mappings as a seeded database table, not hardcoded** — The `regulatory_mappings` table is the living knowledge base. Seed script inserts 15 regulations. New regulations can be added by extending the seed data. Idempotent (skips existing by `regulation_short`).

2. **Wildcard matching with `'any'`** — A regulation with `industry='any'` applies to all industries. The assessment engine filters by customer profile fields and uses `'any'` as a universal match. This allows broad regulations (NIST RMF, GDPR) to apply to all customers while specific ones (SR 11-7, FINRA) only match financial services.

3. **`audit_logging` and `monitoring` auto-covered** — Having AuditHive = you have audit logging and monitoring. These controls are always marked as "covered" regardless of policy config. This correctly reflects that the product itself provides these capabilities.

4. **Gap detector is config-level, not enforcement-level** — The original spec checked audit logs for flagged-but-not-blocked interactions. This doesn't work when the engine normalizes PII to the most restrictive action. Instead, the gap detector analyzes the raw config directly: if SSN is "block" but email is "flag", that's an action inconsistency gap. This is more reliable and doesn't require enforcement data.

5. **Four Questions cross-references actual system state** — The "failure" question always flags a described-vs-established gap because alerting is not yet implemented. When a customer says "we have alerts" but no alerting is configured, the system catches the lie. This is the key differentiator.

6. **Maturity scoring: 4-tier model** — Mature (4/4 with matching controls), Developing (3+/4), Immature (2/4), Ungoverned (0-1/4). Simple, clear, actionable.

7. **Coverage score = covered / required * 100** — Straightforward ratio. A customer with 3 of 10 required controls covered scores 30%. Adding a policy template can close multiple gaps at once, creating a satisfying coverage jump.

8. **Examiner questions are static templates** — No LLM calls. Each missing control maps to a pre-written question that a regulator would ask. This keeps the assessment deterministic, fast, and free. LLM-powered examiner simulation deferred to Phase 6.

9. **Profile upsert (POST creates or updates)** — Single endpoint handles both create and update. The `customer_profiles` table has a unique constraint on `customer_id`, so each customer has exactly one profile.

10. **Dashboard onboarding prompt on Overview** — If no profile exists, the Overview page shows a blue banner: "Answer 4 questions to see your governance coverage" with a link to the Assessment page. After profile creation, the banner is replaced with coverage metrics.

## 5. Tests

**Total: 106 tests (82 existing + 24 new). All passing. Zero regressions.**

### Phase 1-4 tests (82) — no regressions
All 82 PASSED.

### Phase 5 tests (24)

**Profile (4 tests)**
| Test | Status |
|------|--------|
| `test_profile::test_create_profile` | PASSED |
| `test_profile::test_get_profile` | PASSED |
| `test_profile::test_update_profile_overwrites` | PASSED |
| `test_profile::test_profile_scoped_to_customer` | PASSED |

**Assessment (7 tests)**
| Test | Status |
|------|--------|
| `test_assessment::test_assessment_returns_regulations` | PASSED |
| `test_assessment::test_assessment_identifies_missing_controls` | PASSED |
| `test_assessment::test_coverage_score_computed` | PASSED |
| `test_assessment::test_assessment_no_profile_returns_400` | PASSED |
| `test_assessment::test_assessment_with_policy_improves_coverage` | PASSED |
| `test_assessment::test_examiner_questions_generated` | PASSED |
| `test_assessment::test_assessment_saved_to_database` | PASSED |

**Gap Detector (4 tests)**
| Test | Status |
|------|--------|
| `test_gaps::test_gap_detected_action_mismatch` | PASSED |
| `test_gaps::test_gap_detected_weakened_template` | PASSED |
| `test_gaps::test_no_gaps_when_policy_matches` | PASSED |
| `test_gaps::test_gaps_scoped_to_customer` | PASSED |

**Four Questions (4 tests)**
| Test | Status |
|------|--------|
| `test_four_questions::test_four_questions_returns_maturity` | PASSED |
| `test_four_questions::test_four_questions_detects_gap` | PASSED |
| `test_four_questions::test_maturity_level_correct` | PASSED |
| `test_four_questions::test_partial_answers` | PASSED |

**Regulatory Mappings (5 tests)**
| Test | Status |
|------|--------|
| `test_regulatory_mappings::test_seed_loads_all_mappings` | PASSED |
| `test_regulatory_mappings::test_query_by_jurisdiction` | PASSED |
| `test_regulatory_mappings::test_query_by_industry` | PASSED |
| `test_regulatory_mappings::test_wildcard_matching` | PASSED |
| `test_regulatory_mappings::test_composite_query` | PASSED |

**No tests skipped.**

## 6. Definition of Done Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Alembic migration creates 3 new tables | PASSED |
| 2 | `scripts/seed_regulatory_mappings.py` loads 15 regulatory mappings | PASSED |
| 3 | POST/GET /v1/profile creates and retrieves customer profiles | PASSED |
| 4 | GET /v1/assessment returns full governance gap analysis with coverage score | PASSED |
| 5 | Assessment correctly identifies applicable regulations based on profile | PASSED |
| 6 | Assessment correctly identifies missing controls | PASSED |
| 7 | Coverage score computes correctly (covered/required * 100) | PASSED |
| 8 | Examiner questions generated for each missing control | PASSED |
| 9 | GET /v1/assessment/gaps returns described-vs-established gaps | PASSED |
| 10 | Gap detector catches action mismatches | PASSED |
| 11 | Gap detector catches weakened template controls | PASSED |
| 12 | POST /v1/assessment/four-questions accepts answers and returns maturity score | PASSED |
| 13 | Four Questions cross-references answers against actual configuration | PASSED |
| 14 | Dashboard shows governance coverage score and maturity level on Overview | PASSED |
| 15 | Dashboard has Assessment page with full report | PASSED |
| 16 | Onboarding flow prompts for profile if none exists | PASSED |
| 17 | All new tests pass | PASSED (24/24) |
| 18 | All Phase 1-4 tests still pass (zero regressions) | PASSED (82/82) |
| 19 | `docs/phases/PHASE-5-COMPLETE.md` exists with full summary | PASSED (this file) |

## 7. What Was Deferred

| Item | Deferred To | Reason |
|------|-------------|--------|
| LLM-powered examiner simulation | Phase 6 | Requires LLM agent; current version uses static templates |
| PDF report generation | Phase 6 | Enhancement |
| Regulatory change monitoring | Phase 7 | Requires external data source |
| Proactive regulatory alerts | Phase 7 | Requires monitoring infrastructure |
| Cross-customer data aggregation | Phase 8+ | Platform/flywheel feature |
| Industry benchmarking | Phase 8+ | Requires multi-tenant data |
| Alerting integration (email/Slack) | Phase 6 | Four Questions detects the gap but alerting not built yet |

## 8. How to Run

```bash
# Run all tests (106 tests)
cd C:\Users\pmcav\Projects\AuditHive
py -m pytest tests/ -v

# Seed regulatory mappings (requires running database)
docker compose up -d
py -m alembic upgrade head
py scripts/seed_regulatory_mappings.py
py scripts/seed_templates.py

# Start backend
py -m uvicorn src.audithive.api.app:app --reload

# Start dashboard
cd dashboard && npm run dev

# Create a profile and run assessment via curl
curl -X POST http://localhost:8000/v1/profile \
  -H "Authorization: Bearer ah-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ai_use_cases":["customer_chatbot"],"audience_types":["customers"],"industry":"ecommerce","jurisdictions":["california","colorado"]}'

curl http://localhost:8000/v1/assessment \
  -H "Authorization: Bearer ah-YOUR_KEY"

curl http://localhost:8000/v1/assessment/gaps \
  -H "Authorization: Bearer ah-YOUR_KEY"

curl -X POST http://localhost:8000/v1/assessment/four-questions \
  -H "Authorization: Bearer ah-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"purpose":"Customer chatbot","working":"Weekly review","failure":"Email alerts","accountability":"Jane Doe"}'
```
