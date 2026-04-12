# PHASE-3-COMPLETE.md — Policy Templates

## 1. Phase Goal

Build the policy template system: pre-built governance templates loaded from JSON files, browsable via API, applied to customer accounts with optional deep-merge customizations, and enforced through the existing policy engine. Customers pick a template and have governance active immediately.

## 2. What Was Built

### Core Utilities (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/core/utils.py` | `deep_merge()` — recursive dict merge for template customizations |

### Template Loader (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/policy/templates/loader.py` | Reads JSON definitions, seeds/updates `policy_templates` table (idempotent, version-aware) |

### Schemas (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/schemas/template.py` | `TemplateListItem`, `TemplateDetailResponse`, `TemplateApplyRequest/Response` |

### API Routes (1 new file)
| File | Purpose |
|------|---------|
| `src/audithive/api/routes/templates.py` | GET list, GET detail, POST apply (with deep-merge customizations) |

### Scripts (1 new file)
| File | Purpose |
|------|---------|
| `scripts/seed_templates.py` | Standalone script to load templates into database |

### Modified Files
| File | Change |
|------|--------|
| `src/audithive/policy/engine.py` | Added `_is_template_format()`, `_normalize_pii_config()`, `_normalize_template_config()` for backward-compatible template format support |
| `src/audithive/api/app.py` | Registered templates router |

### Template Definition Files (pre-existing, read-only)
| File | Template |
|------|----------|
| `src/audithive/policy/templates/definitions/chatbot.json` | Customer-facing chatbot (high risk) |
| `src/audithive/policy/templates/definitions/document_generation.json` | Internal document generation (medium risk) |
| `src/audithive/policy/templates/definitions/email_automation.json` | Email automation (medium risk) |

### Tests (2 new files)
| File | Purpose |
|------|---------|
| `tests/test_core/test_utils.py` | 10 tests for deep_merge |
| `tests/test_policy/test_templates.py` | 12 tests (4 loader + 7 API + 1 integration) |

**Total new files: 7. Total modified files: 2.**

## 3. Endpoints Added

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/v1/templates` | API key | List all templates (metadata only, no full config) |
| GET | `/v1/templates/{template_id}` | API key | Get full template detail with config |
| POST | `/v1/templates/{template_id}/apply` | API key | Create customer policy from template with optional customizations |

## 4. Design Decisions

1. **`risk_level` and `regulatory_grounding` stored inside the `config` JSON column** — The `PolicyTemplate` model already has a `config` column. Rather than adding new columns (which would require a migration), these metadata fields are stored alongside `pre_call`/`post_call` in the config blob. The API layer extracts them for response schemas and strips them from the policy config when applying templates.

2. **Template list endpoint excludes full config** — `GET /v1/templates` returns only metadata (id, name, description, risk_level, regulatory_grounding). The full config is only returned on `GET /v1/templates/{id}`. This keeps the list response lightweight.

3. **Deep merge: lists replace, dicts recurse** — Per spec, lists from overrides replace base lists entirely (not appended). This is correct for fields like `prohibited_topics` where the customer wants to specify their own list, not add to the template's empty default.

4. **Template-format PII config normalized to flat format** — Template JSON uses per-type action objects (`types: {ssn: {action: "block"}, email: {action: "flag"}}`). The PII check function expects flat format (`types: ["ssn", ...], action: "block"`). The engine normalizes at runtime using the most restrictive action among enabled types. This avoids changing the check functions.

5. **Backward compatibility via format detection** — `_is_template_format(config)` checks for the `pre_call` key. If present, the engine normalizes to flat format before passing to check functions. Phase 2 flat-format policies continue to work unchanged. All 55 existing tests still pass.

6. **Template loading is idempotent** — `load_templates_from_definitions()` skips existing templates (by ID) and only updates if the JSON version is higher. Safe to call on every startup or run repeatedly.

7. **`POST /v1/templates/{id}/apply` creates a `PolicyConfig` row** — The applied policy is a regular `PolicyConfig` with `template_id` set for tracking lineage. It goes through the same enforcement path as manually-created policies.

8. **No startup auto-loading in tests** — Templates are seeded explicitly via a `_seed_templates()` helper in tests. The app startup event is not relied on because the test database is separate.

## 5. Tests

**Total: 77 tests (11 Phase 1 + 44 Phase 2 + 22 Phase 3). All passing.**

### Phase 1 tests (11) — no regressions
All 11 tests PASSED (test_health x4, test_auth x7).

### Phase 2 tests (44) — no regressions
All 44 tests PASSED (test_chat x6, test_logger x6, test_pii x9, test_injection x10, test_content x6, test_engine x7).

### Phase 3 tests (22)

**Deep Merge (10 tests)**
| Test | Status |
|------|--------|
| `test_utils::test_empty_overrides_returns_base` | PASSED |
| `test_utils::test_top_level_override` | PASSED |
| `test_utils::test_nested_dict_merge` | PASSED |
| `test_utils::test_three_levels_deep` | PASSED |
| `test_utils::test_list_replacement` | PASSED |
| `test_utils::test_new_key_added` | PASSED |
| `test_utils::test_none_replaces_value` | PASSED |
| `test_utils::test_base_keys_preserved` | PASSED |
| `test_utils::test_inputs_not_mutated` | PASSED |
| `test_utils::test_empty_base` | PASSED |

**Template Loader (4 tests)**
| Test | Status |
|------|--------|
| `test_templates::test_templates_loaded_from_json` | PASSED |
| `test_templates::test_loader_is_idempotent` | PASSED |
| `test_templates::test_higher_version_updates` | PASSED |
| `test_templates::test_template_config_matches_json` | PASSED |

**Template API (7 tests)**
| Test | Status |
|------|--------|
| `test_templates::test_list_templates` | PASSED |
| `test_templates::test_list_templates_no_full_config` | PASSED |
| `test_templates::test_get_template_detail` | PASSED |
| `test_templates::test_get_nonexistent_template` | PASSED |
| `test_templates::test_apply_template_defaults` | PASSED |
| `test_templates::test_apply_template_with_customizations` | PASSED |
| `test_templates::test_nested_customization_preserves_defaults` | PASSED |

**Integration (1 test)**
| Test | Status |
|------|--------|
| `test_templates::test_template_policy_enforcement` | PASSED |

**No tests skipped.**

## 6. Definition of Done Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | `scripts/seed_templates.py` loads all 3 templates into the database | PASSED |
| 2 | `GET /v1/templates` returns all 3 templates with metadata (no full config) | PASSED |
| 3 | `GET /v1/templates/{id}` returns full template detail with config | PASSED |
| 4 | `POST /v1/templates/{id}/apply` creates a policy from template defaults | PASSED |
| 5 | `POST /v1/templates/{id}/apply` with customizations merges correctly | PASSED |
| 6 | Deep merge handles nested dicts, list replacement, and missing keys correctly | PASSED |
| 7 | Policy created from template works with the chat completions endpoint | PASSED |
| 8 | Template loading is idempotent (re-running seed script doesn't create duplicates) | PASSED |
| 9 | Template version update works (higher version replaces existing) | PASSED |
| 10 | Backward compatibility: Phase 2 flat-format policies still work | PASSED |
| 11 | All new tests pass | PASSED (22/22) |
| 12 | All Phase 1 + Phase 2 tests still pass (zero regressions) | PASSED (55/55) |
| 13 | `docs/phases/PHASE-3-COMPLETE.md` exists with full summary | PASSED (this file) |

## 7. What Was Deferred

| Item | Deferred To | Reason |
|------|-------------|--------|
| Post-call evaluation (hallucination, harmful content, brand tone) | Phase 4+ | Template configs include these sections but the engine doesn't execute them yet |
| Approved answers enforcement | Phase 4+ | Template has the field but not wired |
| Alerting (email/Slack/webhook) | Phase 6 | Template has alerting config but no notification channels exist |
| AI disclosure injection into system prompt | Phase 4+ | Template config present but not implemented |
| Confidential data detection (document_generation template) | Phase 4+ | Template-specific check not yet built |
| Prohibited claims check (email_automation template) | Phase 4+ | Template-specific check not yet built |
| Startup auto-loading of templates | Production | Works but skipped in test mode; deferred to production wiring |
| Additional templates beyond the 3 MVP templates | Post-launch | Three templates sufficient for beta |

## 8. How to Run

```bash
# Run all tests (77 tests, no Docker required)
py -m pytest tests/ -v

# Seed templates into PostgreSQL (requires running database)
docker compose up -d
py -m alembic upgrade head
py scripts/seed_templates.py

# Start the server
py -m uvicorn src.audithive.api.app:app --reload

# Browse templates
curl -H "Authorization: Bearer ah-YOUR_KEY" http://localhost:8000/v1/templates

# Get template detail
curl -H "Authorization: Bearer ah-YOUR_KEY" http://localhost:8000/v1/templates/customer_chatbot

# Apply a template with customizations
curl -X POST http://localhost:8000/v1/templates/customer_chatbot/apply \
  -H "Authorization: Bearer ah-YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Chatbot Policy",
    "customizations": {
      "pre_call": {
        "content_filter": {
          "prohibited_topics": ["competitor pricing", "internal salary"]
        }
      }
    }
  }'
```
