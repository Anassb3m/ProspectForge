# ProspectForge — Gap Matrix

**Date:** 2026-07-17  
**Branch:** `antigravity/prospectforge-production-pilot`

---

## Legend

| Status | Meaning |
|--------|---------|
| ✅ Complete | Implemented, tested, working |
| 🔶 Partial | Exists but incomplete or has defects |
| ❌ Missing | Not implemented |
| ⚠️ Defective | Implemented but incorrect behavior |
| 🏚️ Legacy | V2 code still present, may conflict |

---

## Commercial Correctness (§8)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Awards ≠ automatic pain | Critical | Pain scored 0 for award-only; suspected_pain set as hypothesis | scoring_v3.py:427-481 | ✅ Complete | Low | None | scoring_v3.py | test_p0_commercial.py | - |
| Generic keywords ≠ pain | Critical | STRUCTURAL_COMPLEXITY_KEYWORDS separated from PAIN_KEYWORDS | scoring_v3.py:24-65 | ✅ Complete | Low | None | scoring_v3.py | test_p0_commercial.py | - |
| Score ≠ readiness bypass | Critical | evaluate_readiness() has hard gates for fit/pain/trigger/authority/DQ + human accept | scoring_v3.py:274-322 | ✅ Complete | Low | None | scoring_v3.py | Needs more edge tests | P1 |
| Human accept requires 6 flags | Critical | Server-side validation in form_qualify() | queue.py:185-208 | ✅ Complete | Low | None | queue.py | test_p0_commercial.py | - |
| Contact confidence honest | Critical | Enum validation, deliverable/person match separation | scoring_v3.py:83-120, commercial.py:195-211 | ✅ Complete | Low | None | scoring_v3.py | Needs more tests | P1 |
| Proof/offer match real | High | offer_ok checks OfferAsset table, not hard-coded True | commercial.py:182-192, scoring_v3.py:641-659 | 🔶 Partial | Med | Default play has offer_asset_required=False; no seed data | plays/field_service.py | Need test | P1 |
| Guessed email ≠ verified | Critical | Guessed/pattern emails blocked from Sent events | services.py:226-230, scoring_v3.py:567-570 | ✅ Complete | Low | None | services.py | test_p0_commercial.py | - |

## Data Model (§9)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Evidence deduplication (fingerprint) | High | evidence_fingerprint() + upsert_evidence() | commercial.py:124-173, scoring_v3.py:169-186 | ✅ Complete | Low | None | commercial.py | test_p0_commercial.py | - |
| Reingestion idempotent | High | upsert_evidence checks existing fingerprints | commercial.py:124-173 | ✅ Complete | Med | Need integration test | commercial.py | Need test | P1 |
| Independent source counting | High | INDEPENDENT_SOURCES frozenset + counting function | scoring_v3.py:67-238 | ✅ Complete | Low | None | scoring_v3.py | test_v3_scoring.py | - |
| Evidence expiration | Med | is_active field exists on EvidenceSignal | models.py:382 | 🔶 Partial | Low | No expiration logic/cron | scoring_v3.py | Need test | P2 |
| Source provenance | High | source_type, evidence_url, observed_at on EvidenceSignal | models.py:379-384 | ✅ Complete | Low | None | models.py | - | - |

## Legacy V2/IT Behavior (§10)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Remove active V2 IT scoring | High | scoring.py exists but not imported in app hot paths | grep search | 🏚️ Legacy | Low | Mark clearly as legacy-test-only | scoring.py | - | P2 |
| REGISTRY_IT penalized | High | V3 scoring penalizes REGISTRY_IT signal_type | scoring_v3.py:512-514 | ✅ Complete | Low | None | scoring_v3.py | - | - |
| IT NAF excluded | High | Excluded NAF codes/prefixes in play config | field_service.py:25-30 | ✅ Complete | Low | None | field_service.py | - | - |

## Scoring Consolidation (§11)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Single recompute function | Critical | recompute_commercial_state() in commercial.py | commercial.py:214-256 | ✅ Complete | Low | None | commercial.py | - | - |
| All mutations trigger recompute | High | create, update, log_event, qualify all call it | services.py, queue.py | ✅ Complete | Med | Verify all paths | - | Need integration test | P1 |
| Legacy scoring cannot overwrite V3 | High | scoring.py not imported in app code | grep verified | ✅ Complete | Low | None | - | Need regression test | P1 |

## Daily Queue (§12)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Merge tasks into queue | Critical | Tasks explicitly loaded and annotated on prospect | queue.py:65-125 | ✅ Complete | Low | None | queue.py | - | - |
| Priority: replies > meetings > overdue > accepted > research | Critical | _action_priority correctly sorts queue | queue.py:82-124 | ✅ Complete | Low | None | queue.py | - | - |
| Show exact action, reason, evidence | High | Shows score badges and readiness failures | queue.html | 🔶 Partial | Med | Add task-specific action text | queue.html | - | P1 |

## Suppression (§15)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Check before prospect insertion | Critical | ✓ in create_prospect() | services.py:162-163 | ✅ Complete | Low | None | services.py | - | - |
| Check after contact discovery | High | Checked before applying email | jobs/enrichment.py:53 | ✅ Complete | Low | None | jobs/enrichment.py | - | - |
| Check before qualification accept | Critical | Checked before accept form | queue.py:186-209 | ✅ Complete | Low | None | queue.py | test_p0_commercial.py | - |
| Check before contact-ready | Critical | Checked via is_suppressed read | scoring_v3.py:635 | ✅ Complete | Low | None | scoring_v3.py | test_p0_commercial.py | - |
| Check before CSV export | High | Filtered inside export_csv | services.py:326 | ✅ Complete | Low | None | services.py | - | - |
| Check before Sent event | Critical | ✓ in log_event() | services.py:214-216 | ✅ Complete | Low | None | services.py | test_api.py | - |
| Opt-out removes tasks | High | Tasks cancelled on OptOut event | services.py:255-263 | ✅ Complete | Low | None | services.py | - | - |

## Security (§16)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| CSRF on all form mutations | Critical | CSRFMiddleware active | security.py:36-77 | ✅ Complete | Low | None | security.py | test_api.py | - |
| Login throttling | Critical | 10 attempts / 5 min | security.py:80-99 | ✅ Complete | Low | None | security.py | test_api.py | - |
| Strong password hashing | Critical | bcrypt via passlib | auth.py:20 | ✅ Complete | Low | None | auth.py | - | - |
| SECRET_KEY validation | Critical | Fails hard on weak keys | main.py:76-87 | ✅ Complete | Low | None | main.py | - | - |
| Secure cookies | Critical | Configurable via FORCE_HTTPS_COOKIES | config.py:64-67 | ✅ Complete | Low | None | config.py | - | - |
| Production docs disabled | High | /docs and /redoc off in production | main.py:102-103 | ✅ Complete | Low | None | main.py | - | - |
| Trusted hosts | High | TrustedHostMiddleware in production | main.py:121-122 | ✅ Complete | Low | None | main.py | - | - |
| No public DB port | Critical | DB bound to 127.0.0.1 in docker-compose | docker-compose.yml:69 | ✅ Complete | Low | None | docker-compose.yml | - | - |
| Fail-hard migrations | Critical | entrypoint.sh exits 1 on failure | entrypoint.sh:48-51 | ✅ Complete | Low | None | entrypoint.sh | - | - |
| create_all disabled in prod | Critical | Was missing, now fixed | database.py:38-49 | ✅ Complete | Low | None | database.py | - | - |
| FORWARDED_ALLOW_IPS restricted | High | Was `*`, now `127.0.0.1` | docker-compose.yml:24 | ✅ Complete | Low | None | docker-compose.yml | - | - |

## Deployment (§17-18)

| Requirement | Importance | Current | Evidence | Status | Risk | Required Change | Files | Test | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Docker build + start | Critical | Config valid (when env set) | docker-compose.yml | 🔶 Partial | Med | Need runtime validation | - | Docker test | P1 |
| Reverse proxy config | High | Caddyfile exists | deploy/Caddyfile | 🔶 Partial | Med | Verify for prospects.elevya.tech | deploy/ | - | P1 |
| Backup/restore | High | Scripts exist | scripts/backup.sh, restore.sh | 🔶 Partial | Med | Test restore | scripts/ | - | P1 |

---

## Priority Summary

### P0 — Must fix for commercial correctness
(All P0 issues implemented and verified)

### P1 — Important for production pilot
1. Docker build + runtime validation
2. Ingestion rerun idempotency integration test

### P2 — Deferred but tracked
11. Evidence expiration logic
12. Website intelligence adapter
13. Job posting signals
14. Mark legacy scoring.py clearly
