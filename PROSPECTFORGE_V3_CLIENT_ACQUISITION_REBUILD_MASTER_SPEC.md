# ProspectForge V3 — Client Acquisition Rebuild Master Specification

**Document type:** implementation-grade product, engineering, data, compliance, deployment, and commercial operating specification  
**Target repository:** `ProspectForge-main` version 2.2.0  
**Prepared:** 2026-07-16  
**Primary objective:** transform the existing application from an IT/cyber-oriented prospect database into a reliable internal system that finds, qualifies, prioritizes, and helps convert non-technical SMEs that are plausible buyers of custom operational software.

---

## 0. How to use this document

This is not a replacement concept for the existing application. It is a **controlled rebuild and refinement plan for the code that already exists**.

Use it as:

1. the product specification for ProspectForge V3;
2. the implementation backlog;
3. the acceptance-gate checklist for each change;
4. the VPS deployment specification;
5. the operating manual for the first real acquisition pilot;
6. the decision record preventing the system from drifting back toward an attractive but commercially weak target market.

The order matters. Do not begin by adding more data sources, AI, automatic messaging, or volume. Correct the commercial model, evidence model, scoring, human qualification gate, and deployment first.

---

# 1. Executive decision

## 1.1 Keep the existing system

The existing build is not disposable. It already contains a useful foundation:

- FastAPI application and API layer;
- SQLAlchemy models and Alembic migrations;
- PostgreSQL production configuration;
- HTMX/Jinja operator interface;
- append-only outreach-event history;
- prospect list, detail page, Kanban board, and follow-up queue;
- CSV import/export;
- public-procurement ingestion;
- French registry enrichment;
- email-candidate generation;
- optional SMTP verification;
- dashboard metrics;
- authentication;
- Docker Compose, Caddy, backup scripts, and health checks;
- automated test suite.

The current repository was locally validated with:

- **53 passing tests**;
- **11 Ruff findings**, mainly unused imports and ambiguous variable names.

This proves that the repository is a functioning application. It does **not** prove live-source reliability, target quality, contact accuracy, commercial relevance, legal correctness, deliverability, or client conversion.

## 1.2 Do not deploy it unchanged as the main acquisition engine

The present system is explicitly optimized for French IT, cyber, software, cloud, and digital-service companies. This contradicts the intended strategy of selling operational systems to non-technical or lightly technical SMEs that are less able or willing to build internally.

The mismatch exists across the whole application:

- `README.md` and `GUIDE.md` define an IT/digital ICP;
- `app/discovery/naf.py` classifies and rewards IT/cyber NAF codes;
- `app/discovery/icp.py` gives high scores to IT NAFs, DSI/CTO roles, cyber/cloud language, and digital public buyers;
- `app/discovery/decp.py` filters public awards using IT CPV prefixes and IT/cyber keywords;
- `app/discovery/annuaire.py` searches Section J and calls `discover_it_smes()`;
- `app/jobs/ingestion.py` creates `REGISTRY_IT` prospects;
- `app/scoring.py` adds urgency for IT/cyber NAF codes;
- source labels, badges, templates, and operator instructions reinforce the same targeting.

Changing a few score weights is insufficient. ProspectForge needs a **market-play architecture** in which targeting, signals, pain hypotheses, buyers, offers, exclusions, scoring, and message assets are configurable and linked.

## 1.3 V3 mission

ProspectForge V3 must answer one operational question every morning:

> Which five to ten companies should I contact today, who should I contact, why might they care now, what evidence supports that judgment, which offer fits them, and what should I do next?

A record is not useful merely because it has a company name, a public award, a guessed email, and a score. A useful record must include:

- a clear market play;
- verified company identity;
- acceptable company size and operating model;
- at least one structural-fit signal;
- at least one credible pain or complexity signal;
- a current buying trigger or timing reason;
- an appropriate decision-maker role;
- a contact method with explicit confidence;
- source provenance and evidence;
- a matching service offer and proof asset;
- a human qualification decision;
- a recommended next action.

---

# 2. North-star outcome and operating constraints

## 2.1 North-star outcome

The system succeeds when it consistently produces a small, high-confidence queue of **meeting-ready prospects**, not when it accumulates thousands of records.

A meeting-ready prospect is a company for which the operator can state, in one concise paragraph:

1. what the company does;
2. why it fits the active market play;
3. what operational problem it probably has;
4. what changed recently or why timing may be favorable;
5. who likely owns the problem;
6. what evidence supports the hypothesis;
7. what specific offer and proof should be presented;
8. how the person can be contacted safely.

## 2.2 Required operator output

Each item in the daily queue must display:

- **Company:** legal name, trading name, SIREN/SIRET, website, location, size;
- **Market play:** the active ICP/offer configuration;
- **Why this company:** three to five evidence-backed reasons;
- **Likely pain:** concise operational hypothesis, not a generic claim;
- **Why now:** recent trigger with source and date;
- **Buyer role:** recommended primary and fallback roles;
- **Person:** name, title, source, role confidence;
- **Contact:** channel, address/URL, verification state, risk state;
- **Offer:** the specific packaged service matching the pain;
- **Proof:** case study, screenshots, demo, or relevant portfolio asset;
- **Priority:** opportunity score, readiness state, and penalties;
- **Next action:** research, verify, send, follow up, call, park, or suppress.

## 2.3 Non-goals for the first production version

Do not build these before the manual commercial loop works:

- autonomous LinkedIn scraping;
- automated LinkedIn connection or message sending;
- high-volume cold-email sequencers;
- generic AI lead scoring;
- a full CRM replacement;
- multi-tenant SaaS billing;
- hundreds of integrations;
- complex ML before sufficient outcome data;
- automatic proposal generation without human review;
- scraping sources whose terms prohibit it;
- a “one score explains everything” model.

---

# 3. Current-state audit

## 3.1 Components to retain

| Existing component | Decision | Required treatment |
|---|---|---|
| FastAPI application | Keep | Add stronger service boundaries, CSRF, rate limiting, and production configuration |
| PostgreSQL | Keep | Normalize evidence, contacts, plays, campaigns, job runs, and suppression records |
| SQLAlchemy/Alembic | Keep | Add explicit V3 migrations; remove production `create_all` fallback |
| HTMX/Jinja | Keep | Redesign around a daily action queue and evidence review |
| Outreach event log | Keep and refine | Separate interaction events, pipeline stage, result, objections, and tasks |
| CSV import/export | Keep | Add source/evidence mapping, duplicate resolution, and dry-run validation |
| DECP ingestion | Keep and generalize | Move CPV/keyword logic into market-play configuration |
| Recherche Entreprises | Keep and generalize | Search per play, not Section J only |
| SIRENE enrichment | Keep | Treat it as canonical identity/compliance data, not pain evidence |
| Email permutations | Keep as candidates | Never present guessed patterns as verified contacts |
| Reacher integration | Keep optional | Add catch-all/risky/indeterminate states and licensing/operational controls |
| Dashboard | Keep and replace metrics | Focus on qualified yield and funnel conversion, not database volume |
| Scheduler | Move out of web process | Dedicated worker with persisted run records and locking |
| Docker/Caddy | Keep and harden | Real domain TLS, no public high-port self-signed default, exact trusted hosts |
| Tests | Keep and expand | Add source-contract, migration, security, scoring-calibration, and live smoke tests |

## 3.2 Components to remove or retire

The following should be removed from the active production path:

1. `REGISTRY_IT` as a core signal type.
2. Hard-coded Section J registry hunting.
3. IT/cyber NAF bonuses in the general score.
4. CTO/DSI priority in every market.
5. CPV defaults `72`, `48`, and `62` as universal discovery filters.
6. Cyber/cloud/digital keywords as universal timing signals.
7. A public award automatically implying operational pain.
8. A named legal representative automatically implying buyer relevance.
9. A guessed email automatically making a record contact-ready.
10. A “verified” label that ignores catch-all or ambiguous SMTP responses.
11. Automatic nightly full ingestion enabled by default before live-source validation.
12. Application startup continuing after failed Alembic migration.
13. `Base.metadata.create_all()` as a production safety net.
14. Wildcard trusted hosts in production.
15. Wildcard forwarded-proxy trust when it is avoidable.
16. Plain HTTP as a public operating path.
17. Self-signed public TLS as the recommended final deployment.
18. Resetting or extending prospect retention based only on outgoing messages.
19. The current assumption that a single mutable prospect row can hold all signals and contacts cleanly.
20. Documentation that claims the machine finds and converts prospects without qualification evidence.

## 3.3 Critical current risks

| Risk | Severity | Why it matters |
|---|---:|---|
| Wrong ICP encoded throughout the system | Critical | Efficiently produces the wrong list |
| Award equals need assumption | Critical | Creates false urgency and generic outreach |
| Contact confidence overstated | High | Causes bounces, poor reputation, and wasted messages |
| One contact per company | High | Often selects the legal president rather than the problem owner |
| One signal field per prospect | High | Loses chronology, provenance, and independent evidence count |
| In-process scheduler | High | Jobs can duplicate, disappear, or block web reliability |
| No persistent ingestion-run model | High | Failures and partial imports are difficult to audit or resume |
| No human qualification gate | High | Low-quality records enter outreach immediately |
| Weak production defaults | High | Cookie, host, TLS, migration, and CSRF risks |
| Vanity dashboard metrics | Medium | Encourages volume rather than conversion learning |
| No offer/proof matching | High | System finds companies but does not help make a credible approach |
| No score calibration loop | High | Score can remain persuasive but commercially wrong indefinitely |

---

# 4. Commercial redesign: market plays, not one universal ICP

## 4.1 Market-play concept

A **market play** is a complete acquisition hypothesis. It combines:

- target sectors and NAF ranges;
- target company size;
- target operating characteristics;
- excluded company types;
- pain hypotheses;
- strong and weak signals;
- buying triggers;
- decision-maker roles;
- packaged offer;
- proof assets;
- score weights and gates;
- outreach angle;
- success and kill criteria.

Only one primary market play should be active during an initial outreach sprint. This prevents mixed messages and makes the results interpretable.

## 4.2 Recommended first market play

### `FIELD_SERVICE_OPERATIONS_FR`

This should be the first active play because it is closest to the existing refrigeration/service-system proof.

**Target company types**

- refrigeration and cold-chain installers/maintainers;
- HVAC, heating, ventilation, and air-conditioning contractors;
- electrical and technical installation firms;
- fire-safety and security-system installers;
- industrial maintenance companies;
- facilities and multi-site technical service companies;
- technical equipment service firms with field technicians;
- specialist BTP subcontractors with recurring interventions.

**Illustrative NAF families to validate and configure**

- 43.21 — electrical installation;
- 43.22 — plumbing, heating, thermal and climate equipment installation;
- 43.29 — other construction installation;
- 33.12 — machinery repair;
- 33.20 — installation of industrial machinery and equipment;
- 81.10 — combined facilities support;
- selected 71.12 engineering activities where there is field delivery;
- selected 43.xx specialist works.

Do not treat the above as a permanent universal list. Store them in the market-play configuration and review actual lead quality.

**Structural-fit indicators**

- 10–150 employees, with emphasis on 11–50 and 51–200 bands;
- multiple technicians, sites, agencies, or service areas;
- recurring maintenance contracts;
- quote and intervention workflows;
- equipment, spare parts, vehicles, or stock;
- PDFs, intervention reports, work orders, certificates, or compliance documents;
- a customer-service or planning function;
- public or large-business clients.

**Pain hypotheses**

- quotes and customer follow-up spread across spreadsheets and email;
- intervention scheduling managed manually;
- technicians submit reports using paper, WhatsApp, PDF, or disconnected forms;
- stock and parts visibility is weak;
- commercial, technical, and administrative teams re-enter the same data;
- recurring-contract reporting takes too long;
- customer documents and proof of intervention are difficult to retrieve;
- management lacks a real-time operational view.

**Strong triggers**

- recent public-contract award involving maintenance or technical services;
- several awards or new service contracts in a short period;
- new agency or establishment;
- hiring a planner, service coordinator, ADV, operations manager, stock manager, or administrative assistant;
- explicit multi-site expansion;
- a new major customer or framework contract;
- website language indicating growing field capacity;
- replacement of a legacy tool or job advertisement mentioning ERP/Excel/reporting problems.

**Primary buyer roles**

1. owner, founder, gérant, or president for smaller firms;
2. operations director or exploitation director;
3. service or maintenance director;
4. technical director;
5. administrative/financial director when the pain is reporting or invoicing handoff;
6. commercial director when quote follow-up is the main problem.

**Packaged offer**

> A focused operations-control system for quotes, interventions, technicians, reports, parts, customer history, and management visibility—configured around the company’s existing workflow rather than sold as generic software development.

**Proof to match**

- refrigeration-system case study;
- screenshots showing quotes, roles, dashboard, PDF generation, and daily use;
- two-minute walkthrough;
- diagram of current manual flow versus target flow;
- fixed discovery and delivery process;
- clear first engagement scope.

## 4.3 Second market play

### `PUBLIC_TENDER_OPERATIONS_FR`

Use after the first play has been tested.

**Targets**

- specialist BTP firms;
- engineering and technical consultancies;
- environmental and inspection services;
- equipment suppliers;
- maintenance and professional-service SMEs with repeated public awards.

**Problem focus**

- bid/no-bid decisions;
- document library;
- deadlines and responsibilities;
- recurring administrative evidence;
- tender history;
- post-award delivery reporting;
- cross-team coordination.

**Important rule**

A public award is a timing or budget signal. It is not pain evidence by itself. This play requires an additional operational-complexity or pain signal before a prospect becomes ready.

## 4.4 Third market play

### `FRANCE_MOROCCO_LOGISTICS_OPS`

Use only when proof and a tailored offer exist.

**Targets**

- freight forwarders;
- transport operators;
- import/export coordinators;
- customs and logistics service firms;
- distributors with regular France–Morocco flows.

**Problem focus**

- shipment milestones;
- document collection;
- customer status communication;
- proof of delivery;
- scheduling and exception handling;
- cross-border coordination;
- manual reporting.

**Required extra proof**

A logistics-specific prototype, process map, or diagnostic asset is needed. The existing refrigeration proof is less direct for this play.

## 4.5 Universal exclusions

A company should be excluded or heavily penalized when:

- it is a software house, ESN, IT consultancy, or digital agency unless a special partnership campaign is active;
- it has a substantial internal product/engineering team able to build the system;
- it is a large enterprise outside the practical deal size;
- it is a microbusiness with minimal operational complexity and weak budget;
- it is inactive, dissolved, partially non-diffusible where use is inappropriate, or legally restricted;
- the only evidence is a generic directory listing;
- the target role is unrelated to the proposed problem;
- the contact is opted out or suppressed;
- the source is stale or unverifiable;
- the company has already been rejected for a persistent mismatch reason.

---

# 5. Target system architecture

## 5.1 Target flow

```text
Market play + campaign
        ↓
Source adapters
(DECP / BOAMP / Registry / SIRENE / BODACC / Website / Jobs / Manual LinkedIn)
        ↓
Raw source records with immutable provenance
        ↓
Company identity resolution and deduplication
        ↓
Signals and evidence extraction
        ↓
Contacts and buyer-role discovery
        ↓
Fit + pain + trigger + authority + value + data-quality scoring
        ↓
Hard gates and human qualification review
        ↓
Meeting-ready daily action queue
        ↓
Personalization brief + matching offer + proof asset
        ↓
Manual approved outreach and follow-up tasks
        ↓
Outcome event log
        ↓
Funnel analytics, score calibration, and campaign decisions
```

## 5.2 Architectural principles

1. **Evidence before score.** Every score contribution must point to evidence.
2. **Company, people, signals, and contacts are separate entities.**
3. **One company can participate in several campaigns without duplicating identity data.**
4. **One company can have many signals and many people.**
5. **A source record is immutable; derived fields can be recomputed.**
6. **Human qualification is a formal state, not an informal note.**
7. **Outreach readiness is gated, not inferred from a high score alone.**
8. **The active offer is part of the lead record.**
9. **Automation stops before actions that create legal, platform, or reputation risk.**
10. **Performance is measured by meetings and wins, not records imported.**

---

# 6. Data-model redesign

## 6.1 Migration strategy

Do not delete the current `prospects` table immediately. Introduce normalized V3 tables, migrate useful data, keep compatibility views temporarily, then retire old overloaded fields.

Recommended migration sequence:

- `004_market_plays_campaigns.py`
- `005_companies_source_records_signals.py`
- `006_people_contact_points.py`
- `007_qualification_scores_assets.py`
- `008_outreach_tasks_experiments.py`
- `009_ingestion_runs_suppression_audit.py`
- `010_migrate_legacy_prospects.py`
- `011_retire_legacy_it_fields.py` after verified migration

## 6.2 `market_plays`

```python
class MarketPlay(Base):
    __tablename__ = "market_plays"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=False)

    target_naf_codes: Mapped[list] = mapped_column(JSON)
    target_naf_prefixes: Mapped[list] = mapped_column(JSON)
    excluded_naf_codes: Mapped[list] = mapped_column(JSON)
    cpv_prefixes: Mapped[list] = mapped_column(JSON)
    positive_keywords: Mapped[list] = mapped_column(JSON)
    negative_keywords: Mapped[list] = mapped_column(JSON)
    target_sizes: Mapped[list] = mapped_column(JSON)
    target_regions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    pain_hypotheses: Mapped[list] = mapped_column(JSON)
    trigger_definitions: Mapped[list] = mapped_column(JSON)
    buyer_roles: Mapped[list] = mapped_column(JSON)
    exclusions: Mapped[list] = mapped_column(JSON)
    score_config: Mapped[dict] = mapped_column(JSON)
    readiness_config: Mapped[dict] = mapped_column(JSON)

    offer_name: Mapped[str] = mapped_column(String(200))
    offer_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

A market-play version must be immutable once a campaign starts. New tuning creates a new version so historical results remain interpretable.

## 6.3 `campaigns`

```python
class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    market_play_id: Mapped[int] = mapped_column(ForeignKey("market_plays.id"))
    status: Mapped[str] = mapped_column(String(30))
    # draft, preflight, active, paused, completed, killed

    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    target_touch_count: Mapped[int | None]
    daily_manual_limit: Mapped[int | None]

    primary_offer_asset_id: Mapped[int | None]
    default_channel: Mapped[str | None]
    notes: Mapped[str | None] = mapped_column(Text)
```

A campaign cannot become active until its proof, offer, sender-domain, privacy, and tracking preflight is complete.

## 6.4 `companies`

Move stable company identity out of the overloaded prospect record.

```python
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    siren: Mapped[str | None] = mapped_column(String(9), unique=True, index=True)
    primary_siret: Mapped[str | None] = mapped_column(String(14), index=True)
    legal_name: Mapped[str] = mapped_column(String(250), index=True)
    trading_name: Mapped[str | None] = mapped_column(String(250))
    website: Mapped[str | None] = mapped_column(String(400))
    website_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    naf_code: Mapped[str | None] = mapped_column(String(10), index=True)
    sector_label: Mapped[str | None] = mapped_column(String(120), index=True)
    employee_band: Mapped[str | None] = mapped_column(String(30), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(10), index=True)
    region: Mapped[str | None] = mapped_column(String(120), index=True)
    administrative_state: Mapped[str | None] = mapped_column(String(20))
    diffusion_status: Mapped[str | None] = mapped_column(String(50))
    number_of_establishments: Mapped[int | None]

    identity_confidence: Mapped[int] = mapped_column(default=0)
    last_identity_refresh_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

## 6.5 `campaign_companies`

This replaces the idea that a company has one permanent acquisition score.

```python
class CampaignCompany(Base):
    __tablename__ = "campaign_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)

    lifecycle_state: Mapped[str] = mapped_column(String(30), index=True)
    # discovered, researching, qualified, contact_ready, outreach,
    # conversation, meeting, proposal, won, lost, parked, suppressed

    fit_score: Mapped[int] = mapped_column(default=0)
    pain_score: Mapped[int] = mapped_column(default=0)
    trigger_score: Mapped[int] = mapped_column(default=0)
    authority_score: Mapped[int] = mapped_column(default=0)
    value_score: Mapped[int] = mapped_column(default=0)
    data_quality_score: Mapped[int] = mapped_column(default=0)
    opportunity_score: Mapped[int] = mapped_column(default=0, index=True)

    score_version: Mapped[str] = mapped_column(String(40))
    score_breakdown: Mapped[dict] = mapped_column(JSON)
    readiness_state: Mapped[str] = mapped_column(String(30), index=True)
    readiness_failures: Mapped[list] = mapped_column(JSON)

    suspected_pain: Mapped[str | None] = mapped_column(Text)
    why_now: Mapped[str | None] = mapped_column(Text)
    recommended_buyer_role: Mapped[str | None] = mapped_column(String(160))
    personalization_brief: Mapped[str | None] = mapped_column(Text)
    recommended_next_action: Mapped[str | None] = mapped_column(Text)

    manual_priority_override: Mapped[int | None]
    manual_review_state: Mapped[str] = mapped_column(String(30), default="unreviewed")
    manual_reviewed_at: Mapped[datetime | None]
    manual_reviewed_by: Mapped[int | None]
    rejection_reason_code: Mapped[str | None] = mapped_column(String(80))
```

Unique constraint: `(campaign_id, company_id)`.

## 6.6 `source_records`

Every external record must have immutable provenance.

```python
class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    source_external_id: Mapped[str | None] = mapped_column(String(300), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime]
    published_at: Mapped[datetime | None]
    checksum: Mapped[str | None] = mapped_column(String(128))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    parser_version: Mapped[str] = mapped_column(String(40))
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))
```

Do not overwrite source payloads. Add new records on refresh and mark older records superseded if needed.

## 6.7 `signals`

Replace `signal_type` and `signal_details` with a one-to-many evidence model.

```python
class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), index=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"))

    category: Mapped[str] = mapped_column(String(30), index=True)
    # structural_fit, pain, trigger, value, exclusion, contact, compliance
    signal_type: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(200))
    evidence_text: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]
    confidence: Mapped[int] = mapped_column(default=50)
    strength: Mapped[int] = mapped_column(default=50)
    is_active: Mapped[bool] = mapped_column(default=True)
    manually_confirmed: Mapped[bool] = mapped_column(default=False)
```

Example signal types:

- `PUBLIC_AWARD_RECENT`
- `PUBLIC_AWARD_MULTI`
- `MULTI_SITE_OPERATIONS`
- `FIELD_TECHNICIAN_WORKFORCE`
- `RECURRING_MAINTENANCE`
- `HIRING_PLANNING_COORDINATOR`
- `HIRING_ADMIN_OPERATIONS`
- `NEW_ESTABLISHMENT`
- `MOROCCO_OFFICE_OR_ROUTE`
- `MANUAL_PDF_WORKFLOW`
- `NO_CUSTOMER_PORTAL`
- `EXCEL_OR_MANUAL_REPORTING_MENTION`
- `INTERNAL_SOFTWARE_TEAM`
- `LARGE_ENTERPRISE_EXCLUSION`
- `WEAK_OR_STALE_SOURCE`

## 6.8 `people`

```python
class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(200))
    normalized_role: Mapped[str | None] = mapped_column(String(80), index=True)
    seniority: Mapped[str | None] = mapped_column(String(40))
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(Text)
    role_confidence: Mapped[int] = mapped_column(default=0)
    current_employment_confidence: Mapped[int] = mapped_column(default=0)
    manually_confirmed: Mapped[bool] = mapped_column(default=False)
    last_confirmed_at: Mapped[datetime | None]
```

A legal representative and an operational buyer must be allowed to coexist. The system chooses a campaign-specific primary contact rather than overwriting one global decision-maker field.

## 6.9 `contact_points` and `verification_attempts`

```python
class ContactPoint(Base):
    __tablename__ = "contact_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    channel: Mapped[str] = mapped_column(String(30), index=True)
    value: Mapped[str] = mapped_column(String(320), index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(Text)

    discovery_state: Mapped[str] = mapped_column(String(30))
    # published, inferred, guessed, user_supplied
    verification_state: Mapped[str] = mapped_column(String(30), index=True)
    # untested, syntax_valid, domain_valid, deliverable, catch_all,
    # risky, indeterminate, invalid, bounced, confirmed_by_reply
    confidence: Mapped[int] = mapped_column(default=0)
    is_primary: Mapped[bool] = mapped_column(default=False)
    is_suppressed: Mapped[bool] = mapped_column(default=False)
    last_verified_at: Mapped[datetime | None]
```

`verification_attempts` stores provider, raw result, catch-all status, MX result, SMTP result, timestamp, and error. Never collapse all verification outcomes into `verified/likely`.

## 6.10 `qualification_reviews`

```python
class QualificationReview(Base):
    __tablename__ = "qualification_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_company_id: Mapped[int] = mapped_column(ForeignKey("campaign_companies.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(30))
    # accept, reject, research_more, park
    fit_confirmed: Mapped[bool]
    pain_confirmed: Mapped[bool]
    trigger_confirmed: Mapped[bool]
    buyer_confirmed: Mapped[bool]
    contact_confirmed: Mapped[bool]
    offer_match_confirmed: Mapped[bool]
    reason_codes: Mapped[list] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

## 6.11 `offer_assets`

```python
class OfferAsset(Base):
    __tablename__ = "offer_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_play_id: Mapped[int | None] = mapped_column(ForeignKey("market_plays.id"))
    asset_type: Mapped[str] = mapped_column(String(40))
    # case_study, screenshots, demo, audit, one_pager, pricing, calendar, privacy
    name: Mapped[str] = mapped_column(String(200))
    url_or_path: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    proof_tags: Mapped[list] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)
```

## 6.12 `outreach_events` refinement

Keep the append-only principle, but add structure:

- `campaign_company_id`;
- `person_id`;
- `contact_point_id`;
- `event_kind`: research, message, call, reply, meeting, proposal, decision, task;
- `direction`: outbound, inbound, internal;
- `channel`;
- `result_code`;
- `pipeline_stage_after`;
- `message_variant_id`;
- `subject`;
- `personalization_summary`;
- `proof_asset_ids`;
- `objection_code`;
- `sent_at`, `delivered_at`, `replied_at`;
- `external_message_id` when integrated;
- `created_by`.

Do not derive all status from the last arbitrary event. Derive pipeline stage only from events that declare `pipeline_stage_after`, while allowing notes and research events without changing the pipeline.

## 6.13 `tasks`

A dedicated task table is cleaner than storing only the latest `next_action` inside the last event.

Fields:

- campaign/company/person;
- task type;
- due date;
- priority;
- status;
- completion event;
- snooze reason;
- automatic/manual origin.

## 6.14 `suppression_entries`

Keep suppression independent of active prospect data.

Store normalized email/domain/person/company identifiers or hashes sufficient to prevent re-import and re-contact. Include reason, source, requested date, and scope. Deleting or anonymizing a prospect must not accidentally remove the suppression memory.

## 6.15 `ingestion_runs`

Persist every source job:

- adapter;
- market play/campaign;
- start/end;
- parser version;
- input resource metadata;
- records fetched, parsed, created, updated, rejected, duplicated;
- errors by type;
- status;
- cursor/resume data;
- log summary.

---

# 7. Discovery-source redesign

## 7.1 Source hierarchy

Use each source for a specific purpose. Do not treat all data as equal.

| Source | Primary role | What it does not prove |
|---|---|---|
| SIRENE | identity, activity, status, establishment data | operational pain or buying intent |
| Recherche Entreprises | company search, dirigeants, identity enrichment | correct operational buyer |
| DECP | awarded-contract timing and value evidence | need for custom software |
| BOAMP API | detailed notices and award context | internal workflow pain |
| BODACC | expansion, new establishments, management/business changes | budget or immediate need by itself |
| Company website | operating model, services, locations, team, forms | accurate internal process without corroboration |
| Public job postings | hiring pressure and role-specific complexity | guaranteed software budget |
| LinkedIn manual review | current people and public pain context | permission for automated crawling |
| Email verification | address risk reduction | recipient interest or role relevance |

## 7.2 DECP changes

### Existing problem

`app/discovery/decp.py` has universal IT CPV prefixes and keywords. This makes discovery commercially biased before scoring begins.

### Required redesign

1. Rename the module purpose from “Elevya-relevant IT awards” to generic public-award discovery.
2. Remove `DEFAULT_CPV_PREFIXES` and `DEFAULT_KEYWORDS` as universal constants.
3. Pass `MarketPlay` discovery configuration into `filter_relevant()`.
4. Store every matched award as a source record and signal.
5. Separate:
   - award recency;
   - award count;
   - award amount confidence;
   - buyer type;
   - object relevance;
   - lot information;
   - supplier identity confidence.
6. Deduplicate by stable award/lot UID rather than a partial tuple where possible.
7. Flag missing/invalid amounts instead of silently treating them as zero.
8. Preserve source publication date and fetch date.
9. Use lazy Parquet scanning where practical to reduce memory pressure.
10. Record dataset resource URL, last-modified timestamp, file size, and checksum in the ingestion run.
11. Allow the official Ministry consolidated data as the primary source and the convenient consolidated Parquet dataset as an optional performance source.
12. Create unit tests for every active play’s CPV and keyword configuration.

### Target function shape

```python
def filter_awards(df: pl.LazyFrame, play: MarketPlayConfig, window: DateWindow) -> pl.LazyFrame:
    return (
        normalize_decp(df)
        .filter(valid_award_identity())
        .filter(date_in_window(window))
        .filter(match_cpv_or_keywords(play))
        .with_columns(compute_data_quality_flags())
    )
```

### Acceptance gate

For a manually reviewed sample of at least 50 matched awards:

- at least 80% must belong to the intended market play;
- duplicate award/lot rate must be below 2%;
- every record must have source provenance;
- amount/date quality must be explicit;
- no IT/cyber records should enter a non-IT play merely because of old defaults.

## 7.3 BOAMP adapter

Add `app/discovery/boamp.py`.

Use the official BOAMP API to enrich or discover:

- notice type;
- award versus call for competition;
- object text;
- CPV;
- lot details;
- buyer;
- awardee where available;
- publication date;
- notice URL.

Use BOAMP for detailed notice context and DECP for consolidated award aggregation. Do not assume one is complete enough to replace source cross-checking.

Implement:

- query builder per market play;
- pagination;
- retry with exponential backoff;
- rate and timeout controls;
- source-record checksum;
- stable external ID;
- parser-contract tests against saved fixtures;
- source-health endpoint.

## 7.4 Recherche Entreprises changes

### Existing problem

`app/discovery/annuaire.py` defaults to Section J, IT keywords, IT NAF lists, and `REGISTRY_IT`.

### Required redesign

Replace:

- `SECTION_IT` with configurable section/NAF filters;
- `discover_it_smes()` with `discover_companies_for_play()`;
- `_is_icp_candidate()` with a generic play filter;
- IT-specific blocked/allowed logic with per-play exclusions;
- `signal_hint="REGISTRY_IT"` with structural signal records.

Target function:

```python
async def discover_companies_for_play(
    play: MarketPlayConfig,
    *,
    max_results: int,
    cursor: str | None = None,
) -> DiscoveryBatch:
    ...
```

Registry discovery should create **structural candidates**, not outreach-ready prospects. A registry result without pain or trigger evidence enters `researching`, never `contact_ready`.

## 7.5 SIRENE changes

Keep SIRENE as the canonical identity and diffusion gate.

Required improvements:

- cache by SIREN/SIRET with freshness policy;
- retry and circuit breaker for temporary failure;
- persistent source record;
- distinguish unit-legal and establishment data;
- do not default missing employee band to `1-10` because that creates false certainty;
- store unknown as unknown;
- preserve administrative state and effective dates;
- create a refresh command for stale identities;
- stop the prospect from advancing when the company is inactive or identity is ambiguous;
- make the API version and authentication header configurable and covered by contract tests.

## 7.6 BODACC adapter

Add `app/discovery/bodacc.py` for selected business-change triggers:

- new establishment or branch;
- acquisition or business purchase;
- management change;
- material modification;
- relevant growth or restructuring events.

BODACC signals require careful classification. A restructuring or insolvency event may be a negative exclusion rather than a positive trigger.

Each mapping must declare:

- signal category;
- positive/negative direction;
- confidence;
- expiry;
- human-review requirement.

## 7.7 Company-website intelligence

Add a restrained crawler for public company websites only.

Suggested pages:

- home;
- services;
- sectors;
- about/team;
- locations/agencies;
- careers;
- contact;
- client portal/login;
- downloads/forms;
- legal notice.

Extract evidence such as:

- number of locations;
- field-service vocabulary;
- maintenance and recurring-contract language;
- technician or fleet references;
- downloadable PDF forms;
- customer-area presence or absence;
- job openings;
- Morocco office, route, or partner references;
- named operational leaders;
- public generic email addresses.

Rules:

- obey robots.txt where applicable;
- use a transparent user agent;
- limit depth and request rate;
- store source URL and snippet;
- never claim an internal process solely from absence of a website feature;
- classify extracted data as a hypothesis until confirmed.

## 7.8 Job-posting signals

Add an adapter only for sources whose access terms permit it, or use manual URL import.

High-value job signals for the first play:

- planning coordinator;
- service coordinator;
- assistant ADV;
- operations assistant;
- stock or spare-parts manager;
- tender coordinator;
- administrative assistant for interventions;
- digital-transformation or ERP project role;
- technicians combined with a new planner role.

A job post becomes a pain/scale signal when the responsibilities mention:

- Excel reporting;
- coordination across technicians or sites;
- manual document follow-up;
- scheduling;
- intervention reports;
- stock reconciliation;
- customer reporting;
- repeated data entry.

## 7.9 LinkedIn handling

Keep LinkedIn as a manual last-mile source.

Allowed product behavior:

- generate a Google/LinkedIn search URL;
- let the operator paste a public profile or post URL;
- capture a manual evidence note and date;
- require confirmation that the person currently works at the company;
- use the confirmed title to update role confidence.

Do not add automated crawling, browser automation, connection sending, or message sending without explicit permission from LinkedIn. The system should make the manual step fast, not attempt to evade platform restrictions.

---

# 8. Evidence and qualification model

## 8.1 Independent evidence requirement

A company must not become outreach-ready because of one strong-looking signal.

Minimum readiness evidence:

1. one structural-fit signal;
2. one pain or complexity signal;
3. one current trigger, unless the pain evidence is exceptionally direct;
4. one buyer-role match;
5. one usable contact path;
6. one matching offer/proof asset.

At least two of the evidence items should come from independent source types.

## 8.2 Evidence quality

Each signal receives:

- **confidence:** likelihood that the evidence was parsed and attributed correctly;
- **strength:** how strongly it supports the commercial hypothesis;
- **freshness:** whether it remains relevant;
- **independence:** whether it duplicates another source;
- **manual confirmation:** whether a human validated it.

## 8.3 Human qualification checklist

The review screen must require explicit answers:

- Is the company inside the active market play?
- Is there operational complexity that a custom system could reduce?
- Is the pain specific enough to mention without inventing facts?
- Is there a current reason to contact the company?
- Is the selected role likely to own or influence the problem?
- Is the person’s employment current?
- Is the channel/contact sufficiently reliable?
- Does a relevant proof asset exist?
- Can the first sentence be based on real evidence?
- Is the company free from suppression and compliance blocks?

Possible decisions:

- **Accept:** enters contact-ready queue;
- **Research more:** creates a task and lists missing evidence;
- **Park:** plausible but poor timing;
- **Reject:** stores a reason and prevents repeated waste;
- **Suppress:** legal/opt-out or persistent no-contact state.

---

# 9. Scoring redesign

## 9.1 Remove the current universal urgency score

The current score mixes fit, awards, IT NAF, title, contactability, and outreach staleness. It can make a company look urgent because it is easy to contact or because it won a contract.

Opportunity and task urgency are different concepts:

- **Opportunity score:** likelihood that this company is worth an approach for this campaign.
- **Action urgency:** whether a follow-up or trigger requires action now.

Store them separately.

## 9.2 Opportunity-score dimensions

Use six explicit dimensions:

| Dimension | Weight | Meaning |
|---|---:|---|
| Fit | 25% | Structural match to market play |
| Pain evidence | 25% | Evidence of relevant operational friction/complexity |
| Trigger/timing | 20% | Reason the company may act now |
| Authority/contact | 15% | Correct role/person and reachable channel |
| Value potential | 10% | Plausible deal value and economic capacity |
| Data quality | 5% | Accuracy, source freshness, identity confidence |

Initial formula:

```text
raw_score =
  0.25 × fit
+ 0.25 × pain
+ 0.20 × trigger
+ 0.15 × authority
+ 0.10 × value
+ 0.05 × data_quality

confidence_multiplier = 0.65 + 0.35 × (data_quality / 100)

opportunity_score = clamp(
  raw_score × confidence_multiplier
  - penalties
  + manual_override,
  0,
  100
)
```

The confidence multiplier prevents low-quality data from creating false precision.

## 9.3 Hard readiness gates

A high score cannot bypass these gates:

```python
READY_GATES = {
    "fit_score_min": 60,
    "pain_score_min": 40,
    "trigger_score_min": 30,
    "authority_score_min": 45,
    "data_quality_min": 55,
    "independent_source_types_min": 2,
    "active_signals_min": 3,
    "human_review_required": True,
    "offer_asset_required": True,
    "suppression_clear_required": True,
}
```

Readiness states:

- `insufficient_identity`
- `research_required`
- `buyer_required`
- `contact_required`
- `proof_required`
- `human_review_required`
- `contact_ready`
- `suppressed`

## 9.4 Penalties

Examples:

- internal software/IT team: `-15` to `-30` depending on market play;
- company over target size: `-15`;
- micro company with weak complexity: `-15`;
- only one source: `-10`;
- contact guessed and catch-all: `-15`;
- trigger older than configured window: `-10`;
- no direct pain evidence: prevent readiness rather than only subtracting points;
- stale person employment: `-20`;
- duplicate or suppression: hard zero/block.

## 9.5 Example scoring implementation

```python
@dataclass(frozen=True)
class OpportunityInputs:
    fit: int
    pain: int
    trigger: int
    authority: int
    value: int
    data_quality: int
    penalties: int = 0
    manual_override: int = 0


def compute_opportunity_score(x: OpportunityInputs) -> int:
    raw = (
        0.25 * x.fit
        + 0.25 * x.pain
        + 0.20 * x.trigger
        + 0.15 * x.authority
        + 0.10 * x.value
        + 0.05 * x.data_quality
    )
    confidence_multiplier = 0.65 + 0.35 * (x.data_quality / 100)
    score = raw * confidence_multiplier - x.penalties + x.manual_override
    return max(0, min(100, round(score)))
```

Every component should return reasons and signal IDs, not only a number.

## 9.6 Action urgency

Action urgency is computed from tasks and events:

- reply awaiting response;
- meeting preparation due;
- follow-up due or overdue;
- recent trigger with shrinking relevance window;
- proposal expiration;
- contact confirmation aging;
- no activity after a qualified conversation.

The daily queue should sort first by action state, then opportunity score:

1. inbound replies needing action;
2. meetings/proposals due;
3. overdue qualified follow-ups;
4. newly contact-ready high-score prospects;
5. research tasks;
6. parked/stale prospects.

## 9.7 Score calibration

After enough real outcomes, calibrate rather than guessing forever.

Required reports:

- positive reply rate by score decile;
- meeting rate by score decile;
- human acceptance rate by source and play;
- false-positive reasons for top-ranked prospects;
- conversion by individual signal;
- conversion by buyer role;
- conversion by offer and proof asset.

A score is useful only if higher score groups produce better outcomes. If the top quartile does not outperform lower quartiles, the model fails regardless of how reasonable the formula looks.

Do not introduce ML until there are at least several hundred clean, consistently labeled outreach records. When that threshold is reached, use interpretable logistic regression as a challenger model—not an opaque replacement—and compare it against the rules-based baseline.

---

# 10. Contact intelligence redesign

## 10.1 Role-first contact discovery

The system currently tends to choose a registry dirigeant. V3 should first determine the **buyer role required by the market play**, then find a person.

Example for field-service operations:

1. operations/exploitation director;
2. service/maintenance manager;
3. owner/gérant for smaller firms;
4. technical director;
5. DAF/administration for reporting pain;
6. commercial director for quote pain.

The legal president is a fallback, not automatically the best buyer.

## 10.2 Contact-confidence states

Replace broad `verified`, `likely`, and `unverified` labels with:

- `published_personal`: explicitly public personal work address;
- `published_generic`: public role mailbox;
- `confirmed_by_reply`;
- `deliverable_non_catch_all`;
- `catch_all_indeterminate`;
- `domain_and_pattern_only`;
- `syntax_only`;
- `risky`;
- `invalid`;
- `bounced`;
- `suppressed`.

Suggested action policy:

| State | Automatic readiness |
|---|---|
| confirmed by reply | Yes |
| published personal | Yes after role confirmation |
| deliverable non-catch-all | Yes after role confirmation |
| published generic | Yes for relevant B2B message, lower personalization |
| catch-all indeterminate | Manual review |
| domain and pattern only | No email send; use LinkedIn or verify further |
| syntax only | No |
| risky/invalid/bounced | Block |
| suppressed | Hard block |

## 10.3 Reacher changes

Current `_normalize()` marks `safe` or `is_deliverable=True` as verified without sufficiently separating catch-all ambiguity.

Change it so:

- catch-all never becomes fully verified;
- raw provider response is persisted;
- timeout/provider error becomes indeterminate, not a weak positive;
- verification date and age are visible;
- SMTP verification can be disabled per VPS/provider constraints;
- licensing status is documented before commercial use;
- no mass candidate probing is performed without rate and reputation controls.

## 10.4 Email-candidate changes

Keep permutations, but:

- label every generated address as guessed;
- use observed company email patterns before generic French patterns;
- separate person and generic role candidates;
- do not stop on the first ambiguous SMTP result;
- preserve why a pattern was chosen;
- add a domain-confidence score;
- reject free-mail domains for company contact unless manually confirmed;
- store bounce outcomes and suppress future use.

## 10.5 Contact review UI

The contact panel should show:

- recommended role and why;
- all known people with source and current-employment confidence;
- all contact points with discovery and verification state;
- company domain evidence;
- verification history;
- a Google/LinkedIn manual search button;
- “confirm current employee” action;
- “select primary contact” action;
- “do not email—use LinkedIn/phone” warning;
- suppression status.

---

# 11. Outreach system redesign

## 11.1 The tool should support outreach, not blindly automate it

For the first commercial pilot, ProspectForge should:

- prepare a personalization brief;
- recommend a message variant;
- select the matching proof asset;
- create a draft or mailto action;
- require human approval;
- log the exact message version;
- schedule follow-up tasks;
- record replies, objections, meetings, proposals, and outcomes.

It should not automatically blast sequences.

## 11.2 Personalization brief

For each contact-ready prospect, generate a structured brief:

```text
Observed fact:
Recent trigger:
Likely operational consequence:
Relevant buyer role:
Offer match:
Proof match:
Safe first-line claim:
Claims that must not be made:
Recommended CTA:
```

The brief must use source-linked evidence. It may hypothesize pain, but must clearly distinguish observed facts from inference.

## 11.3 Message variants

Add `message_variants` with:

- campaign;
- channel;
- language;
- subject;
- body template;
- offer asset requirements;
- active/test status;
- version;
- hypothesis;
- result metrics.

Only test one meaningful variable at a time where possible:

- pain angle;
- proof type;
- CTA;
- subject;
- opening trigger.

## 11.4 Outreach preflight gate

A campaign cannot start until:

- professional sender address is active;
- SPF is configured;
- DKIM is configured;
- DMARC is configured and monitored;
- sender identity is clear;
- privacy/objection language exists;
- case study exists;
- demo/screenshots exist;
- offer scope exists;
- calendar or booking process exists;
- suppression logic is tested;
- bounce handling is defined;
- daily volume limit is configured;
- test emails render correctly.

## 11.5 Follow-up policy

Follow-up tasks should be explicit and limited. Example pilot policy:

- initial touch;
- one evidence-based follow-up;
- one final low-pressure close-out;
- stop immediately on refusal or opt-out;
- do not keep resetting follow-up indefinitely.

The exact cadence should be campaign-configurable and must not be presented as a legal rule or guaranteed best practice.

## 11.6 Outcome taxonomy

Use structured outcome codes:

**Delivery**

- delivered;
- soft bounce;
- hard bounce;
- unknown.

**Reply**

- positive;
- neutral;
- referral;
- not now;
- wrong person;
- already solved;
- no budget;
- no need;
- internal capability;
- vendor restriction;
- explicit refusal;
- opt-out.

**Commercial**

- discovery booked;
- discovery held;
- audit requested;
- proposal requested;
- proposal sent;
- negotiation;
- won;
- lost.

Store free-text notes in addition to structured codes.

---

# 12. UX redesign

## 12.1 Main page: Today

Replace the dashboard as the default operator screen with `/today`.

Sections:

1. inbound replies requiring action;
2. meetings and proposals due;
3. overdue follow-ups;
4. top contact-ready prospects;
5. qualification reviews waiting;
6. failed source jobs and data warnings.

Each item must have one clear primary action.

## 12.2 Acquisition cockpit

Redesign `/sourcing` into four tabs:

### A. Raw discoveries

- source;
- company identity confidence;
- play match;
- missing enrichment;
- import/reject reason.

### B. Research queue

- missing evidence;
- suggested source/action;
- estimated research effort;
- quick buttons.

### C. Qualification review

- evidence board;
- score breakdown;
- buyer/contact panel;
- offer/proof match;
- accept/reject/research/park controls.

### D. Contact-ready queue

- action urgency;
- opportunity score;
- personalization brief;
- contact confidence;
- message/proof recommendation;
- send/log action.

## 12.3 Prospect/company detail

Use sections rather than one long mixed page:

- company identity;
- campaign participation;
- evidence timeline;
- awards and business triggers;
- people and contact points;
- score and readiness;
- qualification reviews;
- personalization and assets;
- outreach timeline;
- tasks;
- compliance and suppression;
- raw source records.

## 12.4 Score transparency

Show:

- six component scores;
- every contributing signal;
- penalties;
- data-quality multiplier;
- readiness failures;
- score version;
- last recompute time;
- manual override and reason.

Do not show a single colorful number without the evidence behind it.

## 12.5 Search and filters

Required filters:

- campaign and market play;
- lifecycle and readiness state;
- human-review state;
- opportunity score range;
- fit/pain/trigger minimums;
- sector/NAF;
- size/location;
- signal type and age;
- source type;
- buyer role;
- contact verification state;
- suppression state;
- last contact and task due date;
- rejection reason.

## 12.6 Bulk actions

Allow bulk actions only where safe:

- assign campaign;
- queue enrichment;
- mark for review;
- park/reject with reason;
- export approved contacts;
- create research tasks.

Do not allow bulk “Sent” on records that have not passed readiness and human review.

---

# 13. Analytics and learning loop

## 13.1 Replace vanity metrics

The current dashboard emphasizes prospect totals, contacted counts, and broad reply rates. V3 should emphasize funnel quality.

## 13.2 Required acquisition metrics

### Discovery quality

- raw records fetched;
- unique companies resolved;
- duplicate rate;
- identity-failure rate;
- target-play match rate;
- qualified yield per source;
- contact-ready yield per source;
- median research time per accepted company.

### Outreach quality

- attempted;
- delivered;
- bounce rate;
- reply rate;
- positive reply rate;
- referral rate;
- meeting-booked rate;
- meeting-held rate;
- proposal rate;
- win rate;
- time from discovery to first touch;
- follow-up completion rate.

### Commercial learning

Break down by:

- market play version;
- campaign;
- sector/NAF;
- company size;
- source;
- signal type;
- buyer role;
- channel;
- message variant;
- offer;
- proof asset;
- opportunity-score band.

### Efficiency

- operator minutes per qualified company;
- operator minutes per meeting;
- records reviewed per accepted prospect;
- source/API cost per accepted prospect;
- outreach touches per meaningful conversation.

## 13.3 Small-sample warnings

The UI must show sample sizes. Do not declare a source, message, or play superior after a few replies. Add minimum-observation warnings and confidence intervals where practical.

## 13.4 Weekly decision report

Generate a concise weekly report:

- what was attempted;
- top and bottom sources;
- top rejection reasons;
- strongest signals;
- objections;
- score calibration;
- campaign progress;
- recommended keep/change/kill decisions;
- exact experiments for the next cycle.

---

# 14. Background jobs and reliability

## 14.1 Remove scheduler from the web process

The current application requires one Uvicorn worker because APScheduler runs inside the web process. This couples discovery reliability to web uptime and makes future scaling dangerous.

Create a dedicated `worker` service using the same image.

Recommended simple design without Redis:

- web container serves FastAPI only;
- worker container runs scheduled and queued jobs;
- PostgreSQL stores `ingestion_runs` and job state;
- PostgreSQL advisory locks prevent duplicate execution;
- cron/APScheduler exists only in the worker;
- each run is restartable or safely idempotent.

## 14.2 Job types

- source metadata refresh;
- DECP ingest per play;
- BOAMP ingest per play;
- registry discovery per play;
- SIRENE refresh;
- website enrichment;
- contact verification;
- score recompute;
- stale-evidence expiration;
- retention/suppression maintenance;
- metrics materialization;
- backup verification.

## 14.3 Job controls

Each job needs:

- max records;
- timeout;
- retries;
- concurrency;
- source-specific rate limit;
- circuit breaker;
- idempotency key;
- cursor/resume state;
- dry-run mode;
- manual cancel;
- error summary;
- operator-visible status.

## 14.4 Default automation policy

Production defaults for the first pilot:

- nightly full discovery: **off**;
- manual source run: **on**;
- automatic score recompute after evidence changes: **on**;
- retention/suppression maintenance: **on**;
- contact verification: manual/batched and limited;
- message sending: manual only.

Enable scheduled discovery only after three consecutive live runs pass source-quality and resource-usage gates.

---

# 15. API redesign

## 15.1 New endpoints

Suggested API surface:

```text
GET    /api/market-plays
POST   /api/market-plays
POST   /api/market-plays/{id}/clone-version

GET    /api/campaigns
POST   /api/campaigns
POST   /api/campaigns/{id}/preflight
POST   /api/campaigns/{id}/activate
POST   /api/campaigns/{id}/pause

POST   /api/ingestion-runs
GET    /api/ingestion-runs
GET    /api/ingestion-runs/{id}
POST   /api/ingestion-runs/{id}/cancel

GET    /api/companies
GET    /api/companies/{id}
GET    /api/companies/{id}/evidence
GET    /api/companies/{id}/people
GET    /api/companies/{id}/contacts

GET    /api/campaigns/{id}/queue
POST   /api/campaign-companies/{id}/recompute
POST   /api/campaign-companies/{id}/qualify
POST   /api/campaign-companies/{id}/reject
POST   /api/campaign-companies/{id}/park

POST   /api/people/{id}/confirm
POST   /api/contact-points/{id}/verify
POST   /api/contact-points/{id}/select-primary

POST   /api/outreach/drafts
POST   /api/outreach/events
GET    /api/tasks/today
POST   /api/tasks/{id}/complete
POST   /api/tasks/{id}/snooze

POST   /api/suppression
GET    /api/analytics/funnel
GET    /api/analytics/calibration
```

## 15.2 Compatibility

Keep legacy prospect endpoints during migration, but mark them deprecated and prevent new V3 features from writing only to legacy fields.

---

# 16. Compliance and data governance

## 16.1 Practical B2B principles

The system must enforce that:

- outreach relates to the person’s professional role;
- the sender is identified;
- the commercial purpose is clear;
- objection/opt-out is simple and free;
- source and collection context are documented;
- only necessary data is retained;
- opt-outs are honored across imports and campaigns;
- data is secured and access is audited.

This specification is an engineering control framework, not legal advice. Obtain professional legal advice when required.

## 16.2 Correct `informed_at` behavior

The current system requires `informed_at` before a `Sent` event. Operationally, the disclosure is usually included in the first message.

Change to:

- `privacy_notice_included` on the outbound message/event;
- first compliant `Sent` transaction automatically sets `informed_at` to the send timestamp;
- store the notice version used;
- block send logging if the required notice is missing;
- do not require the operator to enter a fictional earlier timestamp.

## 16.3 Retention

Prospect data should generally be reviewed for deletion/anonymization after the configured period from collection or the last meaningful inbound contact from the prospect. An outgoing sequence should not extend retention indefinitely.

Implement:

- `collected_at`;
- `last_inbound_contact_at`;
- `retention_review_at`;
- `retention_basis`;
- automated review queue;
- separate suppression retention.

## 16.4 Suppression

On refusal/opt-out:

- create suppression entry immediately;
- block all channels in scope;
- remove from future queues;
- prevent re-import from creating a new active contact;
- keep minimal suppression data necessary to honor the request;
- record source and timestamp.

## 16.5 LinkedIn

Do not automate crawling or messaging without permission. Manual confirmation and URL capture remain the safe product boundary.

## 16.6 Audit log

Add immutable audit records for:

- login and security changes;
- campaign activation;
- qualification decisions;
- contact selection;
- bulk export;
- outreach log changes;
- suppression;
- data deletion/anonymization;
- score override;
- job execution.

---

# 17. Security hardening

## 17.1 Authentication

Required changes:

- separate browser session login from API bearer-token response;
- rotate session token on login;
- add CSRF protection to all cookie-authenticated state-changing requests;
- add login throttling by account and IP;
- add password-change route;
- support forced admin-password rotation;
- shorten session duration or add idle expiry;
- invalidate sessions after password change;
- do not expose a bearer token unnecessarily to browser clients;
- log authentication failures without storing plaintext secrets.

## 17.2 Cookies

Production settings:

- `Secure=true`;
- `HttpOnly=true`;
- `SameSite=Lax` or stricter after testing;
- explicit path;
- sensible max age;
- real HTTPS only.

## 17.3 Host and proxy trust

- set `TRUSTED_HOSTS` to the exact domain and necessary internal names;
- do not use `*` in production;
- trust forwarded headers only from the actual reverse proxy path;
- bind the app to the internal Docker network or loopback;
- ensure the database is never publicly exposed.

## 17.4 Migrations

Change startup behavior:

- Alembic failure must terminate startup;
- remove production fallback to `create_all`;
- run a database backup before destructive migrations;
- add migration smoke tests against a copy of production schema;
- verify current revision during readiness.

## 17.5 Web security

Add:

- CSRF tokens;
- Content Security Policy compatible with HTMX/Jinja assets;
- secure headers;
- request-size limits for CSV/imports;
- file-type validation;
- formula-injection protection on CSV export;
- output escaping review;
- rate limits on login, ingest, enrich, and verification endpoints;
- permission checks on every route;
- sanitized error responses in production.

## 17.6 Secrets

- use a root-owned `.env` with restrictive permissions or Docker secrets;
- do not store source credentials in the database unencrypted;
- rotate admin, database, and signing secrets before deployment;
- never log API keys, passwords, full tokens, or raw email-provider credentials.

---

# 18. VPS deployment target

## 18.1 Recommended topology

```text
Internet
  ↓
Existing VPS Caddy/nginx on 80/443
  ↓  HTTPS: prospectforge.elevya.tech
ProspectForge web container on internal/loopback port
  ↔ PostgreSQL internal network
  ↔ ProspectForge worker container
  ↔ optional Reacher profile
  ↔ persistent data/cache volume

Encrypted off-VPS backup destination
```

Use a real subdomain under the existing domain. Do not make users access a self-signed certificate on port 18443 as the normal production experience.

## 18.2 Caddy changes

The target Caddy site should use the domain directly and automatic HTTPS:

```caddyfile
prospectforge.elevya.tech {
    encode zstd gzip

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }

    reverse_proxy 127.0.0.1:18081
}
```

If the VPS already has a reverse proxy, remove the public Caddy service from ProspectForge Compose and expose only loopback/internal app ports.

## 18.3 Compose changes

Services:

- `web` — FastAPI, no scheduler;
- `worker` — ingestion/scheduler;
- `db` — internal only;
- `reacher` — optional profile;
- `backup` — scheduled or host-triggered;
- no public database port;
- no public plaintext ProspectForge port unless used temporarily and firewalled.

Add:

- resource limits;
- read-only root filesystem where feasible;
- `tmpfs` for temporary files;
- explicit health/readiness checks;
- named cache/data volumes;
- separate worker health;
- graceful shutdown;
- log rotation.

## 18.4 Backup design

Current backups on a named volume on the same VPS are insufficient as the only backup.

Required:

- nightly `pg_dump`;
- encryption;
- off-VPS copy;
- retention policy;
- checksum;
- backup success monitoring;
- periodic automated restore test;
- pre-migration snapshot.

## 18.5 Observability

Minimum:

- structured JSON application logs;
- source/job run dashboard;
- exception tracking or alerting;
- disk, memory, CPU, and container health;
- database size and connection monitoring;
- backup status;
- source freshness;
- queue depth;
- email verification error rate;
- security/login anomaly log.

---

# 19. Testing strategy

## 19.1 Preserve current tests

The current 53 tests become regression tests. Fix the 11 Ruff findings and make lint mandatory.

## 19.2 New unit tests

- market-play validation;
- per-play NAF and CPV matching;
- signal freshness and expiry;
- opportunity score components;
- readiness gates;
- penalties;
- suppression checks;
- contact verification normalization;
- buyer-role ranking;
- retention-date logic;
- CSV formula-injection escaping.

## 19.3 Source-contract tests

For each external source:

- store representative fixtures;
- validate parser against fixture schema;
- detect missing required fields;
- test pagination, rate limit, timeout, malformed payload, and empty result;
- maintain a live smoke test that runs manually or on a schedule without breaking normal CI.

## 19.4 Integration tests

Test full flows:

1. raw source record → company resolution;
2. signals → score;
3. missing evidence → research state;
4. human accept → contact-ready;
5. outbound event → informed timestamp and follow-up task;
6. opt-out → suppression and queue removal;
7. duplicate import → no duplicate company/contact;
8. migration from legacy prospect;
9. worker restart → no duplicate ingestion;
10. failed source run → visible recoverable error.

## 19.5 Security tests

- CSRF rejection;
- unauthenticated route rejection;
- trusted-host rejection;
- login rate limiting;
- secure-cookie behavior;
- CSV upload limits;
- injection/escaping checks;
- suppression enforcement on every send path;
- secrets absent from logs.

## 19.6 Live pilot quality gates

Before scheduled operation:

- manually review 50 discoveries from the active play;
- at least 80% must be in-sector;
- at least 70% of the top 20 must be accepted by human review;
- at least 50% of accepted companies should have a credible buyer/contact path;
- no suppressed contact may reappear;
- source jobs must complete repeatedly without resource or schema failure;
- rankings must have evidence explanations.

---

# 20. Exact file-by-file change map

## `README.md`

Replace IT/digital positioning with V3 mission. Document:

- market plays;
- evidence and human qualification;
- meeting-ready queue;
- safe manual last mile;
- honest limitations;
- new production topology.

## `GUIDE.md`

Rewrite completely around:

- active campaign;
- daily `/today` workflow;
- evidence review;
- qualification;
- contact confirmation;
- personalization brief;
- outreach logging;
- weekly learning report.

Remove all instructions that default to IT/cyber and `REGISTRY_IT`.

## `prospectforge_spec_python.md`

Mark V2 as historical or replace with a concise architecture document pointing to this master specification.

## `logic_specification.txt`

Retire the IT-specific pipeline. Replace it with market-play adapter contracts and readiness gates.

## `app/config.py`

Add:

- active play/campaign defaults;
- source enable flags;
- worker mode;
- exact proxy settings;
- CSRF secret/rotation;
- job limits;
- website crawler limits;
- retention configuration;
- off-VPS backup configuration;
- sender-domain preflight settings.

Remove dangerous production defaults such as wildcard trusted hosts and enabled nightly ingestion.

## `app/models.py`

Add normalized V3 models described above. Keep legacy properties temporarily for migration only.

Remove IT-specific constants from global enums. Signal types should be database/config-driven or broad generic enums.

## `app/schemas.py`

Add schemas for plays, campaigns, signals, evidence, people, contacts, qualification, tasks, assets, job runs, suppression, analytics, and preflight.

Avoid mutable list defaults; use `Field(default_factory=list)`.

## `app/discovery/naf.py`

Rename to a general taxonomy module or split:

- `taxonomy/naf.py` — normalization and sector mapping;
- `market_plays/*.yaml` — target/exclusion codes.

Remove `is_it_cyber_naf()` from the universal pipeline.

## `app/discovery/icp.py`

Replace with:

- `app/scoring/opportunity.py`;
- `app/scoring/readiness.py`;
- `app/scoring/role_match.py`;
- `app/market_plays/loader.py`.

No global “Elevya ICP” should remain in code.

## `app/scoring.py`

Separate:

- opportunity scoring;
- task/action urgency;
- score explanation;
- calibration output.

Remove IT NAF boosts and the base-50 urgency design.

## `app/discovery/decp.py`

Make play-configurable, lazy, evidence-producing, and resource-audited.

## `app/discovery/annuaire.py`

Replace `discover_it_smes()` with generic play discovery. Unknown headcount must remain unknown.

## `app/discovery/sirene.py`

Add caching, version/config contract, source persistence, and exact unknown handling.

## `app/discovery/enrich.py`

Break the large waterfall into independent enrichment steps. Deep enrichment should not silently generate a final outreach score. It should create source records, signals, people, and contact candidates, then invoke scoring.

## `app/discovery/emails.py`

Keep permutations but label them guessed. Add pattern evidence and strict state transitions.

Fix ambiguous variable names reported by Ruff.

## `app/discovery/reacher.py`

Add catch-all-safe normalization, persistent verification attempts, age, and provider errors.

## `app/discovery/harvester.py`

Keep disabled by default. Evaluate maintenance, terms, licensing, and actual lead yield. Remove it if it does not materially improve accepted-contact yield.

Fix current unused-variable lint issue.

## `app/jobs/ingestion.py`

Rewrite around:

- campaign/play input;
- adapter runs;
- persisted ingestion records;
- idempotency;
- batch commits with savepoints;
- no full transaction rollback losing unrelated successes;
- explicit rejection reasons;
- worker execution.

Remove “registry means IT SMEs.”

## `app/jobs/scheduler.py`

Move to the worker container. Disable nightly full acquisition by default. Add persistent job state and locks.

## `app/services.py`

Split into domain services:

- company identity;
- evidence/signals;
- scoring/readiness;
- qualification;
- contacts;
- outreach;
- tasks;
- compliance/suppression;
- analytics;
- import/export.

Enforce readiness and suppression in one central service used by every send/log path.

## `app/routers/sourcing.py`

Break the large router into:

- market plays/campaigns;
- discovery runs;
- company research;
- qualification;
- contacts.

## `app/routers/prospects.py`

Migrate to company/campaign-company terminology. Keep legacy aliases temporarily.

## `app/routers/events.py`

Use structured outcome codes, explicit pipeline transitions, and task creation.

## `app/routers/dashboard.py`

Add `/today`, funnel analytics, source quality, and calibration. Remove prospect-count emphasis.

## `app/auth.py` and `app/routers/auth.py`

Add CSRF/session hardening, throttling, password rotation, and separate browser/API behavior. Remove unused imports.

## `app/main.py`

- no `create_all` in production;
- no scheduler in web lifespan;
- exact trusted-proxy configuration;
- sanitized health response;
- security middleware;
- startup config validation.

## Templates

Create:

- `today.html`;
- `campaigns.html`;
- `campaign_detail.html`;
- `qualification_queue.html`;
- `evidence_board.html`;
- `people_contacts.html`;
- `personalization_brief.html`;
- `ingestion_runs.html`;
- `analytics_funnel.html`;
- `analytics_calibration.html`;
- `campaign_preflight.html`.

Refactor existing sourcing/prospect pages to use partials and reduce duplicated business logic.

## `docker-compose.yml`

- split web/worker;
- no public database port;
- disable public high-port proxy when using VPS edge proxy;
- secure cookies true;
- exact trusted hosts;
- nightly ingest false by default;
- add resource and security options;
- optional Reacher profile only.

## `deploy/Caddyfile`

Use real domain automatic HTTPS or remove in favor of existing VPS proxy. Do not advertise self-signed high-port access as the target production design.

## `scripts/entrypoint.sh`

Fail hard on migration error. Remove `create_all` reliance. Support separate web and worker commands.

## `scripts/deploy.sh`

Add:

- config validation;
- pre-deploy backup;
- migration check;
- post-deploy readiness;
- worker health;
- source smoke test optional;
- rollback instructions;
- no recommendation to expose plain HTTP publicly.

## Tests

Fix Ruff issues and add all V3 test classes before enabling scheduled ingestion.

---

# 21. Ordered implementation program

## Gate 0 — Freeze and protect

- create a V3 branch;
- export current data;
- back up database and repository;
- disable nightly ingestion;
- record current migration revision;
- fix 11 lint findings;
- keep all 53 tests green.

**Exit condition:** clean, reproducible baseline.

## Gate 1 — Production hardening

- real-domain reverse proxy;
- secure cookies;
- exact trusted hosts/proxies;
- CSRF;
- login throttling;
- migration fail-hard;
- web/worker split;
- off-VPS backups;
- security tests.

**Exit condition:** safe protected internal deployment with no acquisition automation enabled.

## Gate 2 — Market-play foundation

- add market-play and campaign models;
- seed `FIELD_SERVICE_OPERATIONS_FR`;
- rewrite NAF/CPV configuration;
- remove IT defaults;
- add campaign preflight.

**Exit condition:** the active play controls every discovery and score path.

## Gate 3 — Evidence architecture

- add company, source record, signal, people, contact, and campaign-company models;
- migrate current prospect data;
- preserve legacy compatibility;
- add evidence timeline.

**Exit condition:** every score contribution can reference a signal and source.

## Gate 4 — Discovery correction

- generic registry adapter;
- play-configurable DECP;
- BOAMP adapter;
- SIRENE improvements;
- source-run records;
- manual source-health tests.

**Exit condition:** live sample meets discovery-quality gates.

## Gate 5 — Contact and buyer correction

- role-first ranking;
- multi-person model;
- contact confidence states;
- Reacher correction;
- manual LinkedIn confirmation flow;
- suppression integration.

**Exit condition:** accepted companies have credible buyer/contact paths without overstating guessed emails.

## Gate 6 — Opportunity scoring and qualification

- six-dimensional score;
- hard readiness gates;
- penalties;
- human review screen;
- daily contact-ready queue;
- score explanations.

**Exit condition:** top-ranked sample is accepted by human review at the required rate.

## Gate 7 — Offer, proof, and outreach workflow

- offer assets;
- campaign preflight;
- personalization brief;
- message variants;
- structured outcomes;
- task/follow-up model;
- sender-domain verification checklist.

**Exit condition:** the tool can move one qualified prospect from evidence to a reviewed message and tracked follow-up without spreadsheets.

## Gate 8 — Analytics and pilot

- funnel metrics;
- source quality;
- role/message/offer results;
- calibration charts;
- weekly decision report;
- first controlled real outreach batch.

**Exit condition:** actual outcomes—not assumptions—determine the next iteration.

## Gate 9 — Controlled automation

Only after repeated successful manual operation:

- schedule approved source runs;
- add mailbox draft/reply synchronization if desired;
- add constrained follow-up reminders;
- consider paid enrichment fallback;
- evaluate a calibrated model.

**Exit condition:** automation increases qualified output without reducing quality, compliance, or deliverability.

---

# 22. Commercial pilot gates

The system is not “successful” when deployed. It must pass real commercial gates.

## 22.1 Discovery gate

Review a fixed sample from the active play.

Pass when:

- target relevance is high;
- evidence is source-linked;
- false positives have structured reasons;
- company identity is accurate;
- the top queue is materially better than random registry search.

## 22.2 Outreach gate

Run a controlled batch of fully reviewed prospects.

Track:

- delivery;
- bounce;
- reply;
- positive reply;
- wrong-person referral;
- meeting;
- objections;
- time spent.

Do not scale volume if:

- bounce is high;
- most replies say the problem is irrelevant;
- most contacts are the wrong person;
- top scores do not outperform lower scores;
- personalization cannot be grounded in evidence;
- proof is not credible.

## 22.3 Offer gate

A useful signal can still fail if the offer is generic.

Pass when prospects understand:

- the specific operational outcome;
- the scope;
- why the proof is relevant;
- what the first engagement involves;
- what risk is reduced.

## 22.4 Kill or pivot criteria

Pause a market play when a meaningful sample shows:

- very low human acceptance of discoveries;
- persistent wrong-person problems;
- replies but no pain recognition;
- repeated “we already have this” or “we build internally”;
- no meeting progression;
- delivery effort incompatible with pricing.

A paused play preserves its version and results. Create a new version or new play rather than rewriting history.

---

# 23. Daily operating workflow after V3

## Morning

1. Open `/today`.
2. Respond to inbound replies first.
3. Prepare meetings/proposals.
4. Complete overdue qualified follow-ups.
5. Review newly contact-ready prospects.
6. Send only the configured number of high-quality touches.

## Prospect review

For each prospect:

1. verify observed facts;
2. inspect pain and trigger evidence;
3. confirm buyer role and current person;
4. inspect contact state;
5. select offer/proof;
6. review personalization brief;
7. approve or edit message;
8. log exact send and next task.

## End of day

- resolve bounces;
- record replies and objections;
- correct wrong contacts;
- suppress opt-outs;
- complete tasks;
- note evidence-quality problems.

## Weekly

- review funnel by market play/source/role/message;
- inspect top rejection reasons;
- inspect score calibration;
- adjust one hypothesis at a time;
- decide keep/change/pause;
- refresh proof and offer based on conversations.

---

# 24. Proof and sales assets required outside the code

ProspectForge cannot compensate for missing credibility. Before outreach, prepare:

## 24.1 Case study

- client/company type without exposing confidential identity;
- previous workflow;
- operational problems;
- system delivered;
- roles and modules;
- concrete result that can be truthfully supported;
- screenshots;
- deployment reality;
- your exact role;
- honest limitations.

Do not invent “used daily,” time savings, revenue impact, or delivery duration unless verified.

## 24.2 Demo

- stable deployed demo or private recording;
- two-minute version for first contact;
- deeper version for discovery;
- dummy data;
- no exposed client data;
- mobile and desktop screenshots where relevant.

## 24.3 Packaged offer

For the first play, define:

- diagnostic/discovery step;
- included workflow;
- exclusions;
- required client inputs;
- delivery milestones;
- acceptance criteria;
- maintenance/support option;
- price logic;
- payment schedule;
- risk controls.

## 24.4 Trust assets

- professional email under the domain;
- concise portfolio page;
- privacy information;
- calendar/booking flow;
- clear identity and location;
- GitHub or technical proof when appropriate;
- proposal and statement-of-work templates.

The tool should store links to these assets and enforce campaign preflight.

---

# 25. Priority backlog

## P0 — Must be completed before serious use

- remove IT/cyber hard-coding;
- seed first market play;
- disable nightly ingestion by default;
- correct deployment/TLS/cookies/hosts;
- CSRF and login throttle;
- migration fail-hard;
- evidence/source model;
- human qualification gate;
- opportunity/readiness split;
- role-first contacts;
- contact-confidence correction;
- suppression enforcement;
- proof/offer preflight;
- 53 tests passing and lint clean.

## P1 — Required for an efficient pilot

- BOAMP adapter;
- website evidence crawler;
- BODACC triggers;
- dedicated worker;
- ingestion-run UI;
- daily queue;
- personalization brief;
- structured outcomes/tasks;
- funnel and source-quality analytics;
- off-VPS backup/restore test.

## P2 — Add after pilot evidence

- mailbox draft/sent/reply synchronization;
- job-post adapter;
- paid enrichment waterfall;
- calibrated challenger model;
- richer experiment analytics;
- additional market plays;
- team roles and permissions.

## P3 — Explicitly deferred

- autonomous sequences;
- LinkedIn automation;
- black-box AI score;
- SaaS multi-tenancy;
- billing automation;
- broad CRM replacement.

---

# 26. Definition of done

ProspectForge V3 is ready for normal daily use only when all conditions below are true.

## Product

- one active market play controls discovery, qualification, offer, and messaging;
- daily queue shows evidence, pain, trigger, buyer, contact, offer, and next action;
- no prospect becomes contact-ready without hard gates and human review;
- people and contact points are one-to-many;
- suppression is global and permanent enough to prevent re-contact;
- scores are transparent and versioned.

## Data

- each signal has source provenance and freshness;
- source runs are persisted and auditable;
- duplicate identity resolution works;
- unknown values remain unknown;
- live-source sample passes quality gates.

## Outreach

- campaign preflight passes;
- contact confidence is explicit;
- exact message/proof variant is logged;
- follow-ups are task-based;
- opt-out and bounce handling are tested;
- sender domain authentication is configured.

## Engineering

- all tests pass;
- lint passes;
- migrations are tested and fail hard;
- web and worker are separate;
- CSRF/rate limits/security tests pass;
- backup is copied off VPS and restored successfully;
- real HTTPS and secure cookies are active;
- health, readiness, job health, and logs are visible.

## Commercial

- the top-ranked sample is consistently accepted by human review;
- outreach results are measured by market play and evidence;
- score bands show directional conversion lift or are being corrected;
- the system reduces research and follow-up chaos without increasing low-quality volume.

---

# 27. Immediate first changes

Start with these exact changes, in order:

1. Set `ENABLE_NIGHTLY_INGESTION=false` in production defaults.
2. Create a protected V3 branch and database backup.
3. Fix the 11 Ruff findings and keep all 53 tests green.
4. Add `MarketPlay` and `Campaign` models plus initial migration.
5. Seed `FIELD_SERVICE_OPERATIONS_FR`.
6. Replace IT NAF/CPV/keyword constants with play configuration.
7. Rename and generalize `discover_it_smes()`.
8. Remove `REGISTRY_IT` creation from new ingestion runs.
9. Add source-record and signal tables.
10. Change discovery output from “prospect ready” to “company candidate requiring evidence.”
11. Implement six-dimensional opportunity scoring and hard readiness gates.
12. Add human qualification UI.
13. Add people/contact-point models and correct Reacher state handling.
14. Build the `/today` queue.
15. Split worker from web.
16. Harden deployment on a real HTTPS subdomain.
17. Add offer/proof campaign preflight.
18. Run a manually reviewed live-source sample before enabling any schedule.
19. Run a controlled outreach pilot.
20. Let real results determine further automation.

---

# 28. Authoritative resources

The following official resources should be checked during implementation because APIs, schemas, platform terms, and compliance guidance can change.

- **French consolidated public-procurement data (DECP):**  
  <https://www.data.gouv.fr/datasets/donnees-essentielles-de-la-commande-publique-consolidees-format-tabulaire>

- **French Ministry public-procurement data presentation:**  
  <https://data.economie.gouv.fr/pages/donnees-essentielles-de-la-commande-publique/>

- **BOAMP open data and API:**  
  <https://www.boamp.fr/pages/donnees-ouvertes-et-api/>  
  <https://www.boamp.fr/pages/api-boamp/>

- **API Recherche d’entreprises documentation:**  
  <https://recherche-entreprises.api.gouv.fr/docs/>

- **INSEE API Sirene catalogue:**  
  <https://portail-api.insee.fr/>

- **BODACC open data and API:**  
  <https://www.bodacc.fr/pages/donnees-ouvertes-et-api/>  
  <https://www.bodacc.fr/pages/api-bodacc/>

- **CNIL commercial prospecting guidance:**  
  <https://www.cnil.fr/fr/la-prospection-commerciale>  
  <https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique-sms-mms-et-automate-dappel>  
  <https://www.cnil.fr/fr/questions-reponses-sur-les-referentiels-relatifs-la-gestion-des-activites-commerciales-et-des>  
  <https://www.cnil.fr/fr/comment-utiliser-une-liste-repoussoir-pour-respecter-lopposition-la-prospection>

- **LinkedIn crawling terms and user agreement:**  
  <https://www.linkedin.com/legal/crawling-terms>  
  <https://www.linkedin.com/legal/user-agreement>

- **Gmail sender guidelines:**  
  <https://support.google.com/mail/answer/81126>

- **Caddy automatic HTTPS and reverse proxy documentation:**  
  <https://caddyserver.com/docs/automatic-https>  
  <https://caddyserver.com/docs/caddyfile/directives/reverse_proxy>

- **FastAPI proxy and security middleware documentation:**  
  <https://fastapi.tiangolo.com/advanced/behind-a-proxy/>  
  <https://fastapi.tiangolo.com/advanced/middleware/>

---

# Final directive

Do not judge ProspectForge V3 by how much data it imports or how sophisticated its dashboard looks.

Judge it by four questions:

1. Does the top of the queue contain companies that genuinely resemble buyers of the active offer?
2. Can every reason and score be traced to credible, current evidence?
3. Does the system identify the right role and a safe contact path?
4. Do higher-ranked, evidence-qualified prospects produce more conversations, meetings, proposals, and clients?

Until those answers are supported by real outcomes, ProspectForge is an acquisition hypothesis engine—not a client-generating machine. The rebuild above makes that hypothesis measurable, correctable, operationally safe, and commercially useful.
