# ProspectForge — Project Understanding (Phase 0)

**Date:** 2026-07-17  
**Branch:** `antigravity/prospectforge-production-pilot`  
**Base commit:** `3fb12fb` (main)

---

## 1. What ProspectForge Does Commercially

ProspectForge is an **internal client-acquisition operating system** for Elevya. It automates the discovery, qualification, and tracking of prospective clients — specifically **French non-technical or lightly technical SMEs** that may buy custom operational software from Elevya.

The system is NOT a CRM replacement or a mass lead-generation tool. Its job is to produce a **small, defensible, meeting-ready work queue** — typically 5–15 carefully qualified prospects per week — that the operator then contacts manually (primarily via LinkedIn + email).

---

## 2. First Buyer Profile

**Target:** French SMEs in field-service / technical operations:
- HVAC and refrigeration companies
- Maintenance and technical-service firms
- Electrical installation companies
- Facilities operators
- Industrial maintenance businesses
- Companies with technicians, recurring interventions, quotes, reports, parts, dispatching

**NOT target:** ESNs, IT consultancies, cybersecurity vendors, cloud firms, software houses that could build similar software internally.

**Size sweet spot:** 11–50 or 51–200 employees.

---

## 3. Packaged Offer

> A focused operations-control system for quotes, interventions, technician planning, reports, parts, customer follow-up, and management visibility — configured around the company's real workflow.

This is NOT "Laravel development" or "digital transformation." It's a specific, bounded product for a specific workflow.

---

## 4. Data Sources That Exist Now

| Source | Implementation | Status |
|--------|---------------|--------|
| **DECP** (public procurement awards) | `app/discovery/decp.py` — Polars-based Parquet download + play-driven CPV/keyword filtering | **Complete**, working |
| **Annuaire Entreprises** (Recherche Entreprises) | `app/discovery/annuaire.py` — HTTP API for field-service query search | **Complete** |
| **Sirene** (INSEE API) | `app/discovery/sirene.py` — Company identity, NAF, size, diffusion gate | **Complete** |
| **Email permutator** | `app/discovery/emails.py` — French-pattern email candidate generation | **Complete** |
| **Reacher** (SMTP verification) | `app/discovery/reacher.py` — Self-hosted email deliverability check | **Complete**, disabled by default |
| **theHarvester** (OSINT) | `app/discovery/harvester.py` — Domain-based email/contact discovery | **Complete**, disabled by default |
| **Deep enrichment** | `app/discovery/enrich.py` — Combines Sirene + Annuaire + contacts waterfall | **Complete** |
| **Website intelligence** | Not implemented | **Missing** — highest-priority new source per spec |
| **Job postings** | Not implemented | **Missing** |
| **BOAMP / BODACC** | Not implemented | **Deferred** per spec |

---

## 5. Candidate Journey: Discovery → Contact-Ready

```
1. Discovery (DECP awards / Registry search / Manual import)
   → Companies with SIREN/SIRET identified
   
2. Sirene Enrichment  
   → NAF code, company size, diffusion gate, legal representative
   → Partial-diffusion companies rejected
   
3. V3 Scoring (app/scoring_v3.py)
   → Fit, Pain, Trigger, Authority, Value, Data Quality dimensions
   → Opportunity score computed with weighted formula
   → Readiness state evaluated via hard gates
   
4. Evidence Accumulation
   → Trigger evidence from awards (NOT pain)
   → Structural fit from NAF/size
   → Pain requires explicit workflow evidence or human confirmation
   
5. Human Qualification (app/routers/queue.py)
   → Operator reviews prospect in /queue/{id}/qualify
   → Must confirm all 6 gates for "accept": fit, pain, trigger, buyer, contact, offer match
   
6. Contact Discovery
   → Email permutation + Reacher verification
   → Or operator manually confirms contact
   
7. Contact-Ready
   → All readiness gates satisfied → appears in daily queue as actionable
```

---

## 6. How Evidence Is Stored and Scored

### Storage
- **`EvidenceSignal` table** (`evidence_signals`): Normalized, per-prospect, with category, signal_type, source_type, confidence, strength, is_active, manually_confirmed
- **`Prospect.evidence_json`** (JSON column): Cache of evidence signals, synced from normalized rows by `recompute_commercial_state()`
- **`Prospect.award_history`** (JSON column): List of DECP award dicts

### Scoring
- `scoring_v3.py` reads evidence signals via `_signal_dicts()` → normalizes → deduplicates via fingerprint
- Pain: ONLY from explicit workflow keywords or pain-category signals (NOT from awards)
- Trigger: Awards contribute here (recent + multi-award bonus)
- Fit: NAF code matching against play config
- Authority: Decision-maker title matching against buyer roles
- Value: Award amounts + company size
- Data Quality: Independent source count + metadata completeness

### Deduplication
- `evidence_fingerprint()` creates SHA-256 hash from source_type + signal_type + URL + text + date
- `normalize_signals()` deduplicates in-memory
- `upsert_evidence()` in commercial.py checks existing fingerprints before inserting

---

## 7. How Contacts and People Are Represented

Contacts are stored **directly on the `Prospect` row** (not a separate contacts table):
- `email`, `phone`, `linkedin_url`
- `decision_maker_name`, `decision_maker_title`
- `contact_source`: reacher / theharvester / manual / sirene / none
- `contact_confidence`: Server-validated enum (deliverable, catch_all, published_personal, guessed, etc.)
- `contact_discovery_state`: published / inferred / guessed / user_supplied / none
- `contact_candidates`: JSON list of email candidates from permutator

**Defect:** No separate `Person` / `Contact` table — a single prospect can only have one primary contact.

---

## 8. How Human Qualification Works

### Flow
1. Operator opens `/queue/{id}/qualify` — sees prospect details, evidence, score breakdown
2. Selects decision: `accept` / `reject` / `research_more` / `park`
3. For `accept`: **must check all 6 confirmation boxes** (server-validated)
4. A `QualificationReview` record is created
5. Prospect's `manual_review_state` updated accordingly
6. `recompute_commercial_state()` runs — latest review is source of truth
7. Tasks created: `first_outreach` for accept, `research` for research_more

### Server Enforcement
- `form_qualify()` in queue.py validates all 6 flags for accept — returns 400 with error listing missing flags
- `_is_full_human_accept()` in scoring_v3.py verifies latest review has accept + all 6 flags
- Readiness evaluation requires `human_accepted=True` as a gate

---

## 9. Outreach History, Tasks, Follow-ups, Pipeline

### Outreach Events
- `OutreachEvent` table: prospect_id, channel, event_type, event_date, notes, next_action, next_action_date
- Append-only history — `prospect.current_status` is derived from latest event
- Event types: New, Sent, Replied, Refused, MeetingBooked, PositiveConversation, ProposalSent, ClosedWon, ClosedLost, OptOut

### Tasks
- `Task` table: prospect_id, task_type, title, due_date, priority, status, origin, notes
- Created by qualification (first_outreach, research) or manually
- **Defect:** Tasks not yet surfaced in the daily queue (`/queue` doesn't merge tasks)

### Follow-ups
- `/follow-ups` page shows prospects where `next_action_date <= today`
- Sorted by days overdue + urgency score

### Pipeline / Kanban
- `/kanban` maps event types to columns (New → Sent → Replied → Meeting → Closed)

---

## 10. Suppression and Opt-Out

### Implementation
- `SuppressionEntry` table: kind (email/domain/siren/person), value_normalized, reason, source
- `is_suppressed()` checks email, domain (from email), and siren
- Checked at: prospect creation, event logging, Sent event compliance
- `OptOut` event triggers suppression entry creation for email + siren

### Gaps
- **Not checked:** before qualification acceptance, before contact-ready status, before CSV export
- **Missing:** phone suppression, person suppression
- **No audit trail** for suppression state changes beyond initial creation

---

## 11. Local and Production Deployment

### Local
- SQLite via aiosqlite — `database_url = sqlite+aiosqlite:///./prospectforge.db`
- `uvicorn app.main:app --reload --port 8000`
- `create_all()` in `init_db()` creates tables directly
- Admin bootstrapped from env vars when users table is empty

### Production (Docker)
- PostgreSQL 16 + FastAPI app + Caddy reverse proxy
- `scripts/entrypoint.sh`: wait for DB → Alembic migrate → fail hard if migration fails → uvicorn
- App bound to 127.0.0.1:APP_PORT (loopback only)
- DB bound to 127.0.0.1:POSTGRES_PORT (loopback only)
- Caddy on custom high ports (18080/18443) — self-signed by default
- Target architecture: existing VPS reverse proxy → 127.0.0.1:18081 → app container

### **Critical Defect**: `init_db()` calls `create_all()` as fallback even in production. This bypasses Alembic and may create tables without proper migration tracking.

---

## 12. Feature Status Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| DECP discovery | **Complete** | Play-driven CPV/keyword filters working |
| Registry/Annuaire discovery | **Complete** | Field-service search queries |
| Sirene enrichment | **Complete** | NAF, size, diffusion gate |
| V3 scoring engine | **Complete** | 6 dimensions + hard readiness gates |
| Pain/trigger separation | **Complete** | Awards → trigger only, pain needs evidence |
| Human qualification with 6 gates | **Complete** | Server-enforced, all flags required for accept |
| Contact confidence separation | **Complete** | Deliverability + person matching enums |
| Suppression table | **Complete** | Email, domain, siren kinds |
| Evidence deduplication | **Complete** | Fingerprint-based |
| Market play configuration | **Complete** | FIELD_SERVICE_OPERATIONS_FR active |
| Daily queue `/queue` | **Partial** | Sorts by readiness + score but doesn't merge tasks/follow-ups/replies |
| Task creation from qualification | **Complete** | first_outreach and research tasks created |
| Task visibility in queue | **Missing** | Tasks created but not surfaced in daily queue |
| CSRF protection | **Complete** | Double-submit cookie middleware |
| Login throttling | **Complete** | 10 attempts / 5 min window |
| Production docs disabled | **Complete** | /docs and /redoc off in production |
| Secure cookies | **Complete** | FORCE_HTTPS_COOKIES configurable |
| Trusted hosts | **Complete** | TrustedHostMiddleware in production |
| Weak SECRET_KEY rejection | **Complete** | Fails hard at startup |
| Ingestion run tracking | **Partial** | IngestionRun model exists, but not fully wired |
| Offer/proof asset model | **Partial** | OfferAsset model exists, offer_ok defaulted to model check |
| Website intelligence | **Missing** | Highest-priority new source |
| Job posting signals | **Missing** | |
| Today queue with merged actions | **Missing** | Spec requires replies > meetings > overdue > accepted > research |
| Outreach brief generation | **Missing** | personalization_brief exists but no template/UI |
| Message drafts | **Missing** | |

---

## Source-of-Truth Map

| Concept | Source of Truth | Location |
|---------|----------------|----------|
| Company/prospect identity | `Prospect` row (siren, siret, company_name) | `app/models.py:140` |
| Evidence | `EvidenceSignal` table (normalized) | `app/models.py:366` |
| Score dimensions | Computed by `score_prospect_v3()` → stored on Prospect | `app/scoring_v3.py:369` |
| Readiness | Computed by `evaluate_readiness()` → stored as `readiness_state` | `app/scoring_v3.py:274` |
| Human qualification | Latest `QualificationReview` (by created_at desc) | `app/models.py:388` |
| Contact confidence | `Prospect.contact_confidence` (server-validated enum) | `app/models.py:164` |
| Current outreach status | Derived from latest `OutreachEvent.event_type` | `app/models.py:237` |
| Next action | From latest `OutreachEvent.next_action` + `next_action_date` | `app/models.py:250` |
| Suppression | `SuppressionEntry` table | `app/models.py:422` |
| Market play | `MarketPlay` table + `app/plays/field_service.py` config dict | `app/plays/` |
| Ingestion run | `IngestionRun` table | `app/models.py:433` |

### Duplicate Source-of-Truth Issues
1. **Evidence:** Both `EvidenceSignal` table AND `Prospect.evidence_json` JSON field — `recompute_commercial_state()` syncs them but divergence possible
2. **Score:** `opportunity_score`, `acquisition_score`, `urgency_score` all stored — V3 sets all three to same value in `apply_v3_score()` but legacy scoring.py also exists and could overwrite
3. **Review state:** Both `QualificationReview` table AND `Prospect.manual_review_state` cached field — `recompute_commercial_state()` loads latest review, but cached state could drift

---

## Route Map

| Route | Method | Handler | Purpose |
|-------|--------|---------|---------|
| `/` | GET | `dashboard.page_dashboard` | Dashboard metrics |
| `/login` | GET | `main.login_page` | Login form |
| `/auth/login` | POST | `auth.router` | Login action |
| `/auth/logout` | POST | `auth.router` | Logout |
| `/queue` | GET | `queue.page_daily_queue` | Daily action queue |
| `/queue/{id}/qualify` | GET/POST | `queue.page_qualify/form_qualify` | Human qualification |
| `/sourcing` | GET | `sourcing.page_sourcing` | Sourcing cockpit |
| `/prospects` | GET | `prospects.page_prospects` | Full prospect list |
| `/prospects/new` | GET/POST | `prospects.page_new_prospect/form_create_prospect` | Create prospect |
| `/prospects/{id}` | GET | `prospects.page_prospect_detail` | Prospect detail |
| `/prospects/{id}/edit` | GET/POST | `prospects.page_edit_prospect/form_edit_prospect` | Edit prospect |
| `/follow-ups` | GET | `dashboard.page_follow_ups` | Due follow-ups |
| `/kanban` | GET | `dashboard.page_kanban` | Pipeline kanban |
| `/import` | GET/POST | `prospects.page_import/form_import` | CSV import |
| `/health` | GET | `main.health` | Health check |
| `/ready` | GET | `main.ready` | Readiness check |
| `/api/...` | Various | Multiple routers | JSON API endpoints |

---

## Code Map

```
app/
├── main.py              # FastAPI app, lifespan, middleware, admin bootstrap
├── config.py            # Pydantic settings from env
├── database.py          # SQLAlchemy engine, session, init_db (create_all)
├── models.py            # All ORM models + constant tuples
├── schemas.py           # Pydantic request/response schemas
├── auth.py              # JWT + bcrypt + cookie auth
├── security.py          # CSRF middleware + login rate limiting
├── scoring.py           # LEGACY V2 urgency scoring (still importable)
├── scoring_v3.py        # V3 opportunity scoring + readiness gates
├── commercial.py        # recompute_commercial_state + suppression + evidence upsert
├── services.py          # Domain services: queries, metrics, CSV, follow-ups
├── plays/
│   ├── __init__.py      # Play registry
│   └── field_service.py # FIELD_SERVICE_OPERATIONS_FR config
├── discovery/
│   ├── decp.py          # DECP parquet download + filter
│   ├── annuaire.py      # Recherche Entreprises API
│   ├── sirene.py        # INSEE Sirene enrichment
│   ├── emails.py        # Email permutator
│   ├── reacher.py       # SMTP verification via Reacher
│   ├── harvester.py     # theHarvester OSINT
│   ├── enrich.py        # Deep enrichment orchestrator
│   ├── contacts.py      # Contact candidate management
│   ├── icp.py           # ICP scoring helper
│   └── naf.py           # NAF code mapping
├── routers/
│   ├── auth.py          # Login/logout routes
│   ├── dashboard.py     # Dashboard + follow-ups + kanban
│   ├── events.py        # Outreach event logging
│   ├── prospects.py     # CRUD + CSV + HTML pages
│   ├── queue.py         # Daily queue + qualification
│   └── sourcing.py      # Sourcing cockpit + ingestion + enrichment
├── jobs/
│   ├── ingestion.py     # Batch ingestion job
│   ├── enrichment.py    # Contact enrichment job
│   └── scheduler.py     # APScheduler setup
├── templates/           # Jinja2 HTML templates
└── static/              # CSS + JS assets
```
