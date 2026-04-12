# PHASE-6-COMPLETE.md — Examiner Simulation, Reports & Alerting

## 1. Phase Goal

Build the three features that turn AuditHive data into actionable intelligence for compliance buyers: an LLM-powered examiner simulation agent (with static fallback), an examiner-ready HTML governance report with all 11 sections, and a real-time alerting system (email + webhook) integrated into the chat endpoint.

## 2. What Was Built

### Database Models + Migration (2 files)
| File | Purpose |
|------|---------|
| `src/audithive/db/models.py` | **Modified** — Added `AlertConfig`, `AlertHistory`, `ExaminerReport` models |
| `src/audithive/db/migrations/versions/003_alerts_and_reports.py` | Creates 3 new tables |

### Config (1 modified)
| File | Change |
|------|--------|
| `src/audithive/core/config.py` | Added `ANTHROPIC_API_KEY`, `SMTP_*`, `WEBHOOK_TIMEOUT_SECONDS` settings |

### Examiner Agent (3 new files)
| File | Purpose |
|------|---------|
| `src/audithive/examiner/__init__.py` | Package init |
| `src/audithive/examiner/prompts.py` | Full examiner system prompt (SR 11-7 perspective, four questions, examiner language) |
| `src/audithive/examiner/agent.py` | `generate_examiner_report()` — LLM via Claude Sonnet 4.6 with static fallback |

### Report Generator (3 new files)
| File | Purpose |
|------|---------|
| `src/audithive/reports/__init__.py` | Package init |
| `src/audithive/reports/generator.py` | `generate_governance_report()` — gathers all data, renders Jinja2 HTML, saves to DB |
| `src/audithive/reports/templates/governance_report.html` | Professional 11-section HTML template (print-optimized, AuditHive navy branding) |

### Alerting System (5 new files)
| File | Purpose |
|------|---------|
| `src/audithive/alerts/__init__.py` | Package init |
| `src/audithive/alerts/dispatcher.py` | `dispatch_alert()` — checks config, sends to channels, logs to history |
| `src/audithive/alerts/channels/__init__.py` | Package init |
| `src/audithive/alerts/channels/email.py` | SMTP email channel |
| `src/audithive/alerts/channels/webhook.py` | HTTP POST webhook channel |

### API Routes (3 new files)
| File | Purpose |
|------|---------|
| `src/audithive/api/routes/reports.py` | POST generate, GET download, GET list, POST weekly-digest |
| `src/audithive/api/routes/alerts.py` | GET/POST config, GET history, POST test |
| `src/audithive/schemas/reports.py` | Pydantic models for reports and alerts |

### Modified Backend Files
| File | Change |
|------|--------|
| `src/audithive/api/app.py` | Registered reports and alerts routers |
| `src/audithive/api/routes/chat.py` | Integrated alert dispatch on block/flag |

### Dashboard (4 new/modified files)
| File | Change |
|------|--------|
| `dashboard/src/pages/Reports.jsx` | **New** — Generate, download, and list reports with period selector |
| `dashboard/src/pages/Alerts.jsx` | **New** — Alert config form, test button, alert history table |
| `dashboard/src/api.js` | **Modified** — Added reports and alerts API methods |
| `dashboard/src/components/Sidebar.jsx` | **Modified** — Added Reports and Alerts nav items |
| `dashboard/src/App.jsx` | **Modified** — Added Reports and Alerts routes |

### Tests (4 new files)
| File | Tests |
|------|-------|
| `tests/test_examiner/test_agent.py` | 6 tests |
| `tests/test_reports/test_generator.py` | 5 tests |
| `tests/test_alerts/test_dispatcher.py` | 5 tests |
| `tests/test_alerts/test_config.py` | 4 tests |

**Total new files: 20. Modified files: 6.**

## 3. Endpoints Added

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/reports/generate` | API key | Generate governance report on demand |
| GET | `/v1/reports/{id}/download` | API key | Download report as HTML |
| GET | `/v1/reports` | API key | List all generated reports |
| POST | `/v1/reports/weekly-digest` | API key | Generate weekly digest report |
| GET | `/v1/alerts/config` | API key | Get alert configuration |
| POST | `/v1/alerts/config` | API key | Create/update alert configuration |
| GET | `/v1/alerts/history` | API key | List alert history |
| POST | `/v1/alerts/test` | API key | Send test alert to all channels |

## 4. Design Decisions

1. **HTML reports instead of PDF** — WeasyPrint requires Cairo/Pango system libraries that are painful on Windows. The report is generated as HTML (print-optimized with CSS page breaks and A4 styling). Customers can print-to-PDF from the browser. This is simpler, dependency-free, and produces better output than most PDF libraries.

2. **LLM agent with static fallback** — If `ANTHROPIC_API_KEY` is not configured, `generate_examiner_report()` falls back to `_generate_static_report()` which produces the same structured output using template logic. Tests work without an API key. Production gets LLM intelligence.

3. **Alert dispatch is inline (awaited), not fire-and-forget** — Initially used `asyncio.create_task()` for non-blocking dispatch, but this caused SQLAlchemy session state errors in tests (and would in production). Changed to `await dispatch_alert()` inline. The performance impact is negligible since alerts without SMTP/webhook configured are just DB writes.

4. **`report_html` column instead of `pdf_path`** — The report HTML is stored directly in the database for simplicity. No file system, no S3 bucket, no cleanup needed. For a 30KB HTML report, this is efficient. The model stores `report_html` instead of `pdf_path` from the spec.

5. **Alert config upsert (POST creates or updates)** — Single endpoint handles both. Each customer has one alert configuration. Simpler than separate create/update endpoints.

6. **Examiner system prompt encodes SR 11-7 examiner perspective** — The prompt explicitly instructs Claude to think like a regulatory examiner: prioritize by consumer risk, write in examiner language ("the institution has not implemented..."), cross-reference the four questions, and produce structured findings with evidence.

7. **Report template has 11 sections matching spec** — Cover, executive summary, governance overview, applicable regulations, controls assessment, examiner findings, gaps, four questions, audit trail summary, recommendations, footer.

8. **Webhook payload includes `event`, `timestamp`, `details`** — Standard webhook format compatible with Slack incoming webhooks and any HTTP listener.

## 5. Tests

**Total: 126 tests (106 existing + 20 new). All passing. Zero regressions.**

### Phase 1-5 tests (106) — no regressions
All 106 PASSED.

### Phase 6 tests (20)

**Examiner Agent (6 tests)**
| Test | Status |
|------|--------|
| `test_agent::test_static_report_valid_structure` | PASSED |
| `test_agent::test_static_findings_have_all_fields` | PASSED |
| `test_agent::test_static_risk_rating_high_when_low_coverage` | PASSED |
| `test_agent::test_static_risk_rating_low_when_high_coverage` | PASSED |
| `test_agent::test_agent_falls_back_when_no_api_key` | PASSED |
| `test_agent::test_agent_parses_llm_response` | PASSED |

**Report Generator (5 tests)**
| Test | Status |
|------|--------|
| `test_generator::test_generate_report` | PASSED |
| `test_generator::test_download_report_returns_html` | PASSED |
| `test_generator::test_report_contains_key_sections` | PASSED |
| `test_generator::test_report_saved_to_database` | PASSED |
| `test_generator::test_report_list_scoped_to_customer` | PASSED |

**Alert Dispatcher (5 tests)**
| Test | Status |
|------|--------|
| `test_dispatcher::test_alert_dispatched_on_block` | PASSED |
| `test_dispatcher::test_alert_not_dispatched_when_disabled` | PASSED |
| `test_dispatcher::test_webhook_channel_sends` | PASSED |
| `test_dispatcher::test_test_alert_endpoint` | PASSED |
| `test_dispatcher::test_alert_history_logged` | PASSED |

**Alert Config (4 tests)**
| Test | Status |
|------|--------|
| `test_config::test_create_alert_config` | PASSED |
| `test_config::test_update_alert_config` | PASSED |
| `test_config::test_get_alert_config` | PASSED |
| `test_config::test_config_scoped_to_customer` | PASSED |

**No tests skipped.**

## 6. Definition of Done Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Alembic migration creates alert_configs, alert_history, examiner_reports tables | PASSED |
| 2 | Examiner agent generates structured findings from governance data | PASSED |
| 3 | Examiner agent falls back to static generation when no API key | PASSED |
| 4 | Report generated with all 11 sections | PASSED |
| 5 | Report downloads via GET /v1/reports/{id}/download | PASSED |
| 6 | Report list returns customer's reports | PASSED |
| 7 | Weekly digest generates examiner simulation for last 7 days | PASSED |
| 8 | Alert config CRUD endpoints work | PASSED |
| 9 | Alerts dispatched on policy block (email + webhook) | PASSED |
| 10 | Alerts NOT dispatched when trigger disabled | PASSED |
| 11 | Alert dispatch inline (doesn't break session state) | PASSED |
| 12 | Test alert endpoint works | PASSED |
| 13 | Alert history logged | PASSED |
| 14 | Dashboard has Reports page with generate + download + history | PASSED |
| 15 | Dashboard has Alerts page with config + test + history | PASSED |
| 16 | Chat endpoint triggers alerts on violations | PASSED |
| 17 | All new tests pass | PASSED (20/20) |
| 18 | All Phase 1-5 tests still pass (zero regressions) | PASSED (106/106) |
| 19 | `docs/phases/PHASE-6-COMPLETE.md` exists | PASSED (this file) |

## 7. What Was Deferred

| Item | Deferred To | Reason |
|------|-------------|--------|
| WeasyPrint PDF generation | Post-MVP | System dependency issues on Windows; HTML reports work for beta |
| Scheduled automatic weekly digest | Deployment phase | Manual trigger only; cron scheduling in production |
| Slack-specific integration | Post-MVP | Generic webhook covers Slack incoming webhooks |
| SMS alerts | Post-MVP | Enhancement |
| Alert throttling/rate limiting | Post-MVP | Future enhancement |
| Report template customization | Post-MVP | One standard template for MVP |
| Report scheduling (automatic) | Post-MVP | On-demand only for MVP |

## 8. How to Run

```bash
# Run all tests (126 tests)
py -m pytest tests/ -v

# Start backend
docker compose up -d
py -m alembic upgrade head
py scripts/seed_regulatory_mappings.py
py scripts/seed_templates.py
py -m uvicorn src.audithive.api.app:app --reload

# Start dashboard
cd dashboard && npm run dev

# Generate a governance report
curl -X POST http://localhost:8000/v1/reports/generate \
  -H "Authorization: Bearer ah-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"period_days": 30, "include_examiner_simulation": true}'

# Download the report
curl http://localhost:8000/v1/reports/{REPORT_ID}/download \
  -H "Authorization: Bearer ah-YOUR_KEY" > report.html

# Configure alerts
curl -X POST http://localhost:8000/v1/alerts/config \
  -H "Authorization: Bearer ah-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"on_block": true, "on_flag": false, "email_addresses": ["ops@company.com"], "webhook_urls": ["https://hooks.slack.com/services/xxx"]}'

# Send test alert
curl -X POST http://localhost:8000/v1/alerts/test \
  -H "Authorization: Bearer ah-YOUR_KEY"
```
